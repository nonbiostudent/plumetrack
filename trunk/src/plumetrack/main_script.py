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
import cv2
import multiprocessing
import calendar

import plumetrack
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
     
    for l in split(list_,multiprocessing.cpu_count()):
        q = multiprocessing.Queue(0)
        p = multiprocessing.Process(target=__run_func,args=(func,q,l,args,kwargs))
        p.start()
        processes.append(p)
        queues.append(q)
     
    for i in range(len(processes)):        
        results.append(queues[i].get())
        processes[i].join()
     
    return flatten(results)
 
############################################################################

def split(l,n):
    """
    splits the list l into n approximately equal length lists and returns
    them in a tuple. if n > len(l) then the returned tuple may contain
    less than n elements.
    >>> split([1,2,3],2)
    ([1, 2], [3])
    >>> split([1,2],3)
    ([1], [2])
    """
    length = len(l)
        
    #can't split into more pieces than there are elements!
    if n > length:
        n = length
    
    if int(n) <= 0:
        raise ValueError, "n must be a positive integer"
    
    inc = int(float(length) / float(n) + 0.5)
    split_list = []

    for i in range(0, n - 1):
        split_list.append(l[i * inc:i * inc + inc])
        
    split_list.append(l[n * inc - inc:])
    
    return tuple(split_list)

############################################################################

def flatten(l, ltypes=(list, tuple)):
    """
    Reduces any iterable containing other iterables into a single list
    of non-iterable items. The ltypes option allows control over what 
    element types will be flattened. This algorithm is taken from:
    http://rightfootin.blogspot.com/2006/09/more-on-python-flatten.html
    
    >>> print flatten([range(3),range(3,6)])
    [0, 1, 2, 3, 4, 5]
    >>> print flatten([1,2,(3,4)])
    [1, 2, 3, 4]
    >>> print flatten([1,[2,3,[4,5,[6,[7,8,[9,[10]]]]]]])
    [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    >>> print flatten([1,[2,3,[4,5,[6,[7,8,[9,[10]]]]]]], ltypes=())
    [1, [2, 3, [4, 5, [6, [7, 8, [9, [10]]]]]]]
    >>> print flatten([1,2,(3,4)],ltypes=(list))
    [1, 2, (3, 4)]
    """
    ltype = type(l)
    l = list(l)
    i = 0
    while i < len(l):
        while isinstance(l[i], ltypes):
            if not l[i]:
                l.pop(i)
                i -= 1
                break
            else:
                l[i:i + 1] = l[i]
        i += 1
    return ltype(l)

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
    
    if im1 == process_image_pair.cached_im_name:
        current_masked_im = process_image_pair.cached_im
        integration_mask = process_image_pair.cached_mask
    else:
        current_masked_im = cv2.imread(im1, cv2.IMREAD_UNCHANGED) 
        integration_mask = motion_engine.preprocess(current_masked_im)
    
    next_capture_time = time_from_fname(im2, config)
    next_masked_im = cv2.imread(im2, cv2.IMREAD_UNCHANGED) 
    process_image_pair.cached_mask = motion_engine.preprocess(next_masked_im)
    
    #update cached values
    process_image_pair.cached_im_name = im2
    process_image_pair.cached_im = next_masked_im
    
    #images must be the same size for motion estimation
    if current_masked_im.shape != next_masked_im.shape:
        raise ValueError("Images \'%s\' and \'%s\' are different sizes %s and "
                         "%s respectively"%(im1, im2,str(current_masked_im.shape), 
                                            str(next_masked_im.shape)))
    
    
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
    current_masked_im *= numpy.logical_not(integration_mask) 
    
    so2_flux = flux_engine.compute_flux(current_masked_im, flow, delta_t) 
    
    return so2_flux

#define the cache for the process_image_pair function
process_image_pair.cached_im_name = None
process_image_pair.cached_im = None
process_image_pair.cached_mask = None

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
    
    if plumetrack.have_gpu() and not options.no_gpu:
        motion_engine = motion.GPUMotionEngine(config)
    else:
        motion_engine = motion.MotionEngine(config)
    
    if options.integration_method == '2d': 
        flux_engine = flux.FluxEngine2D(config)
    elif options.integration_method == '1d':
        flux_engine = flux.FluxEngine1D(config)
    else:
        raise ValueError("Unexpected value \"%s\"for integration_method. "
                         "Expected either '1d' or '2d'"%options.integration_method)
     
    image_iter = dir_iter.ListDirIter(image_dir, realtime=options.realtime, 
                                      skip_existing=options.skip_existing, 
                                      recursive=options.recursive, 
                                      sort_func=compare_by_time, 
                                      test_func=is_uv_image,
                                      max_n=options.max_n) 
    
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
        
        
