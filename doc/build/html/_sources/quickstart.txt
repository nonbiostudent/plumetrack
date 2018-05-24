Quickstart
==========

The plumetrack distribution includes a few example images of Villarrica volcano in Chile along with an example configuration file, so that you can quickly get used to using the program. The following tutorial will guide you through processing these example images. The commands listed are for Windows users, Linux users need to substitute blackslashes for forward slashes.

To start, open a terminal and change directory to the examples folder of the plumetrack distribution::

  cd Desktop\plumetrack\examples

Then run the command::

  plumetrack -h

This should print a summary of commands that can be passed to the plumetrack program and what they mean. Now lets calculate some SO2 fluxes from the images. To do this, we will use the settings stored in the villarrica.cfg configuration file, which is provided in the examples folder. If you want to see what these settings are, you can open the villarrica.cfg file in a text editor. Full details of the configuration file format and what each of the settings does can be found in the :ref:`section_configuration` section of this documentation. To calculate the fluxes run the command::

  plumetrack -f villarrica.cfg villarrica

You should see some output much like that shown below::

	villarrica/20120208_201858.png	2012-02-08 20:18:58	1.194971
	villarrica/20120208_201901.png	2012-02-08 20:19:01	0.972490
	villarrica/20120208_201905.png	2012-02-08 20:19:05	1.088389
	villarrica/20120208_201908.png	2012-02-08 20:19:08	0.723179
	villarrica/20120208_201912.png	2012-02-08 20:19:12	1.065459
	villarrica/20120208_201915.png	2012-02-08 20:19:15	0.828853
	villarrica/20120208_201919.png	2012-02-08 20:19:19	1.039275
	villarrica/20120208_201922.png	2012-02-08 20:19:22	0.630464

The lefthand three columns give the filename, capture date and time of each image, and the righthand column gives the SO2 flux across our integration line (in kg per s). If you define multiple integration lines, then there will be additional columns to the right (one flux column for each integration line).


.. _date/time format specifiers: https://docs.python.org/2/library/datetime.html#strftime-strptime-behavior

.. note::

  If you want to write the fluxes to file (rather than printing them to the screen) you can use the ``-o`` option. The filename you use can contain the Python `date/time format specifiers`_ so that large amounts of output can be split accross many files. For example, if you want your output to be automatically split into daily files you could use ``-o %Y/%m/%d_fluxes.txt`` which will create a folder structure of <year>/<month>/<day>_fluxes.txt.

If your PC has multiple processing cores (as most modern PCs do), you might be interested in the ``-p`` option for plumetrack. Try running the command::

  plumetrack -p -f villarrica.cfg villarrica

This time, there should be a pause before any of the fluxes are printed to your screen, and then they should all be printed at once. This is because plumetrack has launched multiple processes to split the computation of the fluxes across all of your PCs processing cores. No results are printed until all the processes have completed. The time taken to compute all the fluxes should decrease approximately linearly with the number of processors/cores your PC has.

All this is very well, but it would be nice to see what is going on. For this we use the ``--output_pngs`` option. Run the command::

  plumetrack -p -f villarrica.cfg --output_pngs=output villarrica

When the command completes, you should find that a new folder called *output* has been created containing images which show plots of the UV images in the villarrica folder. The colour scale on the plots is the pixel values of the raw images (ppm.m in this case). The estimated velocity vectors are plotted as black arrows, and the integration line is shown in white.

You can now play with some of the settings in the configuration file and observe what effect they have on the produced velocity field/fluxes. Although the configuration file is a plain text file and can be edited directly, it is much easier to edit them using the configuration utility that comes with plumetrack. To launch the configuration utility run the command::

  plumetrack-config

Note that you can pass the name of the configuration file that you want to work with as a commandline argument if you want to e.g.::

  plumetrack-config villarrica.cfg
  
This will open a graphical window in which you can set all the configuration paramters. However, when editing a configuation it is useful to be able to see how the configuration paramters change the results. To do this, click the Test button at the bottom of the configuration utility. You will be prompted to select a folder containing images (select the examples/villarrica folder) and then a plotting window will open showing the motion field calculated using the current configuration options. The plotted motion field will update in realtime as you change the parameters in the configuration utility, easily allowing you to fine-tune the configuration. The configuration utility should be fairly self-explanatory, but see :ref:`section_configuration` for details of the different parameters which can be set.



