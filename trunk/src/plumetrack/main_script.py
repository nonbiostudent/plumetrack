#!/usr/bin/python

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

import datetime
import os.path
import numpy
import Image
import multiprocessing
import itertools
import calendar

from plumetrack import settings
from plumetrack import dir_iter
from plumetrack import motion
from plumetrack import flux
from plumetrack import output


############################################################################

def date2secs(d):
    """
    Converts a datetime object into floating point number of seconds since the
    epoch.
    """
    return calendar.timegm(d.timetuple())+d.microsecond/1e6

############################################################################
 
def __run_func(func,q,l,args,kwargs):
    """
    To make parallel_process compatible with Windows, the function passed to
    the Process constructor must be pickleable. It cannot therefore be a 
    lambda function and so __run_func is defined instead.
    """
    q.put([func(i,*args,**kwargs) for i in l])
        
############################################################################    
      
def parallel_process(func, list_, *args, **kwargs):
    """
    Runs the function 'func' on all items in list_ passing any additional
    args or kwargs specified. The list elements are processed asyncronously
    by as many processors as there are cpus. The return value will be a list
    of the return values of the function in the same order as the input list.
    """    
    if len(list_) == 0:
        return []
     
    results = []
    processes = []
    queues = []
     
    for l in unsplice(list_,multiprocessing.cpu_count()):
        q = multiprocessing.Queue(0)
        p = multiprocessing.Process(target=__run_func,args=(func,q,l,args,kwargs))
        p.start()
        processes.append(p)
        queues.append(q)
     
    for i in range(len(processes)):        
        results.append(queues[i].get())
        processes[i].join()
     
    return splice(results)
 
############################################################################
 
def splice(l):
    """
    Performs a round-robin joining of iterables.
     
    >>> print splice([[1, 2, 3],['a', 'b'],[100, 300, 400, 500]])
    [1, 'a', 100, 2, 'b', 300, 3, 400, 500]
    """
    sentinel = object()
    it = itertools.chain.from_iterable(itertools.izip_longest(*l,fillvalue=sentinel))
    return [i for i in it if i is not sentinel]
 
############################################################################
 
def unsplice(l, n):
    """
    Splits a list into n sublists in the following way:
     
    >>> print unsplice(range(10), 3)
    [[0, 3, 6, 9], [1, 4, 7], [2, 5, 8]]
    >>> print splice(unsplice(range(10), 3)) == range(10)
    True
    >>> print unsplice([0, 1], 3)
    [[0], [1]]
    >>> print unsplice([], 2)
    []
     
    This operation can be undone using the splice() function.
    """
    n = min(n, len(l))
    return [l[i::n] for i in range(n)]
 
############################################################################
 

# Main program loop 
def main():
    
    #read the user supplied values from the command line
    options, args = settings.parse_cmd_line()
    image_dir = args[0]
     
    #load all the settings from the configuration file
    config = settings.load_config_file(filename=options.config_file)
     
    #define a function to extract the capture time of an image from its filename
    time_from_fname = lambda fname: datetime.datetime.strptime(os.path.basename(fname), 
                                                               config['filename_format'])
    
    #define a comparator function for ordering UV images by capture time - again
    #we define this within the main() function since it depends on the contents
    #of the config file
    compare_by_time = lambda f1,f2: cmp(time_from_fname(f1), time_from_fname(f2))
    
    #define a function to test if a file is a UV image - we define this within
    #main since it depends on the contents of the config file
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
    
    def process_image_pair(im_pair, motion_engine, flux_engine):
        im1 = im_pair[0]
        im2 = im_pair[1]
         
        current_capture_time = time_from_fname(im1)
        current_image = numpy.array(Image.open(im1)) 
        current_masked_im = motion_engine.preprocess(current_image)
         
        next_capture_time = time_from_fname(im2)
        next_image = numpy.array(Image.open(im2)) 
        next_masked_im = motion_engine.preprocess(next_image)
        
        delta_t = date2secs(next_capture_time) - date2secs(current_capture_time)
         
        flow = motion_engine.compute_flow(current_masked_im, next_masked_im)
             
        if options.png_output_folder is not None:
            if not os.path.isdir(options.png_output_folder):
                os.makedirs(options.png_output_folder)
             
            output_filename = os.path.join(options.png_output_folder, os.path.basename(im1).rstrip(config['file_extension'])+'.png')
             
            output.create_motion_png(current_masked_im, flow, output_filename, flux_engine.get_integration_line())
        
        #only include pixels in the non-masked regions in the flux calculation
        current_image[numpy.where(current_image != current_masked_im)] = 0.0
         
        so2_flux = flux_engine.compute_flux(current_image, flow, delta_t) 
         
        return so2_flux



    motion_engine = motion.MotionEngine(config)
     
    flux_engine = flux.FluxEngine(config)
     
    image_iter = dir_iter.DirFileIter(image_dir, realtime=options.realtime, 
                                      skip_existing=options.skip_existing, 
                                      recursive=options.recursive, 
                                      sort_func=compare_by_time, 
                                      test_func=is_uv_image) 
    
    #set an exit handler if we are working in realtime - otherwise it can hang
    #forever.
    if options.realtime:
        def _quit(*args):
            image_iter.close()
        
        import signal
        
        signal.signal(signal.SIGINT, _quit)
        
    
    if options.realtime or not options.parallel:
        #main loop for realtime processing
        current_image_fname = None
        
        if options.output_file is not None:
            #create a blank file which we later append to
            with open(options.output_file,'w') as ofp:
                pass
         
        for next_image_fname in image_iter:
             
            if current_image_fname is not None:
                so2flux = process_image_pair((current_image_fname, next_image_fname),
                                          motion_engine, flux_engine)
                
                if options.output_file is not None:
                    with open(options.output_file,'a') as ofp:
                        ofp.write("%s\t%f\n"%(str(time_from_fname(current_image_fname)),so2flux))
                else:
                    print "%s\t%f"%(str(time_from_fname(current_image_fname)),so2flux)
                 
            current_image_fname = next_image_fname
     
    else:
        #main loop for parallel processing
        files = [f for f in image_iter]
        file_pairs = zip(files[:-1], files[1:])
         
        fluxes = parallel_process(process_image_pair, file_pairs, motion_engine, 
                                  flux_engine)
        
        if options.output_file is not None:
            with open(options.output_file,'w') as ofp:
                for i in range(len(fluxes)):
                    ofp.write("%s\t%f\n"%(str(time_from_fname(files[i])),fluxes[i]))
        else:
            for i in range(len(fluxes)):
                print "%s\t%f"%(str(time_from_fname(files[i])),fluxes[i])
        
        
