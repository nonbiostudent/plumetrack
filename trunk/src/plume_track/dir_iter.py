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

import os.path
import Queue
import threading
import glob
import itertools

from plume_track.watcher import create_dir_watcher, can_watch_directories

"""
The dir_iter module provides an iterator class for iterating through the files
in a directory structure. In its most simple form it can be used to list 
the files in a directory (much like os.listdir()). However, it can also be used
to list files in realtime as they are created (using the watcher module).

The following code shows how the dir_iter module can be used to print the names
of any new files created in a directory:

    from plume_track import dir_iter
    
    for filename in dir_iter.DirFileIter("my_directory", realtime=True):
        print filename
    
"""

def find_files(path, recursive=False, pattern='*', skip_links=True, full_paths=False):
    """
    Returns a list of files in a directory with various filter options applied.
    
        * path - the directory to search for files
        * recursive - boolean controls whether to search sub-directories or not
        * pattern - Unix "glob" type pattern to match for filenames.
        * skip_links - boolean controls whether links are followed or not
        * full_paths - boolean controls whether the filenames returned are full
                       paths or relative paths.
    """
    if not os.path.isdir(path):
        raise ValueError, "\'%s\' is not a recognised folder" %path
    
    found_files = [os.path.join(path,n) for n in glob.glob1(path,pattern)]
    path_contents = [os.path.join(path,n) for n in os.listdir(path)]
    
    if skip_links:
        path_contents = [x for x in itertools.ifilterfalse(os.path.islink, path_contents)]
    
    dirs = [x for x in itertools.ifilter(os.path.isdir, path_contents)]
    found_files = [x for x in itertools.ifilterfalse(os.path.isdir, found_files)] #now with no dirs in it  

    if recursive:
        found_files += [find_files(x, recursive, pattern, skip_links, full_paths) for x in dirs]
        
    if full_paths:
        return [os.path.abspath(x) for x in flatten(found_files) if x]
    else:
        return [x for x in flatten(found_files) if x]



def flatten(l, ltypes=(list, tuple)):
    """
    Reduces any iterable containing other iterables into a single list
    of non-iterable items. The ltypes option allows control over what 
    element types will be flattened. This algorithm is taken from:
    http://rightfootin.blogspot.com/2006/09/more-on-python-flatten.html
    
    >>> print flatten([range(3),range(3,6)])
    [0, 1, 2, 3, 4, 5]
    >>> print flatten([1,2,(3,4)])
    [1, 2, 3, 4]
    >>> print flatten([1,[2,3,[4,5,[6,[7,8,[9,[10]]]]]]])
    [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    >>> print flatten([1,[2,3,[4,5,[6,[7,8,[9,[10]]]]]]], ltypes=())
    [1, [2, 3, [4, 5, [6, [7, 8, [9, [10]]]]]]]
    >>> print flatten([1,2,(3,4)],ltypes=(list))
    [1, 2, (3, 4)]
    """
    ltype = type(l)
    l = list(l)
    i = 0
    while i < len(l):
        while isinstance(l[i], ltypes):
            if not l[i]:
                l.pop(i)
                i -= 1
                break
            else:
                l[i:i + 1] = l[i]
        i += 1
    return ltype(l)



class DirFileIter:
    def __init__(self, directory, realtime=False, skip_existing=False, 
                 recursive=False, sort_func=cmp, test_func=None):
        """
        Iterator class which returns the filenames in a directory structure, with
        the option of monitoring for new files in realtime.
        
            * directory - the directory to list the files in
            * realtime - boolean controls whether to continuously monitor the
                         directory for new files
            * skip_existing - boolean controls whether to return the files that
                              already exist in the directory (if set to False, 
                              then only files created after the iterator will be
                              returned).
            * recursive - boolean controls whether to list files in sub-directories
            * sort_func - a comparator function used to sort the list of exisiting
                          files before they are returned. Default is that they 
                          are sorted by name. Note that once all the existing 
                          filenames have been returned, filenames will be 
                          returned in the order that they are created regardless
                          of what sort_func is set to.
            * test_func - optional test function which should take a filename as
                          its only argument and return True or False. Only filenames
                          which evaluate to True with the test function will
                          be returned from the iterator. Setting this to None 
                          results in all filenames being returned.
        """
        
        if not os.path.isdir(directory):
            raise ValueError("Cannot access "+directory+". No such directory.")
        
        if skip_existing and not realtime:
            raise RuntimeError("If skip_existing is set to True then realtime "
                               "must also be set to True (otherwise no files " 
                               "will be returned).")
        
        self.__dir = directory
        self.__sort_func = sort_func
        self.__test_func = test_func
        self._filename_q = Queue.Queue()
        self.__realtime_filename_q = Queue.Queue()
        self._stay_alive = True
        self.__existing_loader_thread = None
        self._realtime_loader_thread = None
        self._finished_loading_existing_lock = threading.Lock()
        self._finished_loading_existing_lock.acquire()
        self.__existing_files_found = {}
        self.__recursive = recursive
        
        #note that we start the realtime loader thread BEFORE the existing loader thread
        #this is to prevent spectra that are created during the find_files() call being 
        #skipped.
        if realtime:
            if not can_watch_directories():
                raise RuntimeError("No directory watching implementation available on this system")
            
            self._realtime_loader_thread = threading.Thread(target=self.__load_realtime)
            self._realtime_loader_thread.start()
              
        if not skip_existing:
            self.__existing_loader_thread = threading.Thread(target=self.__load_existing)
            self.__existing_loader_thread.start()
        else:
            self._finished_loading_existing_lock.release()

           
    def __iter__(self):
        """
        Method required by iterator protocol. Allows iterator to be used in 
        for loops.
        """
        return self
    

    def __next__(self):
        #needed for Py3k compatibility
        return self.next()
        
        
    def next(self):
        """
        Method required by iterator protocol. Returns the next filename found
        or raises StopIteration if there are no files left to list (or if 
        close() has been called on the iterator.
        
        Note that if the iterator was created with the realtime option set to 
        True, then this method will block until a new file is detected (or until
        close() is called).
        """
        s = self._filename_q.get(block=True)
        
        if s is None or not self._stay_alive:
            
            raise StopIteration
        
        return s

    
    def close(self):
        """
        This is only needed if the iterator was created with the realtime option
        set to True. Calling close() stops the iterator from waiting for new
        files and causes any pending calls to next() to raise StopIteration.
        """
        self._stay_alive = False
        
        #the loader threads may be blocking waiting to put something into the queue
        while True:
            try:
                self._filename_q.get(block=False)
            except Queue.Empty:
                break
            
        #the next() method may be blocking waiting to get something from the queue
        try:
            self._filename_q.put(None, block=False)
        except Queue.Full:
            pass
        
        #the realtime loader thread may be blocking waiting to get a new filename to load
        try:
            self.__realtime_filename_q.put(None)
        except Queue.Full:
            pass
                  
        if self.__existing_loader_thread is not None:
            self.__existing_loader_thread.join()
            
        if self._realtime_loader_thread is not None:
            self._realtime_loader_thread.join()
               
    
       
    def __load_existing(self):
        
        try: 
            #find_files is slow so use listdir if we don't need to be recursive
            if self.__recursive:
                existing_files = find_files(self.__dir, recursive=True)
            else:
                existing_files = [os.path.join(self.__dir, n) for n in os.listdir(self.__dir)]
            
            #if a test function was specified, then only keep the filenames which satisfy it
            if self.__test_func is not None:
                existing_files = [x for x in itertools.ifilter(self.__test_func, existing_files)]
                
            #sort the filenames using the comparator function specified in the 
            #kwargs to the constructor of the DirFilesIter object
            existing_files.sort(cmp=self.__sort_func)
            
            #create a dict of all the files found so that we can check for 
            #duplicates when the realtime loader thread starts returning filenames
            for filename in existing_files:
                self.__existing_files_found[filename] = None
                self._filename_q.put(filename)
                       
        finally:
            self._finished_loading_existing_lock.release()
            
        if self._realtime_loader_thread is None:        
            #put None into the queue so that the iteration finishes when the q is emptied
            self._filename_q.put(None)
            
    
    
    def __load_realtime(self):
        
        put_into_q = lambda f,t,q: q.put(f)
        
    
        watcher = create_dir_watcher(self.__dir, self.__recursive,
                                     put_into_q, self.__realtime_filename_q)
        watcher.start()
        
        #wait for the existing files to be found
        self._finished_loading_existing_lock.acquire()
        self._finished_loading_existing_lock.release()
        
        #skip any files that were picked up by the existing loader
        while self._stay_alive:
            filename = self.__realtime_filename_q.get(block=True)
            
            if filename is None:
                break
            
            if self.__test_func is not None and not self.__test_func(filename):
                continue
            
            if not self.__existing_files_found.has_key(filename):
                break
        
        self.__existing_files_found = {} #done with this dict now - leave it to be GC'd
        
        while self._stay_alive:         
            if filename is None:
                break

            try:
                if self.__test_func is not None and not self.__test_func(filename):
                    continue
                
                self._filename_q.put(filename, block=False)

            except Queue.Full:
                #if the output queue is full, then just skip the file - otherwise it might block
                #forever
                print "Warning! Filename output queue is full - skipping file \'"+filename+"\'"
                   
            filename = self.__realtime_filename_q.get(block=True)
        
        watcher.stop()
