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

import unittest
import numpy
from pylab import *

from plumetrack import flux




class SimpleFluxesTestCase(unittest.TestCase):
    
    def setUp(self):
        
        self.image = numpy.ones((5, 5), dtype='float')
        self.configs = {
                        'integration_line':[[1.99, 0], [1.99, 4]], #vertical line in centre of image
                        'integration_direction': 1, #positive flux goes from left to right
                        'pixel_size': 1.0,
                        'flux_conversion_factor': 1.0
                        }
        
    
    def test_zero_flux(self):
        #if the velocities are all zero then we would expect zero flux
        flow = numpy.zeros((5, 5, 2), dtype='float')
        
        flux_engine = flux.AdvancedFluxEngine(self.configs)
        
        
        f = flux_engine.compute_flux(self.image, flow, 1.0)
        
        self.assertEqual(f, 0.0, "Expecting zero flux, got %f"%f)

    
    def test_unity_motion_flux(self):
        #if the flow is unity in the positive x direction, then we would expect 
        #a flux equal to the number of pixels in the y-direction of the image
        flow = numpy.zeros((5, 5, 2), dtype='float')
        flow[..., 0] = 1.0
        
        flux_engine = flux.AdvancedFluxEngine(self.configs)
        f = flux_engine.compute_flux(self.image, flow, 1.0)
        
        self.assertEqual(f, 5.0, "Expecting flux of 5, got %f"%f)
    
    
    def test_negativeunity_motion_flux(self):
        #if the flow is unity in the negative x direction, then we would expect 
        #a flux equal to negative of the number of pixels in the y-direction of 
        #the image
        flow = numpy.zeros((5, 5, 2), dtype='float')
        flow[..., 0] = -1.0
        
        flux_engine = flux.AdvancedFluxEngine(self.configs)
        
        f = flux_engine.compute_flux(self.image, flow, 1.0)
        
        self.assertEqual(f, -5.0, "Expecting flux of -5, got %f"%f)
    
    
    def test_parallel_motion_flux(self):
        #if the velocities are all parallel to the integration line (in this case
        #in the y-direction) then we would expect the flux to be zero
        
        #first try the positive y direction
        flow = numpy.zeros((5, 5, 2), dtype='float')
        flow[..., 1] = 1.0
        
        flux_engine = flux.AdvancedFluxEngine(self.configs)
        
        f = flux_engine.compute_flux(self.image, flow, 1.0)
        
        self.assertEqual(f, 0.0, "Expecting flux of 0, got %f"%f)
        
        #now the negative y direction
        flow = numpy.zeros((5, 5, 2), dtype='float')
        flow[..., 1] = -1.0
        
        flux_engine = flux.AdvancedFluxEngine(self.configs)
        
        f = flux_engine.compute_flux(self.image, flow, 1.0)
        
        self.assertEqual(f, 0.0, "Expecting flux of 0, got %f"%f)
    
    
    
    def test_angle_motion_flux(self):
        #if the flow is at 45 degrees and we set the bottom left 4 pixels to 
        #one, then we'd expect a flux of 4 (if the motion is fast enough)
        #first try the positive y direction
        
        #overwrite the image
        self.image = numpy.zeros_like(self.image)
        self.image[3:5,0:2] = 1.0
        
        flow = numpy.ones((5, 5, 2), dtype='float') * 10.0
        flow[...,1] *= -1
        flux_engine = flux.AdvancedFluxEngine(self.configs)
        
        f = flux_engine.compute_flux(self.image, flow, 1.0)
        
        self.assertEqual(f, 4.0, "Expecting flux of 4, got %f"%f)
        
    
     
class MultiSegmentFluxesTestCase(SimpleFluxesTestCase):
    #this class runs all the same tests as above, but for a multipart integration line
    def setUp(self):
        self.image = numpy.ones((5, 5), dtype='float')
        self.configs = {
                        'integration_line':[[1.99, 0], [1.99, 1],[1.99, 2],[1.99, 3],[1.99, 4]], #vertical line in centre of image
                        'integration_direction': 1, #positive flux goes from left to right
                        'pixel_size': 1.0,
                        'flux_conversion_factor': 1.0
                        }    
 




    
if __name__ == '__main__':
    unittest.main()
