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

from ez_setup import use_setuptools
use_setuptools()
from setuptools import setup, Extension
from setuptools.command.install import install
import numpy
import sys
import os
import json
import StringIO

####################################################################
#                    CONFIGURATION
####################################################################

required_modules = [
                    ("cv2","OpenCV (including Python bindings)"),
                   ]

data_files_to_install = []

#check that all the required modules are available
print "Checking for required Python modules not available through PyPi..."
for mod, name in required_modules:
    try:
        print "importing %s..."%mod
        __import__(mod)
    except ImportError:
        print ("Failed to import \'%s\'. Please ensure that %s "
               "is correctly installed, then re-run this "
               "installer."%(mod,name))
        sys.exit(1)

#list of dependencies that are in PyPi
install_dependencies = [
                        'numpy>=1.6', 
                        'matplotlib>=0.9', 
                        'scipy',
                        'wxPython>=2.8.10'
                        ]

if sys.platform == 'win32':
    install_dependencies.append('pywin32')
else:
    install_dependencies.append('pyinotify')


####################################################################
#                        DEFAULTS
####################################################################
#define a default configuration which gets written to file on installation
default_config = {
                  
"filename_format": "%Y%m%d_%H%M%S.png",
"file_extension": ".png",

"threshold_low": 0.0,
"threshold_high": -1.0,
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
"integration_line": [[0, 0],[1, 1]],
"integration_direction": 1                 
                  
}


####################################################################
#                    EXTENSION MODULES
####################################################################
extension_modules = []

numpyincludedirs = numpy.get_include()
gpu_extension = Extension("plumetrack._gpu_motion",
                   ["src/swig/gpu_motion_wrap.cxx", "src/swig/gpu_motion.cxx", "src/swig/traceback.cxx"],
                   include_dirs=[numpyincludedirs] + ['/usr/local/include/opencv', '/usr/local/include'],
                   libraries=['opencv_core','opencv_gpu', 'cudart' ])
 
extension_modules.append(gpu_extension)


####################################################################
#                    BUILD/INSTALL
####################################################################
def supermakedirs(path, mode):
    """
    Create a directory structure and with a certain set of access permissions
    (ignoring the umask - unlike os.makedirs()). This function is copied from 
    http://stackoverflow.com/questions/5231901/permission-problems-when-creating-a-dir-with-os-makedirs-python
    """
    if not path or os.path.exists(path):
        return []
    (head, tail) = os.path.split(path)
    res = supermakedirs(head, mode)
    os.mkdir(path)
    os.chmod(path, mode)
    res += [path]
    return res



class CustomInstall(install):
    def run(self):
        """
        Override the run function to also create the rw directory and create the 
        default config file there
        """
        install.run(self)
        config_filename = os.path.join(plumetrack_preinstall.get_plumetrack_rw_dir(), 
                                       "plumetrack.cfg")
        
        print "Writing default configuration to \'%s\'"%config_filename
        
        if not os.path.isdir(os.path.dirname(config_filename)):
            supermakedirs(os.path.dirname(config_filename), 0777)
        
        with open(config_filename, 'w') as ofp:
            json.dump(default_config, ofp, indent=2)
        os.chmod(config_filename, 0777)



import src.plumetrack as plumetrack_preinstall
import src.plumetrack.settings as settings_preinstall

#ensure that the default config that we are installing is valid (i.e. up to date
#with the version of plumetrack)
decoded_default_config = json.loads(json.dumps(default_config))
settings_preinstall.validate_config(decoded_default_config, "setup.py")

#do the build/install
setup(cmdclass={'install':CustomInstall},
      name             = plumetrack_preinstall.PROG_SHORT_NAME,
      version          = plumetrack_preinstall.VERSION,
      description      = plumetrack_preinstall.SHORT_DESCRIPTION,
      long_description = plumetrack_preinstall.LONG_DESCRIPTION,
      author           = plumetrack_preinstall.AUTHOR,
      author_email     = plumetrack_preinstall.AUTHOR_EMAIL,
      url              = plumetrack_preinstall.URL,
      license          = plumetrack_preinstall.LICENSE_SHORT,  
      package_dir      = {'':'src'},
      packages         = ['plumetrack', 'plumetrack.plumetrack_config'],
      ext_modules      = extension_modules,
      install_requires = install_dependencies,
      entry_points     = {'console_scripts': ['plumetrack = plumetrack.main_script:main'],
                          'gui_scripts': ['plumetrack-config = plumetrack.plumetrack_config.config_script:main']}
      )
