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
from scipy.interpolate import interp1d, interp2d
import numpy


class IntegrationLine:
    def __init__(self, xpts, ypts, direction):
        """
        Class to represent an integration line in an image. Note that the xpts and ypts
        are *not* in pixel coordinates, they are in line coordinates - which are pixel boundary
        coordinates where (0,0) is the top left of the image.
        
        For example, for a 512x512 pixel image, if you want a horizontal integration line
        that spans the entire width of the image you would specify its x points as
        [0, 513].
        
        Integration lines can extend beyond the boundaries of the image without 
        problems.
        """
        
        if len(xpts) != len(ypts):
            raise ValueError("xpts and ypts must contain the same number of elements")
        
        if len(xpts) < 2:
            raise ValueError("At least 2 points are required for interpolation")
        
        self.__xpts = numpy.array(xpts, dtype='float')
        self.__ypts = numpy.array(ypts, dtype='float')
        
        self.direction = direction
        self.__dist = numpy.zeros_like(self.__xpts)
        self.__dist[1:] = numpy.cumsum(numpy.sqrt((self.__xpts[1:]-self.__xpts[:-1])**2 + (self.__ypts[1:]-self.__ypts[:-1])**2))
    

        self._interp_x = interp1d(self.__dist, self.__xpts, kind='linear')
        self._interp_y = interp1d(self.__dist, self.__ypts, kind='linear')

    
    
    def get_length(self):
        """
        Returns the cumulative length of all the line segments in pixels (not 
        in metres!)
        """
        return self.__dist[-1]
    
    
    def get_n_points(self, n=-1):
        """
        Returns an n by 2 array of of x y coordinates of points along the line.
        If n==-1 then it returns the actual points of the line rather than
        interpolating. Note that the points returned are in pixel coordinates, 
        *not* line coordinates.
        """
        if n == -1:
            result = numpy.zeros((len(self.__xpts), 2), dtype='float')
            result[:,0] = self.__xpts - 0.5
            result[:,1] = self.__ypts - 0.5
        
        else:
        
            result = numpy.zeros((n,2), dtype='float')
            
            pts = numpy.linspace(0, self.__dist[-1],n)
            
            result[:,0] = self._interp_x(pts) - 0.5
            result[:,1] = self._interp_y(pts) - 0.5
        
        return result
    
    
    def get_poly_approx(self, n=-1):
        """
        Returns a tuple of arrays (startpoints, vectors, normals). Note that the
        points returned are in pixel coordinates, *not* line coordinates.
        """
        if n < 1 and n != -1:
            raise ValueError("n must be greater than 1 (or -1 for defaults)")

        if n == -1:    
            pts = self.get_n_points(n)
            
        else:
            pts = self.get_n_points(n+1)
        
        vectors = pts[1:] - pts[:-1]
        
        normals = numpy.cross(vectors, numpy.array([0.0,0.0,self.direction]))
        normals /= numpy.sqrt((normals ** 2).sum(-1))[..., numpy.newaxis]
        normals = numpy.array(normals[...,:2]) #only return the xy components of the normals
        
        return pts[:-1], vectors, normals



class FluxEngineBase(object):
    def __init__(self, config):
        xpts, ypts = zip(*config['integration_line'])
        
        self._int_line = IntegrationLine(xpts, ypts, config['integration_direction'])
        
        self._pixel_size = config['pixel_size']
        self._conversion_factor = config['flux_conversion_factor']
    
    
    def get_integration_line(self):
        return self._int_line
    
    
    def compute_flux(self, current_image, flow, delta_t):
        raise TypeError("FluxEngineBase must be subclassed, and the "
                        "compute_flux() method should be defined in the "
                        "subclass.")



class FluxEngine1D(FluxEngineBase):
    
    def __init__(self, config):
        super(FluxEngine1D, self).__init__(config)
    
    
    def compute_flux(self, current_image, flow, delta_t):
        
        if flow[...,0].shape != current_image.shape:
            raise ValueError("The image has a different shape %s to the flow "
                             "array %s"%(str(current_image.shape), str(flow[...,0].shape)))
               
        #convert the displacements to velocities in m/s
        flow *= (self._pixel_size / delta_t)
        
        #work out how many segments to split the integration line into, to get 
        #approximately single pixel resolution
        line_length = self._int_line.get_length()
        number_of_segments = int(round(line_length, 0))
        
        int_pts, int_vecs, int_norms = self._int_line.get_poly_approx(n=number_of_segments) 
        
        #calculate the mid-points of each line segment
        mid_points = int_pts + (0.5*int_vecs)
        
        #interpolate the current image to find the pixel values at the points 
        #on the integration line
        image_interp = interp2d(numpy.arange(current_image.shape[1]), 
                                numpy.arange(current_image.shape[0]), 
                                current_image, copy=False, fill_value=0.0)
               
        #interpolate the flow field to find the velocities on the integration
        #line
        x_flow_interp = interp2d(numpy.arange(flow.shape[1]), 
                                 numpy.arange(flow.shape[0]), 
                                 flow[...,0], copy=False, fill_value=0.0)
        
        y_flow_interp = interp2d(numpy.arange(flow.shape[1]), 
                                 numpy.arange(flow.shape[0]), 
                                 flow[...,1], copy=False, fill_value=0.0)
        
        pix_vals = numpy.zeros((number_of_segments,), dtype='float')
        velocities = numpy.zeros((number_of_segments,2), dtype='float')
        
        #note that we have to do this in a for loop rather than calling the 
        #interpolator with arrays of values - because the mid-points may not be
        #sorted (or even sortable - e.g. the x coordinates may increase as the 
        #y coordinates decrease)
        for i in range(number_of_segments):
            x_coord = mid_points[i,0]
            y_coord = mid_points[i,1]
            pix_vals[i] = image_interp(x_coord, y_coord)        
            velocities[i,0] = x_flow_interp(x_coord, y_coord)
            velocities[i,1] = y_flow_interp(x_coord, y_coord)
        
        #find component of velocities perpendicular to integration line
        perp_vel = numpy.diag(numpy.dot(velocities, int_norms.T))
        
        #caculate flux
        line_length_metres = line_length * self._pixel_size
        fluxes = pix_vals * self._conversion_factor * perp_vel * (line_length_metres / float(number_of_segments))#self._pixel_size
        
        #sanity check
        assert fluxes.shape == (number_of_segments,),"incorrect shape for fluxes array %s, expecting %s"%(str(fluxes.shape), str((number_of_segments,)))
        
        total_flux = numpy.sum(fluxes)
        
        return total_flux
        
        
           
class FluxEngine2D(FluxEngineBase):    
    
    def __init__(self, config):
        super(FluxEngine2D, self).__init__(config)
        
        
    def compute_flux(self, current_image, flow, delta_t):
        if flow[...,0].shape != current_image.shape:
            raise ValueError("The image has a different shape %s to the flow "
                             "array %s"%(str(current_image.shape), str(flow[...,0].shape)))
            
        #convert the pixel values into mass of SO2
        so2_masses_kg = current_image * self._pixel_size**2 * self._conversion_factor
        
        #find the pixels which contribute to the flux
        contributing_pixels = self.find_flux_contributions(flow)
        
        #sum all the contributing pixels (taking into account whether they were
        #a positive or negative contribution)
        total_so2_mass = numpy.sum(so2_masses_kg * contributing_pixels)
        
        #convert to flux
        flux = total_so2_mass / delta_t
        
        return flux
    
    
    def find_flux_contributions(self, flow, poly_approx=-1):
    
        int_pts, int_vecs, int_norms = self._int_line.get_poly_approx(n=poly_approx)
        
        xsize = flow.shape[0]
        ysize = flow.shape[1]
        zsize = int_pts.shape[0] #same as number of line segments in the poly approx
        
        #create an array of start pts for the flow vectors
        flow_pts_x, flow_pts_y = numpy.meshgrid(numpy.arange(ysize), 
                                                numpy.arange(xsize), 
                                                indexing='xy',dtype='float')
        
        flow_pts_x = flow_pts_x.reshape((xsize, ysize, 1, 1))
        flow_pts_y = flow_pts_y.reshape((xsize, ysize, 1, 1))
        flow_pts = numpy.concatenate((flow_pts_x, flow_pts_y), -1)
        
        #reshape the arrays of vectors
        int_pts = int_pts.reshape((1, 1, zsize, 2))
        flow = flow.reshape((xsize, ysize, 1, 2))
        int_vecs = int_vecs.reshape((1, 1, zsize, 2))
        int_norms = int_norms.reshape((1, 1, zsize, 2))
        
        #calculate the intercept parameters
        b = numpy.ones((xsize, zsize, ysize,1), dtype='float') * 2.0 #*2 prevents invalid indexes from passing the b_criteria test below
        denom = numpy.cross(int_vecs,flow)
        valid_idxs = numpy.logical_and(denom != 0.0, numpy.isfinite(denom))
        b[:,:,:,0][valid_idxs] = numpy.cross(flow_pts - int_pts, flow)[valid_idxs] / denom[valid_idxs]
            
        b = b.swapaxes(1,2)
        
        #we ignore divide by 0 and multiply by NaN errors since NaN results will
        #fail the 'criteria' tests below anyway.
        with numpy.errstate(divide='ignore', invalid='ignore'):
            a = b * (int_vecs/flow) - ((flow_pts - int_pts)/flow)
        
        a = a[:,:,:,0]
        b = b[:,:,:,0]
        
        #create a mask for the flow vectors which intercept the integration line
        a_criteria = numpy.logical_and(a <= 1.0, a >= 0.0)
        b_criteria = numpy.logical_and(b < 1.0, b >= 0.0) #<1 not <=1 to prevent b_criteria being True for two integration line segments
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
