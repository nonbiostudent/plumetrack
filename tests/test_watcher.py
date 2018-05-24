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
import os.path
import tempfile
import shutil
import datetime
import time

from plumetrack import watcher

def do_nothing():
    pass


class AvailabilityTestCase(unittest.TestCase):
    
    def test_availability(self):
        """
        Test that if can_watch_dirs returns True, that the returned Watcher is
        not None
        """
        dir_watcher = watcher.create_dir_watcher('.', False, do_nothing)
        
        if watcher.can_watch_directories():
            self.assertFalse(dir_watcher is None)
        else:
            self.assertTrue(dir_watcher is None)


class WatchingTestCase(unittest.TestCase):
    
    def setUp(self):
        """
        Create a temporary directory to watch
        """
        self.dir_name = tempfile.mkdtemp(suffix='', prefix='watch_test', dir=None)
        self.created_files = []
        self.creation_times = []
    
    def new_file_callback(self, filename, write_time):
        self.created_files.append(filename)
        self.creation_times.append(write_time)
    
    def tearDown(self):
        """
        remove any files/dirs which have been created
        """
        shutil.rmtree(self.dir_name)
        
    def test_nonrecursive_watching(self):
        """
        Test watching a directory for new files, ignoring any created in 
        subdirectories
        """
        dir_watcher = watcher.create_dir_watcher(self.dir_name, False, self.new_file_callback)
        
        if dir_watcher is None:
            return
        
        #start watching the dir
        dir_watcher.start()
        try:
            names = []
            times = []
            
            for i in range(100):
                new_file = os.path.join(self.dir_name,'tmp%d'%i)
                fd = open(new_file, 'w')
                times.append(datetime.datetime.utcnow())
                names.append(new_file)
                fd.close()
                time.sleep(0.001)
                
 
            #create a file and hold it open for some time - time recorded
            #by watcher should be first opened time
            new_file = os.path.join(self.dir_name,'tmp_held_open')
            fd = open(new_file, 'w')
            times.append(datetime.datetime.utcnow())
            names.append(new_file)
            time.sleep(1.3)
            fd.close()
            time.sleep(0.001)
            #create a file in a subdir (this should be ignored by the watcher)
            sub_dir = tempfile.mkdtemp(suffix='', prefix='subtmp', dir=self.dir_name)
            new_file = os.path.join(sub_dir,'tmp_in_subdir')
            fd = open(new_file, 'w')
            fd.close()
            time.sleep(1) #wait for watcher to finish
        finally:   
            dir_watcher.stop()
        
        self.assertTrue(len(self.created_files) == 101)
        self.assertTrue(len(self.creation_times) == 101)
        
        #check that the names found by the watcher match up
        for i in range(101):
            self.assertEqual(names[i], self.created_files[i])
            
        #check that the times are within ten millisecond of each other
        close_enough = datetime.timedelta(milliseconds=10)
        for i in range(101):
            self.assertTrue(abs(times[i] - datetime.datetime.utcfromtimestamp(self.creation_times[i]))< close_enough,
                            "difference = %s"%(str(abs(times[i] - datetime.datetime.fromtimestamp(self.creation_times[i])))))
        
    def test_recursive_watching(self):
        """
        Test watching a directory and all its subdirectories recursively.
        """
        dir_watcher = watcher.create_dir_watcher(self.dir_name, True, self.new_file_callback)
        
        if dir_watcher is None:
            return
        
        #start watching the dir
        dir_watcher.start()
        try:
            names = []
            times = []
            for j in range(2):
                subdir = tempfile.mkdtemp(suffix='', prefix='subtmp', dir=self.dir_name)
                
                for k in range(2):
                    subsubdir = tempfile.mkdtemp(suffix='', prefix='subsubtmp', dir=subdir)

                    for i in range(25):
                        new_file = os.path.join(subsubdir,'tmp%d'%i)
                        fd = open(new_file, 'w')
                        times.append(datetime.datetime.utcnow())
                        names.append(new_file)
                        fd.close()
                        time.sleep(0.001)
                        
            time.sleep(1) #wait for watcher to finish
        
        
        finally:   
            dir_watcher.stop()
        
        self.assertEqual(len(self.created_files), 100)
        
        #check that the names found by the watcher match up
        for i in range(100):
            self.assertEqual(names[i], self.created_files[i])
            
        #check that the times are within a millisecond of each other
        close_enough = datetime.timedelta(milliseconds=10)
        for i in range(100):
            self.assertTrue(abs(times[i] - datetime.datetime.fromtimestamp(self.creation_times[i]))< close_enough,
                            "difference = %s"%(str(abs(times[i] - datetime.datetime.fromtimestamp(self.creation_times[i])))))
        
            

if __name__ == '__main__':
    unittest.main()
