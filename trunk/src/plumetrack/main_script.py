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
import cv2
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

def time_from_fname(fname, config):
    """
    Returns the capture time of an image file based on its filename.
        * fname - filename of the image
        * config - dictionary of config values (as returned by settings.load_config_file()
    """
    
    return datetime.datetime.strptime(os.path.basename(fname), 
                                      config['filename_format'])


############################################################################

def is_uv_image_file(filename, config):
    """
    Function returns True if the filename has the format which we expect for a 
    UV image.
    """
    if not filename.endswith(config['file_extension']):
        return False
    try:
        time_from_fname(filename, config)
    except:
        return False
    return True
    
############################################################################
 
def process_image_pair(im_pair, motion_engine, flux_engine, options, config):
    """
    Performs the motion tracking and flux calculation on a single image pair.
    This is split into a separate function to make facilitate parallel execution.
    """
    
    im1 = im_pair[0]
    im2 = im_pair[1]
     
    current_capture_time = time_from_fname(im1, config)
    current_image = cv2.imread(im1) 
    current_masked_im = motion_engine.preprocess(current_image)
     
    next_capture_time = time_from_fname(im2, config)
    next_image = cv2.imread(im2) 
    next_masked_im = motion_engine.preprocess(next_image)
    
    delta_t = date2secs(next_capture_time) - date2secs(current_capture_time)
     
    flow = motion_engine.compute_flow(current_masked_im, next_masked_im)
         
    if options.png_output_folder is not None:
        if not os.path.isdir(options.png_output_folder):
            os.makedirs(options.png_output_folder)
         
        output_filename = os.path.join(options.png_output_folder, 
                                       os.path.splitext(os.path.basename(im1))[0]+'.png')
         
        output.create_motion_png(current_masked_im, flow, output_filename, 
                                 flux_engine.get_integration_line())
    
    #only include pixels in the non-masked regions in the flux calculation
    current_image[numpy.where(current_image != current_masked_im)] = 0.0
     
    so2_flux = flux_engine.compute_flux(current_image, flow, delta_t) 
     
    return so2_flux

############################################################################

def main():
    """
    Calling this function executes the main plumetrack program. This is set as 
    an entry-point in the setup.py script and so is called by the plumetrack 
    executable (which is automatically generated by setuptools during installation).
    """
    #read the user supplied values from the command line
    options, args = settings.parse_cmd_line()
    image_dir = args[0]
     
    #load all the settings from the configuration file
    try:
        config = settings.load_config_file(filename=options.config_file)
    except settings.ConfigError, ex:
        #print a friendly error message rather than a scary looking traceback
        print "plumetrack: Configuration file error!"
        print ex.args[0]
        return
     
    #define a comparator function for ordering UV images by capture time 
    compare_by_time = lambda f1,f2: cmp(time_from_fname(f1, config), time_from_fname(f2, config))
    
    #define a test function for excluding files which are not uv images
    is_uv_image = lambda fname: is_uv_image_file(fname, config)
    

    motion_engine = motion.MotionEngine(config)
    
    if options.integration_method == '2d': 
        flux_engine = flux.FluxEngine2D(config)
    elif options.integration_method == '1d':
        flux_engine = flux.FluxEngine1D(config)
    else:
        raise ValueError("Unexpected value \"%s\"for integration_method. "
                         "Expected either '1d' or '2d'"%options.integration_method)
     
    image_iter = dir_iter.DirFileIter(image_dir, realtime=options.realtime, 
                                      skip_existing=options.skip_existing, 
                                      recursive=options.recursive, 
                                      sort_func=compare_by_time, 
                                      test_func=is_uv_image) 
    
    #set an exit handler if we are working in realtime - otherwise it can hang
    #forever.
    if options.realtime:
        import signal
        
        def _quit(*args):
            image_iter.close()
        
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
                                             motion_engine, flux_engine, options,
                                             config)
                
                if options.output_file is not None:
                    with open(options.output_file,'a') as ofp:
                        ofp.write("%s\t%f\n"%(str(time_from_fname(current_image_fname, config)),so2flux))
                else:
                    print "%s\t%f"%(str(time_from_fname(current_image_fname, config)),so2flux)
                 
            current_image_fname = next_image_fname
     
    else:
        #main loop for parallel processing
        files = [f for f in image_iter]
        file_pairs = zip(files[:-1], files[1:])
         
        fluxes = parallel_process(process_image_pair, file_pairs, motion_engine, 
                                  flux_engine, options, config)
        
        if options.output_file is not None:
            with open(options.output_file,'w') as ofp:
                for i in range(len(fluxes)):
                    ofp.write("%s\t%f\n"%(str(time_from_fname(files[i], config)),fluxes[i]))
        else:
            for i in range(len(fluxes)):
                print "%s\t%f"%(str(time_from_fname(files[i], config)),fluxes[i])
        
        
