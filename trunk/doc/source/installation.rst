
Installation
============

Since plumetrack is still in a fairly early stage of development, installation (especially on Windows) might be a little tricky. Hopefully, this will be gradually improved on in the future. In the meantime, please help to improve useability by reporting any installation problems you have.


Windows
-------

If you do not already have Python installed on your system then it is recommended to use Anaconda. Anaconda is a version of Python which already includes many of the common Python packages (including most of the dependencies for plumetrack), which makes installation of plumetrack easier!


Prerequisites - Using Anaconda
..............................
Download and install Anaconda from `here <https://store.continuum.io/cshop/anaconda/>`_. Note, that you want the Python 2.7 version.

Unfortunately, Anaconda does not come with wxPython, and so you will need to install that separately. wxPython can be downloaded from `here <http://www.wxpython.org/>`_.

Now go to the OpenCV section below.


Prerequisites - Using an Existing Python Installation
.....................................................
If you already have a Python installation on your system, then you will need to install the following Python packages before installing plumetrack:

 * `NumPy <http://www.numpy.org/>`_
 * `SciPy <http://www.scipy.org/>`_
 * `matplotlib <http://matplotlib.org/>`_
 * `pywin32 <http://sourceforge.net/projects/pywin32>`_
 * `wxPython <http://www.wxpython.org/>`_


Installing OpenCV
.................

To install the Python bindings for the OpenCV library:

 #. Download the latest version of OpenCV from `here <http://opencv.org/downloads.html>`_.
 
 #. Unpack the archive (if you downloaded the .exe version then it is a self-extracting archive and all you need to do is run the executable). 

 #. Navigate to the unpacked folder and go to build\\python\\<n.n>\\<arch> where <n.n> is your Python version (probably 2.7) and <arch> is the architecture of your system (x86 if you are running 32bit and x64 if you are running 64bit). 

 #. Copy the cv2.pyd file into the site-packages directory of your Python install, for people using Anaconda this will be something like C:\\Anaconda\\Lib\\site-packages and for people using a standard Python install it will be C:\\Python27\\Lib\\site-packages


Installing plumetrack
.....................

Once you have installed all of the dependencies, then installation of plumetrack itself should be relatively straightforward.

 #. Download the plumetrack distribution package (a .zip file) from `here <http://ccpforge.cse.rl.ac.uk/gf/project/plumetrack/frs>`_.
 
 #. Unzip the package.
 
 #. Open a terminal (start->run->cmd.exe).
 
 #. Navigate to the unzipped plumetrack folder. For example::
     
     cd plumetrack-14.11
 
 #. Install plumetrack using the following commands::

     python setup.py build
     python setup.py install

 #. If the previous commands gave you the error ''python' is not recognised as an internal or external command, operable or batch file', then you need to add c:\\python27 to your system path (or c:\\anaconda if you are using anaconda) there are some instructions for this `here <http://stackoverflow.com/questions/6318156/adding-python-path-on-windows-7>`_.
 
 #. Add the C:\\Python27\\Scripts (or C:\\Anaconda\\Scripts) directory to your system path, following the same procedure as above.

 #. Open a new terminal and type::
     
     plumetrack -h
  
  This should print a summary of options that can be passed to plumetrack. If this works, then you're done!



Installing plumetrack from SVN
..............................

If you want the very latest version of plumetrack (and be advised that this may not be very stable!) then you can install it from the SVN repository. To do this you need an SVN client, which you can get from `here <http://sourceforge.net/projects/win32svn>`_. Once you have installed an SVN client:

 #. Create a folder on your desktop called plumetrack.

 #. Open a terminal (start->run->cmd.exe).

 #. Navigate to the plumetrack folder you just created::
     
     cd Desktop\plumetrack

 #. Check out a copy of the plumetrack repository by entering the following command::
     
     svn checkout http://ccpforge.cse.rl.ac.uk/svn/plumetrack/trunk .

 #. When prompted for a password press enter (blank password). When prompted for a username enter 'anonymous'.

 #. You should now have a full checkout of the plumetrack code. Install plumetrack using the following commands::

     python setup.py build
     python setup.py install

 #. If the previous commands gave you the error ''python' is not recognised as an internal or external command, operable or batch file', then you need to add c:\\python27 to your system path (or c:\\anaconda if you are using anaconda) there are some instructions for this `here <http://stackoverflow.com/questions/6318156/adding-python-path-on-windows-7>`_.

 #. Add the C:\\Python27\\Scripts (or C:\\Anaconda\\Scripts) directory to your system path.

 #. Open a new terminal and type::
     
     plumetrack -h
  
  This should print a summary of options that can be passed to plumetrack. If this works, then you're done!
 



