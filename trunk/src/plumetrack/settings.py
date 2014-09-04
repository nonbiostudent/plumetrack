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
from optparse import OptionParser

import plumetrack

def get_plumetrack_rw_dir():
    """
    Returns the path used by _plumetrack for things like caching settings.
    This is platform dependent, but on Linux it will be in ~/._plumetrack
    """
    
    if sys.platform == 'win32':
        #Windows doesn't really do hidden directories, so get rid of the dot
        return os.path.join(os.path.expanduser('~'),"_plumetrack")
    else:
        return os.path.join(os.path.expanduser('~'),"._plumetrack")



def load_config_file(filename=None):
    
    if filename is None:
        filename = os.path.join(get_plumetrack_rw_dir(), "_plumetrack.cfg")
    
        
    with open(filename,'r') as ifp:
        config = json.load(ifp)
    
    validate_config(config)
    
    return config



def validate_config(config):
    #TODO - validate that all required values exist and are of the correct type
    pass


def parse_cmd_line():
    """
    Function parses the command line input and returns a tuple
    of (options, args)
    """
    usage = ("%prog [options] image_folder")
    
    parser = OptionParser()
    
    parser.usage = usage
    parser.prog = plumetrack.PROG_SHORT_NAME
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
