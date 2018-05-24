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
import matplotlib.pyplot as plt

from plumetrack import flux


class SimpleErrorTestCase(unittest.TestCase):
    
    def test_zero_error_no_motion(self):
        cur_im = numpy.ones((2,3))
        flow = numpy.zeros((2,3,2))
        err = flux.compute_error_map(cur_im, cur_im, flow)
        self.assertTrue(numpy.all(err==0.0), "expecting zero error, got %s"%err)
    
    
    def test_zero_error_unity_motion(self):
        cur_im = numpy.ones((2,3))
        cur_im[0,0] = 2
        next_im = numpy.ones_like(cur_im)
        
        next_im[0,1] = 3
        next_im[0,0] = 0
        flow = numpy.zeros((2,3,2))
        flow[0,0,0] = 1
        
        err = flux.compute_error_map(cur_im, next_im, flow)
        self.assertTrue(numpy.all(err==0.0), "expecting zero error, got %s"%err)
    
    
    def test_zero_error_pix_exchange(self):
        cur_im = numpy.ones((2,3))
        next_im = numpy.ones_like(cur_im)
        flow = numpy.zeros((2,3,2))
        flow[0,0,0] = 1
        flow[0,1,0] = -1
        
        err = flux.compute_error_map(cur_im, next_im, flow)
        self.assertTrue(numpy.all(err==0.0), "expecting zero error, got %s"%err)
        
        
    def test_unity_error_no_motion(self):
        cur_im = numpy.ones((2,3))
        next_im = numpy.ones_like(cur_im)
        flow = numpy.zeros((2,3,2))
        
        next_im[1,2] = 2
        
        err = flux.compute_error_map(cur_im, next_im, flow)
        self.assertTrue(len(err[numpy.where(err!=0)].ravel())==1)
        self.assertTrue(err[1,2]==50.0)

    
    def test_fractional_motion(self):
        cur_im = numpy.ones((2,3))
        next_im = numpy.ones_like(cur_im)
        flow = numpy.zeros((2,3,2))
        
        next_im[0,0] = 0
        
        flow[0,0,0] = 1.5
        flow[0,0,1] = 0.5
        
        err = flux.compute_error_map(cur_im, next_im, flow)
        
        expected_err = numpy.ones_like(err) * 25.0
        expected_err[1,0] = 0.0

        self.assertTrue(numpy.all(err==expected_err))
        
        
#     def test_error(self):
#         cur_im = numpy.ones((2,3))
#         cur_im[0,0] = 2
#         #cur_im[0,1] = 1
#         next_im = numpy.ones_like(cur_im)
#         
#         next_im[0,1] = 3
#         next_im[0,0] = 0
#         flow = numpy.zeros((2,3,2))
#         flow[0,0,0] = 1
#         #flow[0,0,1] = 0.6
#         
#         err = flux.compute_error_map(cur_im, next_im, flow)
#         print err
#         plt.matshow(err,1)
#         plt.title("Error map")
#         plt.colorbar()
#         plt.show()
        
if __name__ == '__main__':
    unittest.main()        