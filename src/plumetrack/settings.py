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
import os
import sys
import json
from types import FloatType, ListType, IntType, UnicodeType, DictType
from optparse import OptionParser


__default_config = {                  
                    "filename_format": "%Y%m%d_%H%M%S.png",
                    "file_extension": ".png",
                    "custom_image_loader":"",
                    
                    "motion_pix_threshold_low": -1.0,
                    "motion_pix_threshold_high": -1.0,
                    "random_mean": 0.0,
                    "random_sigma":0.0,
                    "mask_image": "", 
                    
                    "pixel_size": 1.0,
                    "flux_conversion_factor": 1.0,
                    "downsizing_factor": 1.0,
                    
                    "farneback_pyr_scale": 0.5,
                    "farneback_levels": 4,
                    "farneback_winsize": 20,
                    "farneback_iterations": 10,
                    "farneback_poly_n": 7,
                    "farneback_poly_sigma": 1.5,
                    
                    "integration_method": "2d",
                    "integration_pix_threshold_low" : -1,
                    "integration_lines": [{
                                           "name":"Integration Line 1",
                                           "integration_points": [[0, 0],[1, 1]],
                                           "integration_direction": 1
                                           }]             
                  
                    }



def is_config_file(filename):
    """
    Returns True if filename looks like a config file (i.e. is a JSON file) and 
    returns False otherwise. This function is used to determine if we are loading
    configs from a results file or a config file.
    """
    
    if not os.path.exists(filename):
        return False
    
    with open(filename,'r') as ifp:
        try:
            json.load(ifp)
        except ValueError:
            return False
    
    return True


def get_default_config():
    """
    Returns a default working config which can be used as a template for 
    customisation.
    """
    return __default_config


def load_config_file(filename):
    """
    Load the configuration file and returns a dictionary of name:value pairs
    that were specified in the file. This function calls validate_config on the 
    configuration before returning it.
    
    Configurations may be loaded either from config files, or from plumetrack
    results files.
    """
    
    if not os.path.exists(filename):
        raise IOError("Failed to open config file \'%s\'. No such file."%filename)
        
    with open(filename,'r') as ifp:
        try:
            config = json.load(ifp)
        except ValueError:
            #maybe we are trying to load a configuration from a results file
            ifp.seek(0)
            config_str = ''
            for line in ifp:
                if line.lstrip().lstrip('#').lstrip().startswith('Configuration'):
                    config_str = line.partition('=')[2]
                    break
            
            try:
                config = json.loads(config_str)
            except ValueError:
                raise IOError("File \"%s\" does not contain a valid plumetrack configuration"%filename)
      
    validate_config(config, filename)
    
    return config



class ConfigError(ValueError):
    """
    Exception raised if the configuration file is invalid.
    """
    pass
     

def __validate_im_loader(config):
    """
    wrapper function used to prevent the setup.py script having to import 
    the image_loader module.
    """
    from plumetrack import image_loader
    return image_loader.validate_loader(config)
     

def validate_config(config, filename=None):
    """
    Raises ConfigError if one or more of the configuration entries is 
    invalid. This function checks that all necessary settings are defined, that 
    they have the correct data type and that they are within sensible limits.
    """
    expected_configs = [
                        ("custom_image_loader",UnicodeType, lambda x: x=="" or __validate_im_loader(config), "Invalid value for \'custom_image_loader\'. Either the file does not exist, is not a valid Python source file, or does not define a subclass of the ImageLoader class."),
                        ("filename_format", UnicodeType, lambda x: config["custom_image_loader"] != "" or (x != "" and not x.isspace()), "\'filename_format\' cannot be an empty string (unless you are using a custom image loader)."),
                        ("file_extension", UnicodeType, lambda x: config["filename_format"]=="" or config["filename_format"].endswith(x), "Mismatch between file extension specified in \'filename_format\' and \'file_extension\'."),
                        ("motion_pix_threshold_low", FloatType, lambda x: (config["motion_pix_threshold_high"] == -1 or x < config["motion_pix_threshold_high"]) and (x == -1 or x >= 0), "\'threshold_low\' must be either -1 or greater than or equal to 0 and must be less than \'threshold_high\'." ),
                        ("motion_pix_threshold_high", FloatType, lambda x: x == -1 or x > 0, "\'threshold_high\' must be either -1 or greater than 0." ),
                        ("random_mean", FloatType, lambda x: True, "" ),
                        ("random_sigma", FloatType, lambda x: True, "" ),
                        ("mask_image", UnicodeType, lambda x: x=="" or x.isspace() or os.path.exists(x), "\'mask_image\' file specified does not exist."),
                        ("pixel_size", FloatType, lambda x: True, "" ),
                        ("flux_conversion_factor", FloatType, lambda x: True, "" ),
                        ("downsizing_factor", FloatType, lambda x: x >=1.0, "\'downsizing_factor\' must be greater than or equal to 1."),
                        ("farneback_pyr_scale", FloatType, lambda x: x<1.0, "\'farneback_pyr_scale\' must be <1.0."),
                        ("farneback_levels", IntType, lambda x: x>=1, "\'farneback_levels\' must be >=1"),
                        ("farneback_winsize", IntType, lambda x: x>=1, "\'farneback_winsize\' must be >=1"),
                        ("farneback_iterations", IntType, lambda x: x>=1, "\'farneback_iterations\' must be >=1"),
                        ("farneback_poly_n", IntType, lambda x: x>=3, "\'farneback_poly_n\' must be >=3 (5 or 7 would be a better choice)"),
                        ("farneback_poly_sigma", FloatType, lambda x: x>0.0, "\'farneback_poly_sigma\' must be >0.0"),
                        ("integration_pix_threshold_low", FloatType, lambda x: (x == -1 or x >= 0), "\'integration_pix_threshold_low\' must be either -1 or >=0."),
                        ("integration_lines", ListType, lambda x: len(x) >= 1, "At least one integration line must be defined."),
                        ("integration_method", UnicodeType, lambda x: x in ('1d','2d'), "\'integration_method\' must be either \'1d\' or \'2d\'")
                        ]
    
    int_line_configs = [
                        ("integration_direction", IntType, lambda x: x==1 or x==-1, "\'integration_direction\' must be either 1 or -1"),
                        ("name", UnicodeType, lambda x: x!="" and not x.isspace(), "Missing name for integration line"),
                        ("integration_points", ListType, lambda x: len(x)>1, "At least two points are required for each integration line.")
                        ]
    
    #first validate all the top-level configs
    __validate_config(config, expected_configs, filename=filename)
    
    #now validate the configs for the integration lines
    for i,c in enumerate(config["integration_lines"]):
        if type(c) != DictType:
            raise ConfigError("Incorrect type for definition of integration "
                              "line %d. Expecting a dict."%(i+1))
        
        __validate_config(c, int_line_configs, filename=filename, 
                          subsection="integration line %d"%(i+1))
    


def __validate_config(config, expected_configs, filename=None, subsection=None):
    #first check that they all exist
    defined_names = config.keys()
    for name in [i[0] for i in expected_configs]:
        try:
            defined_names.remove(name)
        except ValueError:
            if filename is not None:
                if subsection is None:
                    raise ConfigError("Missing definition of %s in configuration file %s"%(name, filename))
                else: 
                    raise ConfigError("Missing definition of %s for %s in configuration file %s"%(name, subsection,filename))
            else:
                if subsection is None:
                    raise ConfigError("Missing definition of %s in configuration."%(name))
                else:
                    raise ConfigError("Missing definition of %s for %s in configuration."%(name, subsection))
                    
    #check if any unknown settings were defined
    if len(defined_names) != 0:
        if filename is not None:
            if subsection is None:
                raise ConfigError("Unknown setting \'%s\' in configuration file \'%s\'."%(defined_names[0], filename))
            else:
                raise ConfigError("Unknown setting \'%s\' for %s in configuration file \'%s\'."%(defined_names[0], subsection, filename))
        else:
            if subsection is None:
                raise ConfigError("Unknown setting \'%s\' in configuration."%(defined_names[0]))
            else:
                raise ConfigError("Unknown setting \'%s\' for %s in configuration."%(defined_names[0], subsection))
            
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
                        if subsection is None:
                            raise ConfigError("Incorrect type (%s) for config %s in file %s. Expecting %s"%(type(x),name, filename, expected_type))
                        else:
                            raise ConfigError("Incorrect type (%s) for config %s for %s in file %s. Expecting %s"%(type(x),name, subsection,filename, expected_type))
                    else:
                        if subsection is None:
                            raise ConfigError("Incorrect type (%s) for config %s. Expecting %s"%(type(x),name, expected_type))
                        else:
                            raise ConfigError("Incorrect type (%s) for config %s for %s. Expecting %s"%(type(x),name, subsection, expected_type))
            else:
                if filename is not None:
                    if subsection is None:
                        raise ConfigError("Incorrect type (%s) for config %s in file %s. Expecting %s"%(type(x),name, filename, expected_type))
                    else:
                        raise ConfigError("Incorrect type (%s) for config %s for %s in file %s. Expecting %s"%(type(x),name, subsection,filename, expected_type))

                else:
                    if subsection is None:
                        raise ConfigError("Incorrect type (%s) for config %s. Expecting %s"%(type(x),name, expected_type))
                    else:
                        raise ConfigError("Incorrect type (%s) for config %s for %s. Expecting %s"%(type(x),name, subsection,expected_type))
        if not test_func(x):
            raise ConfigError(message)
    

class OptionError(ValueError):
    pass

class CustomOptionParser(OptionParser):
    def __init__(self, exception_on_error):
        self.exception_on_error = exception_on_error
        OptionParser.__init__(self)
    
    def error(self, message):
        if self.exception_on_error:
            raise OptionError(message)
        else:
            OptionParser.error(self, message)
        


def parse_cmd_line(args=None, exception_on_error=False):
    """
    Function parses the command line input and returns a tuple
    of (options, args). By default this function parses the sys.vargs, but a list
    of command line arguments may be passed in using the args kwarg instead.
    """
    import plumetrack
    usage = ("%prog [options] image_folder")
    
    parser = CustomOptionParser(exception_on_error)
    
    
    parser.prog = plumetrack.PROG_SHORT_NAME
    parser.usage = usage
    parser.description = plumetrack.LONG_DESCRIPTION
    
    parser.add_option("-f", "--config_file", dest="config_file", action='store', 
                      type='string', default=None,
                      help="Specifies the configuration file to use.")
    
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
    
    parser.add_option( "--no_gpu", dest="no_gpu", action="store_true", 
                      default=False,
                      help="Stops plumetrack from using the GPU for processing. "
                      "Note that it may not be using the GPU anyway.")

    parser.add_option("-o","--output_file", dest="output_file", action="store", 
                      default=None, type='string',
                      help="Output file to write computed fluxes to. If no file "
                           "is specified then fluxes will be written to "
                           "standard output. The specified filename may contain "
                           "Python date/time format specifiers to enable "
                           "automatic splitting of output data into multiple "
                           "files. For example a filename of %Y/%m/%d_fluxes.txt "
                           "would split the output into daily files organised by "
                           "month and year.")
    
    parser.add_option("--output_velocities", dest="vel_output_folder", 
                      action="store", default=None, type='string',
                      help="Output computed velocity arrays into this folder. "
                           "The folder (and any subfolders) will be created "
                           "automatically if it does not already exist. The "
                           "file format used for output arrays can be set using" 
                           " the vel_arr_format option. Velocity arrays have a "
                           "shape of MxNx2 where M is image width, N is image "
                           "height. arr[:,:,0] are the computed velocities in "
                           "the x-direction (in m/s) and arr[:,:,1] are the "
                           "computed velocities in the y-direction (in m/s).")
    
    parser.add_option("--vel_arr_format", dest="vel_arr_format", action="store",
                      default='npy', type='string',
                      help="Sets the file format for output velocity arrays. "
                      "Can be set to 'npy' (default) for numpy binary files, "
                      "'mat' for Matlab .mat files (saved using "
                      "scipy.io.savemat) or 'json' for JSON files.")
    
    parser.add_option("--output_pngs", dest="png_output_folder", action="store", 
                      default=None, type='string',
                      help="Output PNG files of the motion field into this "
                           "folder. The folder (and any subfolders) will be "
                           "created automatically if it does not already exist. "
                           "Default is no PNG output.")
          
    parser.add_option("--max_n", dest="max_n", action="store", 
                      default=None, type='int', help="Sets the maximum number "
                      "of images to process. Note that you will get max_n - 1 "
                      "flux measurements returned (since each flux requires "
                      "two images.)")
                      
    parser.add_option("-s", "--skip_existing", dest="skip_existing", 
                      action="store_true", default=False,
                      help="Ignore images that are already in the folder. Use "
                           "of this option implies --realtime")
    
    parser.add_option("", "--version", action="callback", 
                      callback=__print_version_and_exit, help=("Print Plumetrack"
                      " version number and license information and exit."))

    
    (options, args) = parser.parse_args(args=args)

    if len(args) < 1:
        parser.error("No input folder specified")
    
    elif len(args) > 1:
        parser.error("Only one input folder can be specified. Folders with "
                     "spaces in their names should be enclosed in quotation marks")
    
    elif not os.path.isdir(args[0]):
        parser.error("Cannot open images in \'%s\'. No such directory."%(args[0]))
    
    #a config file must be specified
    if options.config_file is None:
        parser.error("No configuration file specified. You must use the \'-f\' "
                     "option to specify a configuration file to use.")
    
    if options.vel_arr_format not in ('npy', 'mat', 'json'):
        parser.error("Invalid value for vel_arr_format, expecting 'npy', 'mat' or 'json'.")
        
    #use of the skip_existing option implies the use of the realtime option
    if options.skip_existing and not options.realtime:
        options.realtime = True
    
        
    return (options, args)



def __print_version_and_exit(*args):
    """
    Prints the version number and license information for plumetrack.
    """
    import plumetrack #imported here to prevent circular imports
    print "%s (version %s)"%(plumetrack.PROG_SHORT_NAME, plumetrack.VERSION)
    print plumetrack.COPYRIGHT
    print plumetrack.LICENSE_SHORT
    print ""
    print "Written by %s."%plumetrack.AUTHOR
    sys.exit(0)
    