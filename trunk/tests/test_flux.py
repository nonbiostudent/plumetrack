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
import math
from pylab import *

from plumetrack import flux


class IntegrationLineTestCase(unittest.TestCase):
    def test_length(self):
        int_line = flux.IntegrationLine([0,0],[0,5],1)
        
        self.assertEqual(int_line.get_length(), 5.0, "Expecting a length of 5.0, got %f"%int_line.get_length())
        
        int_line = flux.IntegrationLine([0,5],[0,5],1)
        self.assertEqual(int_line.get_length(), 5.0 * math.sqrt(2.0), "Expecting a length of 5.0 * sqrt(2), got %f"%int_line.get_length())
        
    
    def test_get_npoints(self):
        int_line = flux.IntegrationLine([1,1,1],[0,3,5],1)
               
        self.assertTrue(numpy.all(int_line.get_n_points(-1)== numpy.array([[0.5,-0.5],[0.5,2.5],[0.5,4.5]])), "Expecting to retrieve [[0.5,-0.5],[0.5,2.5],[0.5,4.5]], got %s"%(str(int_line.get_n_points(-1))))



class Simple1DFluxesTestCase(unittest.TestCase):
    _flux_engine = flux.FluxEngine1D
    
    def setUp(self):
        
        self.image = numpy.ones((5, 5), dtype='float')
        self.configs = {
                        'integration_line':[[3, 0], [3, 5]], #vertical line in centre of image
                        'integration_direction': 1, #positive flux goes from left to right
                        'pixel_size': 1.0,
                        'flux_conversion_factor': 1.0
                        }
        
    def test_get_int_line(self):
        #ensure that we can retrieve the integration line object
        flux_engine = self._flux_engine(self.configs)   
        
        int_line = flux_engine.get_integration_line()
        
        self.assert_(isinstance(int_line, flux.IntegrationLine), "Failed to retrieve the integration line object from the flux engine")
    
    
    def test_zero_flux(self):
        #if the velocities are all zero then we would expect zero flux
        flow = numpy.zeros((5, 5, 2), dtype='float')
        
        flux_engine = self._flux_engine(self.configs)
        
        f = flux_engine.compute_flux(self.image, flow, 1.0)
        
        self.assertEqual(f, 0.0, "Expecting zero flux, got %f"%f)


    def test_line_outside_of_image(self):
        self.configs['integration_line'] = [[0,10],[20,10]]
        
        flow = numpy.zeros((5, 5, 2), dtype='float')
        flow[..., 0] = 1.0
        
        flux_engine = self._flux_engine(self.configs)
        f = flux_engine.compute_flux(self.image, flow, 1.0)
        
        self.assertEqual(f, 0.0, "Expecting flux of 5, got %f"%f)
    
    
    def test_unity_motion_flux(self):
        #if the flow is unity in the positive x direction, then we would expect 
        #a flux equal to the number of pixels in the y-direction of the image
        flow = numpy.zeros((5, 5, 2), dtype='float')
        flow[..., 0] = 1.0
        
        flux_engine = self._flux_engine(self.configs)
        f = flux_engine.compute_flux(self.image, flow, 1.0)
        
        self.assertEqual(f, 5.0, "Expecting flux of 5, got %f"%f)
    
    
    def test_unity_motion_flux_large_pixels(self):
        #if the flow is unity in the positive x direction, then we would expect 
        #a flux equal to the number of pixels in the y-direction of the image times
        #the square of the pixel size
        self.configs['pixel_size'] = 2.3
        
        flow = numpy.zeros((5, 5, 2), dtype='float')
        flow[..., 0] = 1.0
        
        flux_engine = self._flux_engine(self.configs)
        f = flux_engine.compute_flux(self.image, flow, 1.0)
        
        self.assertEqual(f, 2.3*2.3*5.0, "Expecting flux of %f, got %f"%(5.0*2.3**2,f))
    
    
    def test_unity_motion_diagonal_line_flux(self):
        #if the flow is unity in the positive x direction, then we would expect 
        #a flux equal to the number of pixels in the y-direction of the image - 
        #test this using a diagonal line.
        flow = numpy.zeros((5, 5, 2), dtype='float')
        flow[..., 0] = 1.0
        
        self.configs['integration_line'] = [[1.01,1],[4.01,4]]
        
        flux_engine = self._flux_engine(self.configs)
        f = flux_engine.compute_flux(self.image, flow, 1.0)
        
        self.assertEqual(f, 3.0, "Expecting flux of 3, got %f"%f)
    
    
    def test_unity_motion_oversizeline_flux(self):
        #if the flow is unity in the positive x direction, then we would expect 
        #a flux equal to the number of pixels in the y-direction of the image, but 
        #here we allow the integration line to extend beyond the edges of the image
        
        #redefine integration line
        self.configs['integration_line'] = [[3, -100], [3, 100]]
        
        flow = numpy.zeros((5, 5, 2), dtype='float')
        flow[..., 0] = 1.0
        
        flux_engine = self._flux_engine(self.configs)
        f = flux_engine.compute_flux(self.image, flow, 1.0)
        
        self.assertEqual(f, 5.0, "Expecting flux of 5, got %f"%f)
    
    
    def test_negativeunity_motion_flux(self):
        #if the flow is unity in the negative x direction, then we would expect 
        #a flux equal to negative of the number of pixels in the y-direction of 
        #the image
        flow = numpy.zeros((5, 5, 2), dtype='float')
        flow[..., 0] = -1.0
        
        flux_engine = self._flux_engine(self.configs)
        
        f = flux_engine.compute_flux(self.image, flow, 1.0)
        
        self.assertEqual(f, -5.0, "Expecting flux of -5, got %f"%f)
    
    
    def test_negativeunity_motion_diagonal_line_flux(self):
        #if the flow is unity in the negative x direction, then we would expect 
        #a flux equal to the negative number of pixels in the y-direction of the image - 
        #test this using a diagonal line.
        flow = numpy.zeros((5, 5, 2), dtype='float')
        flow[..., 0] = -1.0
        
        self.configs['integration_line'] = [[1.01,1],[4.01,4]]
        
        flux_engine = self._flux_engine(self.configs)
        f = flux_engine.compute_flux(self.image, flow, 1.0)
        
        self.assertEqual(f, -3.0, "Expecting flux of -3, got %f"%f)
    
    
    def test_parallel_motion_flux(self):
        #if the velocities are all parallel to the integration line (in this case
        #in the y-direction) then we would expect the flux to be zero
        
        #first try the positive y direction
        flow = numpy.zeros((5, 5, 2), dtype='float')
        flow[..., 1] = 1.0
        
        flux_engine = self._flux_engine(self.configs)
        
        f = flux_engine.compute_flux(self.image, flow, 1.0)
        
        self.assertEqual(f, 0.0, "Expecting flux of 0, got %f"%f)
        
        #now the negative y direction
        flow = numpy.zeros((5, 5, 2), dtype='float')
        flow[..., 1] = -1.0
        
        flux_engine = self._flux_engine(self.configs)
        
        f = flux_engine.compute_flux(self.image, flow, 1.0)
        
        self.assertEqual(f, 0.0, "Expecting flux of 0, got %f"%f)
    
    
    def test_nonuniform_image(self):
        #if one pixel along the integration line has a different value, check 
        #that this gets included into the flux correctly
        flow = numpy.zeros((5, 5, 2), dtype='float')
        flow[..., 0] = 1.0
        
        flux_engine = self._flux_engine(self.configs)
        
        for row in range(5):
            im = numpy.array(self.image) #copy of the array
            im[row, :] = 3.6
        
            f = flux_engine.compute_flux(im, flow, 1.0)
        
            self.assertEqual(f, 7.6, "Expecting flux of 7.6, got %f when row=%d"%(f,row))
    
    
    def test_nonuniform_image2(self):
        #if the pixels along the integration line have different values, check 
        #that this gets included into the flux correctly
        flow = numpy.zeros((5, 5, 2), dtype='float')
        flow[..., 0] = 1.0
        
        flux_engine = self._flux_engine(self.configs)
        
        im = numpy.array(self.image) #copy of the array
        
        for row in range(5):
            im[row, :] = row
        
        f = flux_engine.compute_flux(im, flow, 1.0)
        
        self.assertEqual(f, sum(range(5)), "Expecting flux of %d, got %f"%(sum(range(5)),f))
 
        
    
     
class MultiSegment1DFluxesTestCase(Simple1DFluxesTestCase):
    #this class runs all the same tests as above, but for a multipart integration line
    def setUp(self):
        self.image = numpy.ones((5, 5), dtype='float')
        self.configs = {
                        'integration_line':[[3, 0], [3, 1],[3, 2],[3, 3],[3, 5]], #vertical line in centre of image
                        'integration_direction': 1, #positive flux goes from left to right
                        'pixel_size': 1.0,
                        'flux_conversion_factor': 1.0
                        }
        
        
    def test_unity_motion_oversizeline_flux(self):
        #if the flow is unity in the positive x direction, then we would expect 
        #a flux equal to the number of pixels in the y-direction of the image, but 
        #here we allow the integration line to extend beyond the edges of the image
        
        #redefine integration line
        self.configs['integration_line'] = [[3, -100], [3, -50], [3, -25], [3, 25], [3, 100]]
        
        flow = numpy.zeros((5, 5, 2), dtype='float')
        flow[..., 0] = 1.0
        
        flux_engine = self._flux_engine(self.configs)
        f = flux_engine.compute_flux(self.image, flow, 1.0)
        
        self.assertEqual(f, 5.0, "Expecting flux of 5, got %f"%f)
    
        
    def test_line_outside_of_image(self):
        self.configs['integration_line'] = [[0,10],[3,10],[15,10],[20,10]]
        
        flow = numpy.zeros((5, 5, 2), dtype='float')
        flow[..., 0] = 1.0
        
        flux_engine = self._flux_engine(self.configs)
        f = flux_engine.compute_flux(self.image, flow, 1.0)
        
        self.assertEqual(f, 0.0, "Expecting flux of 5, got %f"%f)
            
    def test_unity_motion_diagonal_line_flux(self):
        #if the flow is unity in the positive x direction, then we would expect 
        #a flux equal to the number of pixels in the y-direction of the image - 
        #test this using a diagonal line.
        flow = numpy.zeros((5, 5, 2), dtype='float')
        flow[..., 0] = 1.0
        
        self.configs['integration_line'] = [[1.01,1],[2.01,2],[3.01,3],[4.01,4]]
        
        flux_engine = self._flux_engine(self.configs)
        f = flux_engine.compute_flux(self.image, flow, 1.0)
        
        self.assertEqual(f, 3.0, "Expecting flux of 3, got %f"%f)  
 

class Simple2DFluxesTestCase(Simple1DFluxesTestCase):
    _flux_engine = flux.FluxEngine2D


    def test_angle_motion_flux(self):
        
        #if the flow is at 45 degrees and we set the bottom left 4 pixels to 
        #one, then we'd expect a flux of 4 (if the motion is fast enough)
        #first try the positive y direction
        
        #overwrite the image
        self.image = numpy.zeros_like(self.image)
        self.image[3:5,0:2] = 1.0
        
        flow = numpy.ones((5, 5, 2), dtype='float') * 10.0
        flow[...,1] *= -1
        flux_engine = self._flux_engine(self.configs)
        
        f = flux_engine.compute_flux(self.image, flow, 1.0)
        
        self.assertEqual(f, 4.0, "Expecting flux of 4, got %f"%f)
        
        
class MultiSegment2DFluxesTestCase(Simple2DFluxesTestCase, MultiSegment1DFluxesTestCase):
    _flux_engine = flux.FluxEngine2D


#now try the tests with an image of incorrect data type
class IncorrectDataType1DTestCase(Simple1DFluxesTestCase):
    def setup(self):
        super(IncorrectDataType1DTestCase, self).setup()
        self.image = numpy.ones((5, 5), dtype='int32')


class IncorrectDataType2DTestCase(MultiSegment2DFluxesTestCase):
    def setup(self):
        super(IncorrectDataType2DTestCase, self).setup()
        self.image = numpy.ones((5, 5), dtype='int32')


#test with a closed loop integration line - this test also checks for reappearance
#of the bug related to unascending points on the integration line. These tests are
#also performed on non-square images
class ClosedLoopIntegration1D(unittest.TestCase):
    _flux_engine = flux.FluxEngine1D
    def setUp(self):
        self.image = numpy.ones((5, 10), dtype='float')
        self.configs = {
                        'integration_line':[[3, 2], [7, 2],[7, 4],[3, 4],[3, 2]], #vertical line in centre of image
                        'integration_direction': 1, #positive flux goes from left to right
                        'pixel_size': 1.0,
                        'flux_conversion_factor': 1.0
                        }
    
    def test_unity_flow(self):
        
        flow = numpy.zeros((5, 10, 2), dtype='float')
        flow[..., 0] = 1.0
        
        flux_engine = self._flux_engine(self.configs)
        f = flux_engine.compute_flux(self.image, flow, 1.0)
        #matshow(flux_engine.find_flux_contributions(flow))
        #colorbar()
        #show()
        self.assertEqual(f, 0.0, "Expecting flux of 0, got %f"%f)  
        
               
    def test_diagonal_flow(self):
        
        flow = numpy.zeros((5, 10, 2), dtype='float')
        flow[..., 0] = 1.0
        flow[..., 1] = -1.0
        flux_engine = self._flux_engine(self.configs)
        f = flux_engine.compute_flux(self.image, flow, 1.0)
        
        self.assertEqual(f, 0.0, "Expecting flux of 0, got %f"%f)


#now perform the closed loop tests for the 2D flux engine
class ClosedLoopIntegration2D(ClosedLoopIntegration1D):
    _flux_engine = flux.FluxEngine2D
            
if __name__ == '__main__':
    unittest.main()
