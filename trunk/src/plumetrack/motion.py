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

import plumetrack



class MotionEngine(object):
    def __init__(self, config):
        """
        Class providing methods for computing the flow field that maps pixels in
        one image to pixels in a consecutive image. The config argument should be
        a dict of configuration options (as returned from settings.load_config_file()).
        """
        self.low_thresh = config['threshold_low']
        self.high_thresh = config['threshold_high']
        self.__random_image = None
        self.random_mean = config['random_mean']
        self.random_sigma = config['random_sigma']
        self.downsizing_factor = config['downsizing_factor']
        
        if config['mask_image'] != "":
            self.__mask_im = cv2.imread(config['mask_image'], cv2.IMREAD_GRAYSCALE)
            
            #if we are using downsizing - then rescale the mask image
            if self.downsizing_factor != 1.0:
                new_x = int(round(self.__mask_im.shape[0] / self.downsizing_factor))
                new_y = int(round(self.__mask_im.shape[1] / self.downsizing_factor))
                
                self.__mask_im = cv2.resize(self.__mask_im, (new_x,new_y))
            
            #ensure the loaded mask has the correct data type
            self.__mask_im = self.__mask_im.astype(numpy.uint8, copy=False)
        else:
            self.__mask_im = None
        
        self.pyr_scale = config['farneback_pyr_scale']
        self.levels = config['farneback_levels']
        self.winsize = config['farneback_winsize']
        self.iterations = config['farneback_iterations']
        self.poly_n = config['farneback_poly_n']
        self.poly_sigma = config['farneback_poly_sigma']
    
    
    def preprocess(self, image):
        """
        Performs any required preprocessing tasks on the image (should be called
        prior to calling compute_flow()). Depending on the configuration,
        preprocessing tasks may include thresholding the image and applying 
        random noise masking.
         
        The image argument should be a numpy array. Note that the preprocessing
        is done in-place - modifying the array that is passed in.
        
        Returns the mask array (boolean) showing which array elements were 
        replaced with random noise.
        """
        #if we are using downsizing - then rescale the image
        if self.downsizing_factor != 1.0:
            new_x = int(round(image.shape[0] / self.downsizing_factor))
            new_y = int(round(image.shape[1] / self.downsizing_factor))
            
            im_cpy = image.copy()
            
            image.resize((new_x, new_y), refcheck=False)
            
            cv2.resize(im_cpy, (new_x,new_y), image)
        
        if self.__random_image is None:
            if self.random_sigma > 0:
                self.__random_image = numpy.random.normal(self.random_mean, 
                                                          self.random_sigma, 
                                                          size=image.shape)
            else:
                self.__random_image = numpy.ones_like(image) * self.random_mean

        else:
            if image.shape != self.__random_image.shape:
                print image.shape, self.__random_image.shape
                raise ValueError("Image is a different size to previously "
                                 "preprocessed images.")

        if self.high_thresh < 0:
            h_thresh = image.max()
        else:
            h_thresh = self.high_thresh
        
        if self.low_thresh < 0:
            l_thresh = image.min()
        else:
            l_thresh = self.low_thresh
        
        thresh_criteria = numpy.logical_or(image < l_thresh, 
                                           image > h_thresh)
        
        if self.__mask_im is not None:
            mask_criteria = numpy.logical_not(self.__mask_im)
        else:
            mask_criteria = numpy.zeros_like(image)
        
        mask = numpy.logical_or(thresh_criteria, mask_criteria)
        mask_idx = numpy.where(mask)
        
        image[mask_idx] = self.__random_image[mask_idx]
        
        return mask



    def compute_flow(self, current_image, next_image):
        """
        Uses the Farneback algorithm to compute the flow field that maps pixels
        in current_image, to pixels in next_image. Both image arguments should be
        numpy arrays.
        """                             
        return cv2.calcOpticalFlowFarneback(current_image, next_image, 
                                            self.pyr_scale,
                                            self.levels,
                                            self.winsize,
                                            self.iterations,
                                            self.poly_n,
                                            self.poly_sigma,
                                            flags=cv2.OPTFLOW_FARNEBACK_GAUSSIAN)
    
        
if plumetrack.have_gpu():
    from plumetrack import gpu_motion
    
    class GPUMotionEngine(MotionEngine):
        
        def __init__(self, config):
            """
            Subclass of MotionEngine which uses OpenCV's GPU implementation of
            the Farneback algorithm to compute the flow between image frames.
            
            Note that this class is only defined if a CUDA capable GPU is 
            detected on the system and plumetrack has been built with GPU support.
            """
            super(GPUMotionEngine, self).__init__(config)
            
            self.__gpu_interface = gpu_motion.GPUInterface(self.pyr_scale, 
                                                               self.levels,
                                                               self.winsize,
                                                               self.iterations,
                                                               self.poly_n,
                                                               self.poly_sigma)

            
        def compute_flow(self, current_image, next_image):
            """
            Uses the Farneback algorithm to compute the flow field that maps pixels
            in current_image, to pixels in next_image. Both image arguments should be
            numpy arrays.
            
            The computation is done on the GPU which should be much faster than 
            then CPU implementation.
            """
            xflow = numpy.zeros((current_image.shape[0], current_image.shape[1]), dtype='float32')
            yflow = numpy.zeros((current_image.shape[0], current_image.shape[1]), dtype='float32')
            
            self.__gpu_interface.computeFlow(current_image, next_image, xflow, yflow)
            
            flow = numpy.dstack((xflow,yflow))
            if numpy.all(flow == 0):
                print "All zeros!"
            
            return flow
                
        
        
        