#Copyright (C) Nial Peters 2014
#
#This file is part of plumetrack.
#
#plumetrack is free software: you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.
#
#plumetrack is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with plumetrack.  If not, see <http://www.gnu.org/licenses/>.
from scipy.interpolate import interp1d
import numpy


class Spline2D:
    def __init__(self, xpts, ypts):
        
        if len(xpts) != len(ypts):
            raise ValueError("xpts and ypts must contain the same number of elements")
        
        if len(xpts) < 2:
            raise ValueError("At least 2 points are required for interpolation")
        
        xpts = numpy.asarray(xpts)
        ypts = numpy.asarray(ypts)
        
        self.__dist = numpy.zeros_like(xpts)
        self.__dist[1:] = numpy.cumsum(numpy.sqrt((xpts[1:]-xpts[:-1])**2 + (ypts[1:]-ypts[:-1])**2))
        
        if len(xpts) > 3:        
            self._interp_x = interp1d(self.__dist, xpts, kind='cubic')
            self._interp_y = interp1d(self.__dist, ypts, kind='cubic')
            
        elif len(xpts) > 1:
            #at lease four points are required for spline interpolation - so below
            #this we just use linear
            self._interp_x = interp1d(self.__dist, xpts, kind='linear')
            self._interp_y = interp1d(self.__dist, ypts, kind='linear')
    
    
    
    def get_n_points(self, n):
        """
        Returns an n by 2 array of of x y coordinates of points on the spline.
        """
        result = numpy.zeros((n,2), dtype='float')
        
        pts = numpy.linspace(0, self.__dist[-1],n)
        
        result[:,0] = self._interp_x(pts)
        result[:,1] = self._interp_y(pts)
        
        return result
    
    
    
    def get_poly_approx(self, n=-1, z=-1.0):
        """
        Returns a tuple of arrays (startpoints, vectors, normals)
        """
        if n == -1:
            #make each polygon segment approx 1 pixel in size
            n = int(round(self.__dist[-1],0))
        elif n < 1:
            raise ValueError("n must be greater than 1 (or -1 for defaults)")
        
        pts = self.get_n_points(n+1)
        
        vectors = pts[1:] - pts[:-1]
        

        normals = numpy.cross(vectors, numpy.array([0.0,0.0,z]))
        normals /= numpy.sqrt((normals ** 2).sum(-1))[..., numpy.newaxis]
        
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
    
    #calculate the intercept parameters
    b = numpy.cross(flow_pts - int_pts, flow) / numpy.cross(int_vecs,flow)
    b = b.swapaxes(1,2)
    b = b.reshape(xsize, ysize, zsize,1)
    a = b * (int_vecs/flow) - ((flow_pts - int_pts)/flow)
    
    a = a[:,:,:,0]
    b = b[:,:,:,0]
    
    #create a mask for the flow vectors which intercept the integration line
    a_criteria = numpy.logical_and(a <= 1.0, a >= 0.0)
    b_criteria = numpy.logical_and(b <= 1.0, b >= 0.0)
    mask = numpy.zeros_like(a)
    mask[numpy.where(numpy.logical_and(b_criteria, a_criteria))] = 1.0
    
    
    #now calculate if the contribution was positive or negative
    sign = numpy.sign(numpy.dot(flow, int_norms))
    
    mask *= sign
    
    return mask



def calc_flux(image, mask, delta_t):
    #TODO
    pass

    
class FluxEngine(object):
    def __init__(self, config):
        pass
    def compute_flux(self, current_image, current_capture_time, velocities):
        return None