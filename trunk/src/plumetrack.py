#!/usr/bin/python

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

import datetime
import os.path
import numpy
import Image
from std_ops.iter_ import parallel_process

from plume_track import settings
from plume_track import dir_iter
from plume_track import motion
from plume_track import flux
from plume_track import output


#read the user supplied values from the command line
options, args = settings.parse_cmd_line()
image_dir = args[0]

#load all the settings from the configuration file
config = settings.load_config_file(filename=options.config_file)



#function to extract the capture time of an image from its filename
time_from_fname = lambda fname: datetime.datetime.strptime(os.path.basename(fname), 
                                                           config['filename_format'])

def is_uv_image(filename):
    """
    Function returns True if the filename has the format which we expect for a 
    UV image.
    """
    if not filename.endswith(config['file_extension']):
        return False
    try:
        time_from_fname(filename)
    except:
        return False
    return True


def compare_by_time(f1, f2):
    """
    Comparator function for sorting UV images by capture time.
    """
    t1 = time_from_fname(f1)
    t2 = time_from_fname(f2)
    return cmp(t1,t2)



motion_engine = motion.MotionEngine(config)

flux_engine = flux.FluxEngine(config)

image_iter = dir_iter.DirFileIter(image_dir, realtime=options.realtime, 
                                  skip_existing=options.skip_existing, 
                                  recursive=options.recursive, 
                                  sort_func=compare_by_time, 
                                  test_func=is_uv_image)


# Main program loop for realtime processing
if __name__ == '__main__':
    if options.realtime or not options.parallel:
        current_image = None
        current_masked_im = None
        current_image_fname = None
        
        for next_image_fname in image_iter:
            print next_image_fname
            next_capture_time = time_from_fname(next_image_fname)
            
            next_image = numpy.array(Image.open(next_image_fname))
            
            next_masked_im = motion_engine.preprocess(next_image)
            
            if current_image is not None:
            
                print "Processing %s and %s"%(current_capture_time, next_capture_time)
                
                velocities = motion_engine.compute_motion_field(current_masked_im, 
                                                                next_masked_im, 
                                                                current_capture_time, 
                                                                next_capture_time)
                
                if options.png_output_folder is not None:
                    if not os.path.isdir(options.png_output_folder):
                        os.makedirs(options.png_output_folder)
                    
                    output_filename = os.path.join(options.png_output_folder, os.path.basename(current_image_fname).rstrip(config['file_extension'])+'.png')
                    
                    output.create_motion_png(current_masked_im, velocities, output_filename)
                
                so2_flux = flux_engine.compute_flux(current_image, current_capture_time,
                                                    velocities)
                
                print "flux = ", so2_flux
            
            current_image = next_image
            current_masked_im = next_masked_im
            current_capture_time = next_capture_time 
            current_image_fname = next_image_fname
    
    else:
        #main loop for parallel processing
        
        def process(im_pair):
            im1 = im_pair[0]
            im2 = im_pair[1]
            
            current_capture_time = time_from_fname(im1)
            current_image = numpy.array(Image.open(im1)) 
            current_masked_im = motion_engine.preprocess(current_image)
            
            next_capture_time = time_from_fname(im2)
            next_image = numpy.array(Image.open(im2)) 
            next_masked_im = motion_engine.preprocess(next_image)
            
            velocities = motion_engine.compute_motion_field(current_masked_im, 
                                                                next_masked_im, 
                                                                current_capture_time, 
                                                                next_capture_time)
                
            if options.png_output_folder is not None:
                if not os.path.isdir(options.png_output_folder):
                    os.makedirs(options.png_output_folder)
                
                output_filename = os.path.join(options.png_output_folder, os.path.basename(im1).rstrip(config['file_extension'])+'.png')
                
                output.create_motion_png(current_masked_im, velocities, output_filename)
            
            so2_flux = flux_engine.compute_flux(current_image, current_capture_time,
                                                velocities) 
            
            return so2_flux
        
        files = [f for f in image_iter]
        file_pairs = zip(files[:-1], files[1:])
        
        fluxes = parallel_process(process, file_pairs)
