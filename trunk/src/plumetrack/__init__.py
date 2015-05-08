#Copyright (C) Nial Peters 2014
#
#This file is part of plumetrack.
#
#plumetrack is free software: you can redistribute it and/or modify
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
#along with plumetrack.  If not, see <http://www.gnu.org/licenses/>.

import os
import sys

import image_loader

####################################################################
#                     Program Information
####################################################################
VERSION = "15.01" #year.month of release

AUTHOR = 'Nial Peters'

AUTHOR_EMAIL = 'nonbiostudent@hotmail.com'

URL = 'http://ccpforge.cse.rl.ac.uk/gf/project/plumetrack/'

PROG_SHORT_NAME = 'Plumetrack'

PROG_LONG_NAME = 'Plumetrack SO2 flux calculator'

SHORT_DESCRIPTION = 'Calculates SO2 fluxes from UV camera images'

LONG_DESCRIPTION = ('Calculates SO2 fluxes from UV camera images using the '
                    'Farneback algorithm to compute motion between successive '
                    'frames.')

COPYRIGHT = 'Copyright (C) 2014 %s'%AUTHOR

LICENSE_SHORT = ('GNU General Public License v3 or later (GPLv3+)')

COPY_PERMISSION =(
'\n%s is free software: you can redistribute it and/or modify\n'
'it under the terms of the GNU General Public License as published by\n'
'the Free Software Foundation, either version 3 of the License, or\n'
'(at your option) any later version.\n'
'\n'
'%s is distributed in the hope that it will be useful,\n'
'but WITHOUT ANY WARRANTY; without even the implied warranty of\n'
'MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the\n'
'GNU General Public License for more details.\n'
'\n'
'You should have received a copy of the GNU General Public License\n'
'along with %s.  If not, see <http://www.gnu.org/licenses/>.\n'
''%(PROG_SHORT_NAME, PROG_SHORT_NAME, PROG_SHORT_NAME))

SRC_FILE_HEADER = ('#%s\n\nThis file is part of %s.\n\n%s'
                   ''%(COPYRIGHT, PROG_SHORT_NAME, 
                       COPY_PERMISSION)).replace('\n','\n#')

####################################################################

__have_gpu = False
try:
    from plumetrack import gpu_motion
    __have_gpu = gpu_motion.haveGPU()
except ImportError:
    pass


def have_gpu():
    """
    Returns True if at least one CUDA capable GPU is detected on the system and
    plumetrack has been built with GPU support. Returns False otherwise.
    """
    return __have_gpu


def get_plumetrack_rw_dir():
    """
    Returns the path used by plumetrack for things like caching settings,
    storing templates etc. This is platform dependent, but on Linux it 
    will be in ~/.plumetrack
    """
    
    if sys.platform == 'win32':
        #Windows doesn't really do hidden directories, so get rid of the dot
        return os.path.join(os.path.expanduser('~'),"%s"%PROG_SHORT_NAME)
    else:
        return os.path.join(os.path.expanduser('~'),".%s"%PROG_SHORT_NAME)


def get_plumetrack_sys_dir():
    """
    Returns the path used by Plumetrack to store user independent 
    files
    """
    return __path__[0]


def get_plumetrack_icons_dir():
    """
    Returns the full path to the directory where the Plumetrack icons
    are stored.
    """
    return os.path.join(get_plumetrack_sys_dir(),'icons')


####################################################################

#make some important classes which are scattered throughout the source code
#available here to make finding them easier for the user
ImageLoader = image_loader.ImageLoader

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

#make sure that all the directories that we are expecting to exist actually do.
try:
    supermakedirs(get_plumetrack_rw_dir(),0o777)
    
except OSError:
    #dir already exists
    pass