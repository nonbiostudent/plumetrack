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
import datetime
import json
import os
import matplotlib.pyplot as plt
import scipy.misc

import plumetrack


def resample_velocities(image, velocities, yn):
    x_size = int(round((float(yn)/image.shape[1]) * image.shape[0],0))
    
    x_shifts = scipy.misc.imresize(velocities[...,0], (x_size, yn), 'nearest','F')
    y_shifts = scipy.misc.imresize(velocities[...,1], (x_size, yn), 'nearest','F')
    
    extent = (0.0, float(yn-1), float(x_size-1), 0.0)
    
    return x_shifts, y_shifts, extent


def create_motion_png(image, velocities, output_filename, integration_line):
    """
    Creates and saves a PNG image showing the original image with the computed 
    motion vectors and the integration line superimposed on the top. Note that 
    the motion field will be downsampled to make the vectors visible on the plot.
    """
    x_shifts, y_shifts, extent = resample_velocities(image, velocities, 64)
    plt.close()
    plt.quiver(x_shifts, -y_shifts, units='xy', scale_units='xy',scale=1.5)

    plt.imshow(image, extent=extent)
    
    x_size = int(round((64/image.shape[1]) * image.shape[0],0))
    
    #plot the integration line
    scale_factor_x = float(x_size-1) / image.shape[0]
    scale_factor_y = 63.0 / image.shape[1]
    pts = integration_line.get_n_points()

    pts[:,0] *= scale_factor_x
    pts[:,1] *= scale_factor_y
    
    plt.plot(pts[:,0], pts[:,1], 'w-')
    
    plt.xlim((0,63))
    plt.ylim((x_size-1,0))
    plt.xticks([])
    plt.yticks([])
    plt.colorbar()
    plt.savefig(output_filename)


def create_output_file(filename, im_dir, config):
    
    try:
        folder = os.path.dirname(filename)
        if folder:
            os.makedirs(folder)
    except OSError:
        #folder already exists
        pass
    
    config_str = json.dumps(config)
    
    flux_headings = '\t\t'.join([i['name'] for i in config['integration_lines']])
    
    ofp = open(filename,'w')
        
    ofp.write("# plumetrack results file\n")
    ofp.write("# Created on %s using plumetrack version %s\n"%(datetime.datetime.now(), plumetrack.VERSION))
    ofp.write("#\n")
    ofp.write("# Image folder = %s\n"%im_dir)
    ofp.write("# Configuration = %s\n"%config_str)
    ofp.write("#\n")
    ofp.write("#\n")
    ofp.write("# Filename\t\tTime\t\t%s\n"%flux_headings)
    ofp.write("#\n")
    
    return ofp


def write_output(options, config, image_dir, times, filenames, fluxes):
        ofp = None
        
        for i in range(len(fluxes)):
            
            fluxes_str = '\t'.join(['%f'%j for j in fluxes[i]])
            
            output_str = "%s\t%s\t%s"%(filenames[i], times[i],fluxes_str)
            
            if options.output_file is None:
                print output_str
                continue
            
            new_fname = times[i].strftime(options.output_file)
            
            #check to see if we need to start a new file
            if write_output.cur_output_filename != new_fname:
                if ofp is not None:
                    ofp.close()                
                ofp = create_output_file(new_fname, image_dir, config)
                write_output.cur_output_filename = new_fname
            else:
                if ofp is None:
                    ofp = open(new_fname, "a")
            
            ofp.write(output_str)
            ofp.write("\n")
        
        if ofp is not None:
            ofp.close()
    
write_output.cur_output_filename = None    
    


    