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
import os
import sys
import numpy
import inspect
import datetime
import importlib


class ImageLoader(object):
    def __init__(self, config):
        """
        Class for loading images. All custom image loaders should inherit from 
        this class and override the load() method to perform any required 
        preprocessing.
        """
        self.config = config
        self.__fname_fmt = config['filename_format']
        
    
    def can_load(self, filename):
        """
        Returns True if it looks like this file can be opened by the loader, 
        False otherwise.
        """
        if not filename.endswith(self.config["file_extension"]):
            return False
        
        try:
            self.time_from_fname(filename)
        except ValueError:
            return False
        
        return True
        
        
    def time_from_fname(self, filename):
        """
        Given the filename of an image, returns a datetime object representing
        the capture time of the image.
        """
        return datetime.datetime.strptime(os.path.basename(filename), 
                                          self.__fname_fmt)
    
    
    def _load_and_check(self, filename):
        """
        Calls self.load() on the supplied filename and then checks that the 
        returned image has the required properties (i.e. only one channel, 
        sensible dtype etc.) before returning it along with its capture time.
        
        Subclasses should NOT override this method - it is here to ensure that
        your subclass's load() method is doing the right thing.
        """
        res = self.load(filename)
        
        if not (type(res) in (tuple, list) and #return type is correct
                len(res) == 2 and #returns two values
                type(res[0]) is numpy.ndarray and #image is a numpy array
                type(res[1]) is datetime.datetime): #capture time is a datetime object
            raise ImageLoaderError("Error in the load() method of custom image "
                                   "loader class %s. Expecting a return type of "
                                   "tuple containing a numpy array of the image "
                                   "data and a datetime object of the image "
                                   "capture time."%self.__name__)
        
        if len(res[0].shape) < 2:
            raise ImageLoaderError("Error in the load() method of custom image "
                                   "loader class %s. Returned image array must "
                                   "be two-dimensional."%self.__name__)
        
        if len(res[0].shape) > 2 and res[0].shape[2] != 1:
            raise ImageLoaderError("Error in the load() method of custom image "
                                   "loader class %s. Returned image has too many "
                                   "channels."%self.__name__)
        
        return res
        
        
    def load(self, filename):
        """
        Given the filename of an image returns a tuple of (image, time), where 
        image is a numpy array containing the pixel data of the image, and time
        is a datetime object representing the capture time of the image.
        
        Subclasses should override this method to perform any preprocessing that
        is required.
        """
        
        im = cv2.imread(filename, cv2.IMREAD_UNCHANGED)
        t = self.time_from_fname(filename)
        
        return im,t


class ImageLoaderError(Exception):
    pass


def validate_loader(config):
    """
    Returns True if the config contains a valid value for the custom_image_loader
    (and the custom loader can be created successfully), False otherwise.
    """
    
    try:
        get_image_loader(config)
        return True
    except:
        return False
    


def get_image_loader(config):
    """
    Returns an image loader object as defined in the config. This may be the 
    default loader, or a custom one if that has been specified in the configuration.
    """
    if config["custom_image_loader"] == "":
        return ImageLoader(config)
    
    folder, module_file = os.path.split(config["custom_image_loader"])
    
    #set the system path to the folder where the module lives
    old_sys_path = sys.path
    if folder != "":
        sys.path = [folder] + sys.path
    
    try:
        #import the module
        mod_name = os.path.splitext(module_file)[0]
        mod = importlib.import_module(mod_name)
        
    finally:
        #reset system path again
        sys.path = old_sys_path
        
    #search the module for valid loader classes
    isvalid_loader = lambda x: inspect.isclass(x) and issubclass(x, ImageLoader) and x != ImageLoader
    loaders = [c for c in mod.__dict__.values() if isvalid_loader(c)]

    if len(loaders) == 0:
        raise ImageLoaderError("File %s did not contain any ImageLoader classes."%module_file)
    
    if len(loaders) > 1:
        raise ImageLoaderError("File \"%s\" contains multiple ImageLoader classes"%module_file)
    
    return loaders[0](config)
    
    
    

