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

import matplotlib.pyplot as plt
import numpy
import scipy.interpolate


def create_motion_png(image, velocities, output_filename, integration_line):
    x_size = int(round((64.0/image.shape[0]) * image.shape[1],0))
    
    #plot the shift vectors (we interpolate onto a 50x50 grid so that there aren't too many vectors to plot)
    interp_x = numpy.linspace(0,image.shape[0],64)
    interp_y = numpy.linspace(0,image.shape[1],x_size)
    
    orig_x = numpy.arange(image.shape[0])
    orig_y = numpy.arange(image.shape[1])
    x_shift_interp = scipy.interpolate.RectBivariateSpline(orig_x, orig_y, velocities[...,0])
    x_shifts = x_shift_interp(interp_x,interp_y)
    
    y_shift_interp = scipy.interpolate.RectBivariateSpline(orig_x, orig_y, velocities[...,1])
    y_shifts = y_shift_interp(interp_x,interp_y)
    
    plt.close()
    plt.quiver(x_shifts, -y_shifts, units='xy', scale_units='xy',scale=1.5)
    extent = (0, x_size-1, 64-1, 0)
    plt.imshow(image, extent=extent)
    
    #plot the integration line
    scale_factor_x = float(x_size-1) / image.shape[0]
    scale_factor_y = 63.0 / image.shape[1]
    pts = integration_line.get_n_points(100)

    pts[:,0] *= scale_factor_x
    pts[:,1] *= scale_factor_y
    
    plt.plot(pts[:,0], pts[:,1], 'w-')
    
    plt.xlim((0,63))
    plt.ylim((x_size-1,0))
    plt.xticks([])
    plt.yticks([])
    plt.colorbar()
    plt.savefig(output_filename)