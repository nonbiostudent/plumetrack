#! python
# -*- coding: utf-8 -*-

#Copyright (C) Nial Peters 2015
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
import os.path
import sys
import shutil
import cPickle

import plumetrack


if sys.argv[1] == '-install':
    #find where the  script got installed to - this will be in the same
    #folder as the postinstall script (i.e. this script)
    
    script_dir = os.path.abspath(os.path.dirname(sys.argv[0]))
    script_path = os.path.join(script_dir,'plumetrack-gui-script.pyw')
    
    desktop_folder = get_special_folder_path("CSIDL_DESKTOPDIRECTORY")
    start_menu_folder = get_special_folder_path("CSIDL_STARTMENU")
    plumetrack_prog_name = plumetrack.PROG_SHORT_NAME+'.lnk'
    
    icon_path = os.path.join(plumetrack.get_plumetrack_icons_dir(),'plumetrack.ico')
    
       
    create_shortcut(
        script_path, # program
        plumetrack.SHORT_DESCRIPTION, # description
        plumetrack_prog_name, # filename
        '', # parameters
        '', # workdir
        icon_path, # iconpath
    )
    # move shortcut from current directory to Start menu
    shutil.move(os.path.join(os.getcwd(), plumetrack_prog_name),
                os.path.join(start_menu_folder, plumetrack_prog_name))
    
    # tell windows installer that we created another
    # file which should be deleted on uninstallation
    file_created(os.path.join(start_menu_folder, plumetrack_prog_name))

if sys.argv[1] == '-remove':
    pass
    # This will be run on uninstallation. Nothing to do.
