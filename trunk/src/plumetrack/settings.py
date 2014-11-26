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
from types import FloatType, ListType, IntType, UnicodeType
from optparse import OptionParser



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
    """
    Load the configuration file and returns a dictionary of name:value pairs
    that were specified in the file. If filename is not specified, then loads
    the default configuration file. This function calls validate_config on the 
    configuration before returning it.
    """
    if filename is None:
        filename = os.path.join(get_plumetrack_rw_dir(), "plumetrack.cfg")
    
    if not os.path.exists(filename):
        raise IOError("Failed to open config file \'%s\'. No such file."%filename)
        
    with open(filename,'r') as ifp:
        config = json.load(ifp)
      
    validate_config(config, filename)
    
    return config


class ConfigError(ValueError):
    """
    Exception raised if the configuration file is invalid.
    """
    pass
     

def validate_config(config, filename=None):
    """
    Raises ConfigError if one or more of the configuration entries is 
    invalid. This function checks that all necessary settings are defined, that 
    they have the correct data type and that they are within sensible limits.
    """
    expected_configs = [
                        ("filename_format", UnicodeType, lambda x: x != "" and not x.isspace(), "\'filename_format\' cannot be an empty string."),
                        ("file_extension", UnicodeType, lambda x: config["filename_format"].endswith(x), "Mismatch between file extension specified in \'filename_format\' and \'file_extension\'."),
                        ("threshold_low", FloatType, lambda x: (config["threshold_high"] == -1 or x < config["threshold_high"]) and (x == -1 or x >= 0), "\'threshold_low\' must be either -1 or greater than or equal to 0 and cannot be greater than \'threshold_high\'." ),
                        ("threshold_high", FloatType, lambda x: x == -1 or x > 0, "\'threshold_high\' must be either -1 or greater than 0." ),
                        ("random_mean", FloatType, lambda x: True, "" ),
                        ("random_sigma", FloatType, lambda x: True, "" ),
                        ("mask_image", UnicodeType, lambda x: x=="" or x.isspace() or os.path.exists(x), "\'mask_image\' file specified does not exist."),
                        ("pixel_size", FloatType, lambda x: True, "" ),
                        ("flux_conversion_factor", FloatType, lambda x: True, "" ),
                        ("farneback_pyr_scale", FloatType, lambda x: x<1.0, "\'farneback_pyr_scale\' must be <1.0."),
                        ("farneback_levels", IntType, lambda x: x>=1, "\'farneback_levels\' must be >=1"),
                        ("farneback_winsize", IntType, lambda x: x>=1, "\'farneback_winsize\' must be >=1"),
                        ("farneback_iterations", IntType, lambda x: x>=1, "\'farneback_iterations\' must be >=1"),
                        ("farneback_poly_n", IntType, lambda x: x>=3, "\'farneback_poly_n\' must be >=3 (5 or 7 would be a better choice)"),
                        ("farneback_poly_sigma", FloatType, lambda x: x>0.0, "\'farneback_poly_sigma\' must be >0.0"),
                        ("integration_line", ListType, lambda x: len(x) >=2, "At least 2 points are required for \'integration_line\'"),
                        ("integration_direction", IntType, lambda x: x==1 or x==-1, "\'integration_direction\' must be either 1 or -1")
                        ]

    #first check that they all exist
    defined_names = config.keys()
    for name in [i[0] for i in expected_configs]:
        try:
            defined_names.remove(name)
        except ValueError:
            if filename is not None:
                raise ConfigError("Missing definition of %s in configuration file %s"%(name, filename))
            else:
                raise ConfigError("Missing definition of %s in configuration."%(name))
        
    #check if any unknown settings were defined
    if len(defined_names) != 0:
        if filename is not None:
            raise ConfigError("Unknown setting \'%s\' in configuration file \'%s\'."%(defined_names[0], filename))
        else:
            raise ConfigError("Unknown setting \'%s\' in configuration."%(defined_names[0]))
        
    #now check all the types and the test_functions
    for name, expected_type, test_func, message in expected_configs:
        x = config[name]
        
        if type(x) != expected_type:
            if expected_type == FloatType:
                #allow floats to be specified as ints and or strings
                try:
                    x = float(x)
                    config[name] = x
                except ValueError:
                    if filename is not None:
                        raise ConfigError("Incorrect type (%s) for config %s in file %s. Expecting %s"%(type(x),name, filename, expected_type))
                    else:
                        raise ConfigError("Incorrect type (%s) for config %s. Expecting %s"%(type(x),name, expected_type))
            else:
                if filename is not None:
                    raise ConfigError("Incorrect type (%s) for config %s in file %s. Expecting %s"%(type(x),name, filename, expected_type))
                else:
                    raise ConfigError("Incorrect type (%s) for config %s. Expecting %s"%(type(x),name, expected_type))
        if not test_func(x):
            raise ConfigError(message)
    


def parse_cmd_line():
    """
    Function parses the command line input and returns a tuple
    of (options, args)
    """
    import plumetrack
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
    
    parser.add_option("-i","--integration_method", dest="integration_method", action="store", 
                      default='2d', type='string',
                      help="Select either '1d' or '2d' method for integrating "
                           "the flux. Default is '2d'.")
    
    parser.add_option("-t", "--realtime", dest="realtime", action="store_true", 
                      default=False,
                      help="Continuously monitor the image folder for new files")
    
    parser.add_option( "--no_gpu", dest="no_gpu", action="store_true", 
                      default=False,
                      help="Stops plumetrack from using the GPU for processing")

    
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
    
    parser.add_option("", "--version", action="callback", 
                      callback=__print_version_and_exit, help=("Print plumetrack"
                      " version number and license information and exit."))

    
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
    
    #check that the integration method is valid
    if not options.integration_method in ('1d','2d'):
        parser.error("Unknown integration_method '%s', expecting either '1d' "
                     "or '2d'"%options.integration_method)
        
    return (options, args)


def __print_version_and_exit(*args):
    """
    Prints the version number and license information for plumetrack.
    """
    import plumetrack
    print "%s (version %s)"%(plumetrack.PROG_SHORT_NAME, plumetrack.VERSION)
    print plumetrack.COPYRIGHT
    print plumetrack.LICENSE_SHORT
    print ""
    print "Written by %s."%plumetrack.AUTHOR
    sys.exit(0)