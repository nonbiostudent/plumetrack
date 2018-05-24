.. _section_loading_images:

Loading Images
==============

Supported Image Formats
-----------------------

Plumetrack uses OpenCV's `imread() <http://docs.opencv.org/modules/highgui/doc/reading_and_writing_images_and_video.html?highlight=imread#imread>`_ function to load image files. As such, it supports most popular image file formats such as JPEG, PNG and TIFF (depending on what plugins were enabled when OpenCV was built). A full list of supported formats can be found in the `imread() documentation <http://docs.opencv.org/modules/highgui/doc/reading_and_writing_images_and_video.html?highlight=imread#imread>`_. Images that are not supported natively can be loaded through the use of a custom image loader - see below.



Customised Preprocessing and Loading Unsupported Images
-------------------------------------------------------

In some situations it may be necessary to load image file formats which are not supported natively by Plumetrack. Furthermore, some custom preprocessing of images (cropping to a region of interest, filtering etc.) may be required. To facilitate both of these tasks, Plumetrack allows users to define their own "custom image loader". The custom image loader is just some Python code that Plumetrack calls on the image file prior to processing it. Creating a custom image loader is best demonstrated with an example:

In this example, lets assume that our images are in FITS format (which is not loadable with OpenCV's imread() function) and that we want to median filter the images before we process them with Plumetrack. To do this, we create a plain text file called "my_image_loader.py". Into the file we put the following:

.. code-block:: python

    from plumetrack import ImageLoader
    import pyfits
    import numpy
    import scipy.signal


    class FITSImageLoader(ImageLoader):
        
        def load(self, filename):
        
            hdulist = pyfits.open(filename)
            
            im = numpy.array(hdulist[0].data)
            
            im = scipy.signal.medfilt2d(im, kernel_size=5)
            
            t = self.time_from_fname(filename)
            
            return im, t
        
Now lets go through what all that means bit at a time.

.. code-block:: python

    from plumetrack import ImageLoader

ImageLoader is the class that Plumetrack normally uses to load images. We want to create a subclass of this in which we redefine (override) the load() method in order to load FITS images and perform our median filter.

.. code-block:: python

    import pyfits
    import numpy
    import scipy.signal
    
`pyfits <https://pypi.python.org/pypi/pyfits/3.3>`_ is the module that we will use to load the FITS file. It's not part of the standard Python install, so if you want to use it you will have to install it separately. `numpy <http://www.numpy.org/>`_ is a numerical library for Python. Plumetrack expects the load() method to return images as a NumPy array, so we also need this module. `scipy.signal <http://www.scipy.org/>`_ has a median filtering function which we will use.


.. code-block:: python

    class FITSImageLoader(ImageLoader):
        
        def load(self, filename):
        
Here we are defining a subclass of the ImageLoader class and overriding its load() method. The load() method takes the filename of the image to be loaded as an argument.

.. code-block:: python

    hdulist = pyfits.open(filename)
            
    im = numpy.array(hdulist[0].data)

The first line loads the contents of the FITS file (see the `pyfits documentation <http://pythonhosted.org/pyfits/>`_ for details. The second line extracts the pixel data and converts it to a NumPy array.

.. code-block:: python

    im = scipy.signal.medfilt2d(im, kernel_size=5)
    
This line median filters the image data, overwriting the original `im` array with a median filtered version of itself.

.. code-block:: python

    t = self.time_from_fname(filename)

The ImageLoader class defines a time_from_fname() method which extracts the capture time of an image from its filename (based on the filename_format that the user supplies - see :ref:`section_configuration`) and returns it as a datetime object. This method can also be overridden in order to load images whose capture times do not feature in their filenames - see example below.

.. code-block:: python

    return im, t

Your customised load() method needs to return both the image (as a NumPy array) and the corresponding capture time (as a datetime object).

To get Plumetrack to use your image loader rather than the default one, simply enable the "Custom Image Loader" checkbox in the graphical interface and set the value to the full path of the file which contains the definition ("my_image_loader.py" in this case).
        
Images Without Times in Their Filenames
---------------------------------------

Plumetrack is designed to work with sets of images whose capture times form part of their filenames. However, this may not always be the case. Custom image loaders can also be used to deal with image sets without capture times in their filenames, by overriding the time_from_fname() method of the standard loader. For example, lets consider a set of numerically named PNG files (000.png, 001.png etc) whose capture times are stored in the PNG header data. In this case we can define a custom image loader as shown below:

 .. code-block:: python
 
    from plumetrack import ImageLoader
    
    import datetime
    import Image
    
    class MyCustomLoader(ImageLoader):
    
        def time_from_fname(self, filename):
            """
            Overrides the base class method in order to read the capture time from
            the PNG file header.
            """
            
            # open the PNG file using the Python Image Library (PIL)
            im = Image.open(filename)
            
            # read the capture time string from the PNG header
            cap_time_string = im.info['capture time']
            
            # convert the string to a datetime object. Here we assume that the 
            # capture time is in the format 20151123_092555 (yearmonthday_hourminutesecond)
            cap_time = datetime.datetime.strptime(cap_time_string,"%Y%m%d_%H%M%S")
            
            return cap_time
            
The above code should be placed in a plain text file with a ".py" extension, and the full path of this file should be entered in the "Custom image loader" box in the Plumetrack graphical interface.           
            
            
