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
from setuptools import setup
from setuptools.command.install import install
import sys
import os

####################################################################
#                    CONFIGURATION
####################################################################

required_modules = [
                    ("cv2","OpenCV (including Python bindings)")
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
                        'numpy>=1.8', 
                        'matplotlib>=0.9', 
                        'scipy',
                        'Image',
                        #'wxPython>=2.8.12'
                        ]

if sys.platform == 'win32':
    install_dependencies.append('pywin32')
else:
    install_dependencies.append('pyinotify')


class CustomInstall(install):
    def run(self):
        """
        Override the run function to also create the rw directory and create the 
        default config file there
        """
        install.run(self)


####################################################################
#                    BUILD/INSTALL
####################################################################
import src.plumetrack as plumetrack_preinstall

setup(name             = plumetrack_preinstall.PROG_SHORT_NAME,
      version          = plumetrack_preinstall.VERSION,
      description      = plumetrack_preinstall.SHORT_DESCRIPTION,
      author           = plumetrack_preinstall.AUTHOR,
      author_email     = plumetrack_preinstall.AUTHOR_EMAIL,
      url              = plumetrack_preinstall.URL,
      package_dir      = {'':'src'},
      packages         = ['plumetrack'],
      install_requires = install_dependencies,
      entry_points     = {'console_scripts': ['plumetrack = plumetrack.main_script:main']}
      )
