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
import os
import sys
import json
from types import StringType, FloatType, ListType, IntType
from optparse import OptionParser

import plumetrack

def get_plumetrack_rw_dir():
    """
    Returns the path used by plumetrack for things like caching settings.
    This is platform dependent, but on Linux it will be in ~/.plumetrack
    """
    
    if sys.platform == 'win32':
        #Windows doesn't really do hidden directories, so get rid of the dot
        return os.path.join(os.path.expanduser('~'),"plumetrack")
    else:
        return os.path.join(os.path.expanduser('~'),".plumetrack")



def load_config_file(filename=None):
    
    if filename is None:
        filename = os.path.join(get_plumetrack_rw_dir(), "plumetrack.cfg")
    
    if not os.path.exists(filename):
        raise IOError("Failed to open config file \'%s\'. No such file."%filename)
        
    with open(filename,'r') as ifp:
        config = json.load(ifp)
    
    validate_config(config, filename)
    
    return config


class ConfigFileError(ValueError):
    pass
     

def validate_config(config, filename):
    expected_configs = [
                        ("filename_format", StringType, lambda x: x != "" and not x.isspace(), "filename_format cannot be an empty string."),
                        ("file_extension", StringType, lambda x: config["filename_format"].endswith(x), "mismatch between file extension specified in filename_format and file_extension."),
                        ("threshold_low", FloatType, lambda x: config["threshold_high"] == -1 or x < config["threshold_high"], "threshold_low cannot be greater than threshold_high." ),
                        ("threshold_high", FloatType, lambda x: x == -1 or x > 0, "threshold_high must be either -1 or greater than 0." ),
                        ("random_mean", FloatType, lambda x: True, "" ),
                        ("random_sigma", FloatType, lambda x: True, "" ),
                        ("mask_image", StringType, lambda x: x=="" or x.isspace() or os.path.exists(x), "mask_image file specified does not exist."),
                        ("pixel_size", FloatType, lambda x: True, "" ),
                        ("flux_conversion_factor", FloatType, lambda x: True, "" ),
                        ("farneback_pyr_scale", FloatType, lambda x: x<1.0, "farneback_pyr_scale must be <1.0."),
                        ("farneback_levels", IntType, lambda x: x>=1, "farneback_levels must be >=1"),
                        ("farneback_winsize", IntType, lambda x: x>=1, "farneback_winsize must be >=1"),
                        ("farneback_iterations", IntType, lambda x: x>=1, "farneback_iterations must be >=1"),
                        ("farneback_poly_n", IntType, lambda x: x>=3, "farneback_poly_n must be >=3 (5 or 7 would be a better choice)"),
                        ("farneback_poly_sigma", FloatType, lambda x: x>0.0, "farneback_poly_sigma must be >0.0"),
                        ("integration_line", ListType, lambda x: len(x) >=2, "at least 2 points are required for the integration_line"),
                        ("integration_direction", IntType, lambda x: x==1 or x==-1, "integration_direction must be either 1 or -1")
                        ]

    #first check that they all exist
    for name in [i[0] for i in expected_configs]:
        if not config.has_key(name):
            raise ConfigFileError("Missing definition of %s in configuration file %s"%(name, filename))
    
    #now check all the types and the test_functions
    for name, expected_type, test_func, message in expected_configs:
        x = config[name]
        
        if type(x) != expected_type:
            raise ConfigFileError("Incorrect type for conifg %s in file %s. Expecting %s"%(name, filename, expected_type))
        
        if not test_func(x):
            raise ConfigFileError(message)
    


def parse_cmd_line():
    """
    Function parses the command line input and returns a tuple
    of (options, args)
    """
    usage = ("%prog [options] image_folder")
    
    parser = OptionParser()
    
    
    parser.prog = plumetrack.PROG_SHORT_NAME
    parser.usage = usage
    parser.description = plumetrack.LONG_DESCRIPTION
    
    parser.add_option("-f", "--config_file", dest="config_file", action='store', 
                      type='string', default=None,
                      help="Specifies the configuration file to use. If no "
                           "config file is specified then the default config "
                           "file is used.")
    
    parser.add_option("-r", "--recursive", dest="recursive", 
                      action="store_true", default=False,
                      help="Scan folders recursively for image files")
    
    parser.add_option("-p", "--parallel", dest="parallel", action="store_true", 
                      default=False,
                      help="Parallel process the images. This will be ignored "
                           "when used with the realtime option")
    
    parser.add_option("-t", "--realtime", dest="realtime", action="store_true", 
                      default=False,
                      help="Continuously monitor the image folder for new files")

    parser.add_option("-o","--output_file", dest="output_file", action="store", 
                      default=None, type='string',
                      help="Output file to write computed fluxes to. If no file "
                           "is specified then fluxes will be written to "
                           "standard output")
    
    parser.add_option("--output_pngs", dest="png_output_folder", action="store", 
                      default=None, type='string',
                      help="Output PNG files of the motion field into this "
                           "folder. Default is no PNG output.")      
    
    parser.add_option("-s", "--skip_existing", dest="skip_existing", 
                      action="store_true", default=False,
                      help="Ignore images that are already in the folder. Use "
                           "of this option implies --realtime") 

    
    (options, args) = parser.parse_args()

    if len(args) < 1:
        parser.error("No input folder specified")
    
    elif len(args) > 1:
        parser.error("Only one input folder can be specified. Folders with "
                     "spaces in their names should be enclosed in quotation marks")
    
    elif not os.path.isdir(args[0]):
        parser.error("Cannot open images in \'%s\'. No such directory."%(args[0]))
        
    #use of the skip_existing option implies the use of the realtime option
    if options.skip_existing and not options.realtime:
        options.realtime = True
        
    return (options, args)
