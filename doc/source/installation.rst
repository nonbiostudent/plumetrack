
Installation
============

.. note::

  If you have an old version of Plumetrack installed on your computer, it is highly recommended to remove it before installing the latest version. 
  


Linux
-----

These instructions are for Ubuntu Linux, other distributions should be similar, but the package names may be slightly different.

  #. Use your package manager (e.g. Synaptic, apt-get etc.) to install the following packages: python-numpy, python-scipy, python-opencv, python-matplotlib, python-wxgtk2.8, python-pyinotify. For example (if you are using apt-get)::
  
      sudo apt-get install python-numpy python-scipy python-opencv python-matplotlib python-wxgtk2.8 python-pyinotify

  #. Download the Plumetrack distribution package (a .zip file) from `here <https://github.com/nonbiostudent/plumetrack/releases>`_.
  
  #. Right-click on the zip file and select "Extract here", or open a terminal and use the command::
  
      unzip plumetrack-x.x.zip 
      
    (where x.x is the version number).
  
  #. Open a terminal and navigate to the unpacked Plumetrack folder:: 
  
      cd plumetrack-x.x
  
  #. Then run the commands::
    
      python setup.py build
      sudo python setup.py install
  
  #. Plumetrack should now be installed. You can test the installation using::
  
      plumetrack -h
     
     If Plumetrack has installed correctly then the above command should print a list of command-line options that can be used with Plumetrack and their meanings.
     
  #. The graphical interface for Plumetrack should also have been added to your applications menu, so you can open it without needing to use the terminal.


Windows
-------

.. note:: There is a bundled executable of the Plumetrack GUI available for Windows users named plumetrack_gui_x.x.exe `here <https://github.com/nonbiostudent/plumetrack/releases>`_. This may be used "as is" without installing any dependencies (not even Python). However, it is a very large file, slow to open and lacks the parallel processing capabilities of the standard Plumetrack distributions. The bundled executable is only available for 64 bit systems.

If you do not already have Python installed on your system then it is recommended to use Anaconda. Anaconda is a version of Python which already includes many of the common Python packages (including most of the dependencies for Plumetrack), which makes installation of Plumetrack easier!


Prerequisites - Using Anaconda
..............................
Download and install Anaconda from `here <https://store.continuum.io/cshop/anaconda/>`_. Note, that you want the Python 2.7 version.

Unfortunately, Anaconda does not come with wxPython, and so you will need to install that separately. wxPython can be downloaded from `here <https://sourceforge.net/projects/wxpython/files/wxPython/3.0.2.0/>`_.

.. warning:: Plumetrack does not currently work with v4 (Phoenix) versions of wxPython. Please make sure you install wxPython3.x.

Now go to the OpenCV section below.


Prerequisites - Using an Existing Python Installation
.....................................................
If you already have a Python installation on your system, then you will need to install the following Python packages before installing Plumetrack:

 * `NumPy <http://www.numpy.org/>`_
 * `SciPy <http://www.scipy.org/>`_
 * `matplotlib <http://matplotlib.org/>`_
 * `pywin32 <http://sourceforge.net/projects/pywin32>`_
 * `wxPython <https://sourceforge.net/projects/wxpython/files/wxPython/3.0.2.0/>`_
 
.. warning:: Plumetrack does not currently work with v4 (Phoenix) versions of wxPython. Please make sure you install wxPython3.x.

Installing OpenCV
.................

To install the Python bindings for the OpenCV library:

 #. Download the latest version of OpenCV from `here <http://opencv.org/downloads.html>`_.
 
 #. Unpack the archive (if you downloaded the .exe version then it is a self-extracting archive and all you need to do is run the executable). 

 #. Navigate to the unpacked folder and go to build\\python\\<n.n>\\<arch> where <n.n> is your Python version (probably 2.7) and <arch> is the architecture of your system (x86 if you are running 32bit and x64 if you are running 64bit). 

 #. Copy the cv2.pyd file into the site-packages directory of your Python install, for people using Anaconda this will be something like C:\\Anaconda\\Lib\\site-packages and for people using a standard Python install it will be C:\\Python27\\Lib\\site-packages


Installing Plumetrack
.....................

Once you have installed all of the dependencies, then installation of Plumetrack itself should be relatively straightforward. You can either download and run one of the executable installers (.exe files) from `here <https://github.com/nonbiostudent/plumetrack/releases>`_, or you can follow the instructions below to install from source:

 #. Download the Plumetrack distribution package (a .zip file) from `here <https://github.com/nonbiostudent/plumetrack/releases>`_.
 
 #. Unzip the package.
 
 #. Open a terminal (start->run->cmd.exe).
 
 #. Navigate to the unzipped Plumetrack folder. For example::
     
     cd plumetrack-x.x
   (where x.x is the version number).
 
 #. Install Plumetrack using the following commands::

     python setup.py build
     python setup.py install

 #. If the previous commands gave you the error ''python' is not recognised as an internal or external command, operable or batch file', then you need to add c:\\python27 to your system path (or c:\\anaconda if you are using anaconda) there are some instructions for this `here <http://stackoverflow.com/questions/6318156/adding-python-path-on-windows-7>`_.
 
 #. Add the C:\\Python27\\Scripts (or C:\\Anaconda\\Scripts) directory to your system path, following the same procedure as above.

 #. Open a new terminal and type::
     
     plumetrack -h
  
  This should print a summary of options that can be passed to Plumetrack. If this works, then you're done!
  
.. note::

 If you used one of the executable installers for Plumetrack, then a Start Menu entry should have been created for the graphical interface to Plumetrack. You can therefore open it as you would any other program.





