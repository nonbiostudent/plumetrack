.. plumetrack documentation master file, created by
   sphinx-quickstart on Tue Sep  2 17:38:48 2014.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to plumetrack's documentation!
======================================

.. image:: _static/test.png
   :width: 400px
   :align: right

plumetrack is a `Python <http://www.python.org>`_ program for computing sulphur dioxide fluxes from SO2 camera data. It does *not* perform image calibration into SO2 column amounts. Instead it uses optical flow to calculate the velocity field between pre-calibrated images and allows integrations to be performed across arbitrary paths in the images to compute fluxes.

It is designed with volcanic monitoring in mind and can perform both real-time and batch processing of images.




Contents:

.. toctree::
   :maxdepth: 2
   
   installation
   quickstart
   configuration
   
   
   
.. toctree::
   :maxdepth: 1
      
   API


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

