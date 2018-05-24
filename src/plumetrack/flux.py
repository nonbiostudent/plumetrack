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
import math
import collections

#new data type to hold a value and its associated error
ValueAndError = collections.namedtuple('ValueAndError', ('value','error'))


class IntegrationLine:
    def __init__(self, name,xpts, ypts, direction):
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
        self.name = name
        
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


def create_flux_engine(config):
    """
    Returns a flux engine object based on the values in config.
    """
    if config['integration_method'] == '2d':
        return FluxEngine2D(config)
    
    elif config['integration_method'] == '1d':
        return FluxEngine1D(config)
    
    else:
        raise ValueError("Unknown integration method \"\". Expecting either \"1d\" or \"2d\".")



class FluxEngineBase(object):
    def __init__(self, config):
        """
        Base class for flux engine classes. Creates integration lines based on 
        the values in config. Subclasses must override the compute_flux method.
        """
        self._int_lines = []
        
        for int_line_cfg in config['integration_lines']:
            xpts, ypts = zip(*int_line_cfg['integration_points'])
            
            xpts = [i/config['downsizing_factor'] for i in xpts]
            ypts = [i/config['downsizing_factor'] for i in ypts]
            
            self._int_lines.append(IntegrationLine(int_line_cfg['name'], xpts, ypts, int_line_cfg['integration_direction']))
        
        self._pixel_size = config['pixel_size'] * config['downsizing_factor']
        self._conversion_factor = config['flux_conversion_factor']
        self._low_pix_threshold = config['integration_pix_threshold_low']
    
    
    def get_integration_lines(self):
        """
        Returns a list of IntegrationLine objects that were defined in the config.
        """
        return self._int_lines
    
    
    def compute_flux(self, current_image, flow, delta_t):
        """
        Should be implemented by subclasses.
        """
        raise TypeError("FluxEngineBase must be subclassed, and the "
                        "compute_flux() method should be defined in the "
                        "subclass.")
    

def compute_error_map(current_image, next_image, flow):
    """
    This function attempts to estimate the error associated with an image pair 
    and their corresponding motion field. It works by considering conservation of
    mass. For each pixel in current_image, it uses the motion vector to compute
    where the mass of SO2 in the pixel should end up - eventually creating a 
    "modelled next image". This is then compared to the real next image to 
    estimate the error. The motion field is then used to map the errors back 
    onto their source pixels in current_image.
    """
    flat_len = numpy.prod(current_image.shape)
    
    flat_error_map = numpy.zeros(flat_len, dtype='float')
    
    src_coords = numpy.dstack(numpy.meshgrid(numpy.arange(current_image.shape[0]),numpy.arange(current_image.shape[1]), indexing='ij'))

    primary_dest_coords = src_coords + flow[...,::-1] #reverse x and y flows since we are dealing with row and columns now
    
    #calculate the fractional contribution to each destination pixel
    fraction = ((primary_dest_coords + 1).astype('int') - primary_dest_coords)
    
    #convert the destination coordinates into coordinates for a flattened image
    flat_dest_coords = (primary_dest_coords[...,1].astype('int').ravel() + 
                        primary_dest_coords[...,0].astype('int').ravel() * current_image.shape[1])
    
    #add up the various contributions. Note that this is slightly complicated by the fact 
    #that multiple pixels in the current image can contribute to the pixels in the next
    #image. This means that our dest_coords array can contain duplicate entries, and so
    #we have to use the bincount function to add it to our error map.
    
    #11 contribution
    dest_coords = flat_dest_coords
    valid_mask = numpy.where(numpy.logical_and(dest_coords > 0, dest_coords < flat_len))
    contribution = (current_image * fraction[...,0] * fraction[...,1]).ravel()
    flat_error_map += numpy.bincount(dest_coords[valid_mask],weights=contribution[valid_mask], minlength=flat_len)
    
    #12 contribution
    dest_coords = flat_dest_coords + 1 #plus one column
    valid_mask = numpy.where(numpy.logical_and(dest_coords > 0, dest_coords < flat_len))
    contribution = (current_image * fraction[...,0] * (1.0 - fraction[...,1])).ravel()
    flat_error_map += numpy.bincount(dest_coords[valid_mask], weights=contribution[valid_mask], minlength=flat_len)
    
    #21 contribution
    dest_coords = flat_dest_coords + current_image.shape[1] #plus one row
    valid_mask = numpy.where(numpy.logical_and(dest_coords > 0, dest_coords < flat_len))
    contribution = (current_image * (1.0 - fraction[...,0]) * fraction[...,1]).ravel()
    flat_error_map += numpy.bincount(dest_coords[valid_mask], weights=contribution[valid_mask], minlength=flat_len)
    
    #22 contribution
    dest_coords = flat_dest_coords + current_image.shape[1] + 1#plus one row and one col
    valid_mask = numpy.where(numpy.logical_and(dest_coords > 0, dest_coords < flat_len))
    contribution = (current_image * (1.0 - fraction[...,0]) * (1.0 - fraction[...,1])).ravel()
    flat_error_map += numpy.bincount(dest_coords[valid_mask], weights=contribution[valid_mask], minlength=flat_len)
    
    error_map = flat_error_map.reshape(current_image.shape)
    
    error_map -= next_image
    
    percentage_errors = numpy.zeros_like(error_map)
    valid_mask = numpy.where(next_image != 0)
    percentage_errors[valid_mask] = numpy.abs(100 * error_map[valid_mask] / next_image[valid_mask])
    
    #error map now contains the computed error in next_image following the motion
    #however, what we want is a map of where this error originated from (i.e. 
    #the error in current_image). So, we now invert the error map, splitting the
    #error in each pixel in next_image between the pixels in current_image that
    #contributed to it. 
    flat_err_map = percentage_errors.ravel()
    
    flat_inverted_error_map = numpy.zeros_like(flat_err_map)
    
    #11 contribution
    dest_coords = flat_dest_coords
    valid_mask = numpy.where(numpy.logical_and(dest_coords > 0, dest_coords < flat_len))
    flat_inverted_error_map[valid_mask] += (fraction[...,0] * fraction[...,1]).ravel()[valid_mask] * flat_err_map[dest_coords[valid_mask]]
    
    #12 contribution
    dest_coords = flat_dest_coords + 1 #plus one column
    valid_mask = numpy.where(numpy.logical_and(dest_coords > 0, dest_coords < flat_len))
    flat_inverted_error_map[valid_mask] += (fraction[...,0] * (1.0 - fraction[...,1])).ravel()[valid_mask] * flat_err_map[dest_coords[valid_mask]]

    #21 contribution
    dest_coords = flat_dest_coords + current_image.shape[1] #plus one row
    valid_mask = numpy.where(numpy.logical_and(dest_coords > 0, dest_coords < flat_len))
    flat_inverted_error_map[valid_mask] += ((1.0 - fraction[...,0]) * fraction[...,1]).ravel()[valid_mask] * flat_err_map[dest_coords[valid_mask]]

    #22 contribution
    dest_coords = flat_dest_coords + current_image.shape[1] + 1#plus one row and one col
    valid_mask = numpy.where(numpy.logical_and(dest_coords > 0, dest_coords < flat_len))
    flat_inverted_error_map[valid_mask] += ((1.0 - fraction[...,0]) * (1.0 - fraction[...,1])).ravel()[valid_mask] * flat_err_map[dest_coords[valid_mask]]

    
    #returns % errors.
    return flat_inverted_error_map.reshape(current_image.shape)
    


class FluxEngine1D(FluxEngineBase):
    
    def __init__(self, config):
        """
        One dimensional flux calculation engine. This works by multiplying each 
        pixel on the integration line by its corresponding velocity and then 
        integrating along the line. This is the "traditional" flux calculation 
        method.
        """
        super(FluxEngine1D, self).__init__(config)
    
    
    def compute_flux(self, current_image, next_image,flow, delta_t):
        """
        Returns the fluxes and associated errors across each defined integration 
        line.
        """
        if flow[...,0].shape != current_image.shape:
            raise ValueError("The image has a different shape %s to the flow "
                             "array %s"%(str(current_image.shape), str(flow[...,0].shape)))
               
        #calculate the errors associated with the image pair and flow field
        pix_errors = compute_error_map(current_image, next_image, flow)
        
        #convert the displacements to velocities in m/s
        flow *= (self._pixel_size / delta_t)
        
        #interpolate the current image and error values to find the values at 
        #the points on the integration line
        image_interp = interp2d(numpy.arange(current_image.shape[1]), 
                                numpy.arange(current_image.shape[0]), 
                                current_image, copy=False, fill_value=0.0)
        
        errors_interp = interp2d(numpy.arange(current_image.shape[1]), 
                                numpy.arange(current_image.shape[0]), 
                                pix_errors, copy=False, fill_value=0.0)
               
        #interpolate the flow field to find the velocities on the integration
        #line
        x_flow_interp = interp2d(numpy.arange(flow.shape[1]), 
                                 numpy.arange(flow.shape[0]), 
                                 flow[...,0], copy=False, fill_value=0.0)
        
        y_flow_interp = interp2d(numpy.arange(flow.shape[1]), 
                                 numpy.arange(flow.shape[0]), 
                                 flow[...,1], copy=False, fill_value=0.0)
        
        #now compute the flux for each integration line in the list
        total_fluxes = []
        for integration_line in self._int_lines:
            
            #work out how many segments to split the integration line into, to get 
            #approximately single pixel resolution
            line_length = integration_line.get_length()
            number_of_segments = int(round(line_length, 0))
            
            int_pts, int_vecs, int_norms = integration_line.get_poly_approx(n=number_of_segments) 
            
            #calculate the mid-points of each line segment
            mid_points = int_pts + (0.5*int_vecs)
            
            pix_vals = numpy.zeros((number_of_segments,), dtype='float')
            err_vals = numpy.zeros((number_of_segments,), dtype='float')
            velocities = numpy.zeros((number_of_segments,2), dtype='float')
            
            #note that we have to do this in a for loop rather than calling the 
            #interpolator with arrays of values - because the mid-points may not be
            #sorted (or even sortable - e.g. the x coordinates may increase as the 
            #y coordinates decrease)
            for i in range(number_of_segments):
                x_coord = mid_points[i,0]
                y_coord = mid_points[i,1]
                pix_vals[i] = image_interp(x_coord, y_coord) 
                err_vals[i] = errors_interp(x_coord, y_coord)       
                velocities[i,0] = x_flow_interp(x_coord, y_coord)
                velocities[i,1] = y_flow_interp(x_coord, y_coord)
            
            #find component of velocities perpendicular to integration line
            perp_vel = numpy.diag(numpy.dot(velocities, int_norms.T))
            
            #caculate flux
            line_length_metres = line_length * self._pixel_size
            fluxes = pix_vals * self._conversion_factor * perp_vel * (line_length_metres / float(number_of_segments))#self._pixel_size
            
            #sanity check
            assert fluxes.shape == (number_of_segments,),"incorrect shape for fluxes array %s, expecting %s"%(str(fluxes.shape), str((number_of_segments,)))
            
            #only sum the values with pixel values above the low pixel threshold
            if self._low_pix_threshold > -1:
                mask = numpy.where(pix_vals > self._low_pix_threshold)
                total_flux = numpy.sum(fluxes[mask])
                
                #total error is quadrature sum of pixel errors
                error = math.sqrt(numpy.sum(((err_vals[mask]/100.0) * fluxes[mask])**2))
                error = (error/total_flux) * 100.0 #convert to percentage
            else:
                total_flux = numpy.sum(fluxes)
                error = math.sqrt(numpy.sum(((err_vals/100.0) * fluxes)**2))
                error = (error/total_flux) * 100.0 #convert to percentage
                
            
            total_fluxes.append(ValueAndError(total_flux, error))
            
        #need to return a tuple NOT a list - since parallel processing uses
        #the flatten() function    
        return tuple(total_fluxes)
        
        
           
class FluxEngine2D(FluxEngineBase):    
    
    def __init__(self, config):
        """
        Two dimensional flux calculation engine. This works by considering the 
        motion of every pixel in the image and computing whether it crosses the 
        integration line or not. This is a more robust method of flux computation
        particularly for images with a large time step between them, or for 
        rapidly moving plumes.
        """
        super(FluxEngine2D, self).__init__(config)
        
        
    def compute_flux(self, current_image, next_image, flow, delta_t):
        """
        Returns the fluxes and associated errors across each defined integration 
        line.
        """
        if flow[...,0].shape != current_image.shape:
            raise ValueError("The image has a different shape %s to the flow "
                             "array %s"%(str(current_image.shape), str(flow[...,0].shape)))
            
        #convert the pixel values into mass of SO2
        so2_masses_kg = current_image * self._pixel_size**2 * self._conversion_factor
        
        #calculate the errors associated with the image pair and flow field
        percent_pix_errors = compute_error_map(current_image, next_image, flow)
        pix_errors = (percent_pix_errors/100.0) * so2_masses_kg
        
        #now compute the flux for each integration line in the list
        total_fluxes = []
        for integration_line in self._int_lines:
            #find the pixels which contribute to the flux
            contributing_pixels = self.find_flux_contributions(flow, integration_line)
            
            #sum all the contributing pixels (taking into account whether they were
            #a positive or negative contribution)
            if self._low_pix_threshold > -1:
                #only sum the values with pixel values above the low pixel threshold
                contributing_pixels[numpy.where(current_image < self._low_pix_threshold)] = 0
            
            total_so2_mass = numpy.sum(so2_masses_kg * contributing_pixels)
            
            error = math.sqrt(numpy.sum((contributing_pixels * pix_errors)**2))
            
            error = 100 * (error/total_so2_mass)
            
            #convert to flux
            flux = total_so2_mass / delta_t
            
            total_fluxes.append(ValueAndError(flux, error))
        
        #need to return a tuple NOT a list - since parallel processing uses
        #the flatten() function
        return tuple(total_fluxes)
    
    
    def find_flux_contributions(self, flow, integration_line, poly_approx=-1):
        """
        For every pixel in the image, computes whether its motion vector 
        crosses the integration line and whether it crosses in a positive or 
        negative direction. Returns an array the same size as the image, where 
        each element is either 1 (positive contribution to flux), 0 (no 
        contribution) or -1 (negative contribution to flux).
        """
        int_pts, int_vecs, int_norms = integration_line.get_poly_approx(n=poly_approx)
        
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
