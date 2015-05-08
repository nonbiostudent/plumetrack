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

#set this to true to enable CUDA-capable GPU support - this is still very much 
#under development and almost certainly won't work under Windows.
enable_gpu_support = False


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


####################################################################
#                    EXTENSION MODULES
####################################################################
extension_modules = []

if enable_gpu_support:
    numpyincludedirs = numpy.get_include()
    gpu_extension = Extension("plumetrack._gpu_motion",
                       ["src/swig/gpu_motion_wrap.cxx", "src/swig/gpu_motion.cxx", "src/swig/traceback.cxx"],
                       include_dirs=[numpyincludedirs] + ['/usr/local/include/opencv', '/usr/local/include'],
                       libraries=['opencv_core','opencv_gpu', 'cudart' ])
     
    extension_modules.append(gpu_extension)


####################################################################
#                    BUILD/INSTALL
####################################################################




class CustomInstall(install):
    def __init__(self,*args, **kwargs):
        install.__init__(self,*args, **kwargs)
        self.install_paths = {}
    
    
    def finalize_options (self):
        """
        Override the finalize_options method to record the install paths so that
        we can copy them into the build_info.py file during post-install
        """
        install.finalize_options(self)
        
        #note that these MUST be absolute paths
        self.install_paths['prefix'] = os.path.abspath(self.install_base)
        self.install_paths['install_data'] = os.path.abspath(self.install_data)
        self.install_paths['lib_dir'] = os.path.abspath(self.install_lib)
        self.install_paths['script_dir'] = os.path.abspath(self.install_scripts)
    
    
    def run(self):
        """
        Override the run function to also create the rw directory and create the 
        default config file there
        """
        install.run(self)
        config_filename = os.path.join(plumetrack_preinstall.get_plumetrack_rw_dir(), 
                                       "plumetrack.cfg")
        
        print "Writing default configuration to \'%s\'"%config_filename
        
        #note that the rw folder is created automatically when we import plumetrack
        
        with open(config_filename, 'w') as ofp:
            json.dump(default_config, ofp, indent=2)
        os.chmod(config_filename, 0o777)
        
        self.execute(self.run_post_install_tasks, (), 
                     msg="Running post install tasks")
        
        
    def run_post_install_tasks(self):
        """
        Executes any tasks required after the installation is completed, e.g.
        creating .desktop files etc.
        """
        #create a desktop file (if we are in Linux)
        if sys.platform == "linux2":
            create_desktop_file(self.install_paths)


def create_desktop_file(install_paths):
    """
    Function to create the .desktop file for Linux installations.
    """
    import plumetrack
    apps_folder = os.path.join(install_paths['prefix'],'share','applications')
    
    if not os.path.isdir(apps_folder):
        try:
            os.makedirs(apps_folder)
        except OSError:
            print ("Warning! Failed to create plumetrack.desktop file. Unable to "
                   "create folder \'%s\'."%apps_folder)
            return
    
    desktop_file_path = os.path.join(apps_folder,'plumetrack.desktop')
    
    with open(desktop_file_path,'w') as ofp:
        ofp.write('[Desktop Entry]\n')
        ofp.write('Version=%s\n'%plumetrack.VERSION)
        ofp.write('Type=Application\n')
        ofp.write('Exec=plumetrack-gui\n')
        ofp.write('Comment=%s\n'%plumetrack.SHORT_DESCRIPTION)
        ofp.write('NoDisplay=false\n')
        ofp.write('Categories=Science;Education;\n')
        ofp.write('Name=%s\n'%plumetrack.PROG_SHORT_NAME)
        ofp.write('Icon=%s\n'%os.path.join(plumetrack.get_plumetrack_icons_dir(),
                                           '64x64','plumetrack.png'))
    
    return_code = os.system("chmod 644 " + os.path.join(apps_folder, 
                                                        'plumetrack.desktop'))
    if return_code != 0:
        print ("Error! Failed to change permissions on \'" + 
               os.path.join(apps_folder, 'plumetrack.desktop') + "\'")



#populate the list of data files to be installed
dirs = [d for d in os.listdir(os.path.join('src','plumetrack','icons')) if os.path.isdir(os.path.join('src','plumetrack','icons',d))]
icon_files_to_install = []
for d in dirs:
    if d.startswith('.'):
        continue
    
    icon_files = os.listdir(os.path.join('src','plumetrack','icons',d))
    for f in icon_files:
        if f.startswith('.'):
            continue #skip the .svn folder
        icon_files_to_install.append(os.path.join('icons', d,f))


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
      package_data     = {'plumetrack':icon_files_to_install},
      packages         = ['plumetrack', 'plumetrack.gui'],
      ext_modules      = extension_modules,
      install_requires = install_dependencies,
      entry_points     = {'console_scripts': ['plumetrack = plumetrack.main_script:main'],
                          'gui_scripts': ['plumetrack-gui = plumetrack.gui.main:main']}
      )
