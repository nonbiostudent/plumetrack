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

import cv2
import numpy
import numpy.random
import calendar
import Image

def date2secs(d):
    return calendar.timegm(d.timetuple())+d.microsecond/1e6

class MotionEngine(object):
    def __init__(self, config):
        
        self.low_thresh = config['threshold_low']
        self.high_thresh = config['threshold_high']
        self.pix_size = config['pixel_size']
        self.__random_image = None
        self.random_level = config['random_level']
        self.__mask_im = numpy.array(Image.open(config['mask_image']).convert('L'))
        
        self.pyr_scale = config['farneback_pyr_scale']
        self.levels = config['farneback_levels']
        self.winsize = config['farneback_winsize']
        self.iterations = config['farneback_iterations']
        self.poly_n = config['farneback_poly_n']
        self.poly_sigma = config['farneback_poly_sigma']
        
    
    
    def preprocess(self, image):
        
        if self.__random_image is None:
            self.__random_image = numpy.random.rand(*image.shape) * self.random_level
        else:
            if image.shape != self.__random_image.shape:
                print image.shape, self.__random_image.shape
                raise ValueError("Image is a different size to previously "
                                 "preprocessed images.")
        
        thresh_criteria = numpy.logical_or(image < self.low_thresh, 
                                           image > self.high_thresh)
        
        mask_criteria = (self.__mask_im == 0)
        
        
        mask_idx = numpy.where(numpy.logical_or(thresh_criteria, mask_criteria))
        masked_im = numpy.array(image)
        
        masked_im[mask_idx] = self.__random_image[mask_idx]
        
        return masked_im



    def compute_motion_field(self, current_image, next_image, 
                             current_capture_time, next_capture_time):
        
        flow = cv2.calcOpticalFlowFarneback(current_image, next_image, 
                                            self.pyr_scale,
                                            self.levels,
                                            self.winsize,
                                            self.iterations,
                                            self.poly_n,
                                            self.poly_sigma,
                                            flags=cv2.OPTFLOW_FARNEBACK_GAUSSIAN)
    
        #convert to m/s
        delta_t = date2secs(next_capture_time) - date2secs(current_capture_time)
        velocities = self.pix_size * flow / delta_t
        
        return velocities
        
        
        
        
        