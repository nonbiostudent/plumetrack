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

####################################################################
#                     Program Information
####################################################################
VERSION = "14.09" #year.month of release

AUTHOR = 'Nial Peters'

AUTHOR_EMAIL = 'nonbiostudent@hotmail.com'

URL = 'http://ccpforge.cse.rl.ac.uk/gf/project/_plumetrack/'

PROG_SHORT_NAME = 'plumetrack'

PROG_LONG_NAME = 'plumetrack SO2 flux calculator'

SHORT_DESCRIPTION = 'Calculates SO2 fluxes from UV camera images'

LONG_DESCRIPTION = ('Calculates SO2 fluxes from UV camera images using the '
                    'Farneback algorithm to compute motion between successive '
                    'frames.')

COPYRIGHT = 'Copyright (C) 2014 %s'%AUTHOR

LICENSE_SHORT = ('License GPLv3+: GNU GPL version 3 or later '
                 '<http://gnu.org/licenses/gpl.html>.\nThis is free software: '
                 'you are free to change and redistribute it.\nThere is NO '
                 'WARRANTY, to the extent permitted by law.')

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
