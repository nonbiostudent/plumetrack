#Copyright (C) Nial Peters 2014
#
#This file is part of _plumetrack.
#
#_plumetrack is free software: you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.
#
#_plumetrack is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with _plumetrack.  If not, see <http://www.gnu.org/licenses/>.
from scipy.interpolate import interp1d
import numpy


class Spline2D:
    def __init__(self, xpts, ypts, direction):
        
        if len(xpts) != len(ypts):
            raise ValueError("xpts and ypts must contain the same number of elements")
        
        if len(xpts) < 2:
            raise ValueError("At least 2 points are required for interpolation")
        
        self.__xpts = numpy.array(xpts, dtype='float')
        self.__ypts = numpy.array(ypts, dtype='float')
        
        self.direction = direction
        self.__dist = numpy.zeros_like(self.__xpts)
        self.__dist[1:] = numpy.cumsum(numpy.sqrt((self.__xpts[1:]-self.__xpts[:-1])**2 + (self.__ypts[1:]-self.__ypts[:-1])**2))
        
        if len(xpts) > 3:        
            self._interp_x = interp1d(self.__dist, self.__xpts, kind='cubic')
            self._interp_y = interp1d(self.__dist, self.__ypts, kind='cubic')
            
        elif len(xpts) > 1:
            #at lease four points are required for spline interpolation - so below
            #this we just use linear
            self._interp_x = interp1d(self.__dist, self.__xpts, kind='linear')
            self._interp_y = interp1d(self.__dist, self.__ypts, kind='linear')
    
    
    
    def get_n_points(self, n):
        """
        Returns an n by 2 array of of x y coordinates of points on the spline.
        """
        result = numpy.zeros((n,2), dtype='float')
        
        pts = numpy.linspace(0, self.__dist[-1],n)
        
        result[:,0] = self._interp_x(pts)
        result[:,1] = self._interp_y(pts)
        
        return result
    
    
    
    def get_poly_approx(self, n=-1):
        """
        Returns a tuple of arrays (startpoints, vectors, normals)
        """
        if n < 1 and n != -1:
            raise ValueError("n must be greater than 1 (or -1 for defaults)")

        if len(self.__dist) < 4 and n == -1:
            pts = numpy.zeros((len(self.__dist),2), dtype='float')
            pts[:,0] = self.__xpts
            pts[:,1] = self.__ypts
        
        elif n == -1:
            #make each polygon segment approx 1 pixel in size
            n = int(round(self.__dist[-1],0))
            
            pts = self.get_n_points(n+1)
            
        else:
            pts = self.get_n_points(n+1)
        
        vectors = pts[1:] - pts[:-1]
        
        normals = numpy.cross(vectors, numpy.array([0.0,0.0,self.direction]))
        normals /= numpy.sqrt((normals ** 2).sum(-1))[..., numpy.newaxis]
        normals = numpy.array(normals[...,:2]) #only return the xy components of the normals
        
        #only return the xy components of the normals
        return pts[:-1], vectors, normals


def find_flux_contributions(flow, integration_line, poly_approx=-1):
    
    int_pts, int_vecs, int_norms = integration_line.get_poly_approx(n=poly_approx)
    
    xsize = flow.shape[0]
    ysize = flow.shape[1]
    zsize = int_pts.shape[0] #same as number of line segments in the poly approx
    
    #create an array of start pts for the flow vectors
    flow_pts_x, flow_pts_y = numpy.meshgrid(numpy.arange(xsize), 
                                              numpy.arange(ysize), 
                                              indexing='xy',dtype='float')
    
    flow_pts_x = flow_pts_x.reshape((xsize, ysize, 1, 1))
    flow_pts_y = flow_pts_y.reshape((xsize, ysize, 1, 1))
    flow_pts = numpy.concatenate((flow_pts_x, flow_pts_y),-1)
    
    #reshape the arrays of vectors
    int_pts = int_pts.reshape((1, 1, zsize, 2))
    flow = flow.reshape((xsize, ysize, 1, 2))
    int_vecs = int_vecs.reshape((1, 1, zsize, 2))
    int_norms = int_norms.reshape((1, 1, zsize, 2))
    
    #flows of zero should be replaced by a small value to prevent division by
    #zero errors
    flow[numpy.where(flow == 0)] = 1e-10
    
    #calculate the intercept parameters
    b = numpy.ones((xsize, zsize, ysize,1), dtype='float')
    denom = numpy.cross(int_vecs,flow)
    valid_idxs = numpy.nonzero(denom)
    b[:,:,:,0][valid_idxs] = numpy.cross(flow_pts - int_pts, flow)[valid_idxs] / denom[valid_idxs]
        
    b = b.swapaxes(1,2)

    a = b * (int_vecs/flow) - ((flow_pts - int_pts)/flow)
    
    a = a[:,:,:,0]
    b = b[:,:,:,0]
    
    #create a mask for the flow vectors which intercept the integration line
    a_criteria = numpy.logical_and(a <= 1.0, a >= 0.0)
    b_criteria = numpy.logical_and(b <= 1.0, b >= 0.0)
    mask = numpy.zeros_like(a)
    mask_idxs = numpy.where(numpy.logical_and(b_criteria, a_criteria))
    
    mask[mask_idxs] = 1.0
    
    #now calculate if the contribution was positive or negative
    sign = numpy.sign(numpy.dot(flow[:,:,0,:], int_norms[0,0,:,:].T))
    
    mask *= sign
    
    #collapse the mask along the z-direction such that each element in the array
    #simply gives the sign of the contribution for that pixel in the image
    mask = numpy.sum(mask, axis=-1)
    
    #sanity check - no pixel in the image should contribute more than once 
    #(or less than minus once) to the total flux
    assert numpy.all(numpy.fabs(mask) <= 1), "Multiple contributions to the flux from the same pixel detected. Please send the offending image and your plumetrack configuration file to the plumetrack developers."
    
    return mask




    
class FluxEngine(object):
    def __init__(self, config):
        
        xpts, ypts = zip(*config['integration_line'])
        
        self.__int_line = Spline2D(xpts, ypts, config['integration_direction'])
        
        self.__pixel_size = config['pixel_size']
        self.__conversion_factor = config['flux_conversion_factor']
    
    
    def get_integration_line(self):
        return self.__int_line
    
    
    def compute_flux(self, current_image, flow, delta_t):
        
        
        #convert the pixel values into mass of SO2
        so2_masses_kg = current_image * self.__pixel_size**2 * self.__conversion_factor
        
        #find the pixels which contribute to the flux
        contributing_pixels = find_flux_contributions(flow, self.__int_line)
        
        #sum all the contributing pixels (taking into account whether they were
        #a positive or negative contribution)
        total_so2_mass = numpy.sum(so2_masses_kg * contributing_pixels)
        
        #convert to flux
        flux = total_so2_mass / delta_t
        
        return flux
    
    
    
    
    
    