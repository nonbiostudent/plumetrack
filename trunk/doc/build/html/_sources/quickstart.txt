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

  2012-02-08 20:18:58	5.084186
  2012-02-08 20:19:01	4.143273
  2012-02-08 20:19:05	4.561784
  2012-02-08 20:19:08	3.115284
  2012-02-08 20:19:12	4.609075
  2012-02-08 20:19:15	3.623731
  2012-02-08 20:19:19	4.424330
  2012-02-08 20:19:22	2.774147

The lefthand two columns give the capture date and time of each image, and the righthand column gives the SO2 flux across our integration line (in kg per s). If your PC has multiple processing cores (as most modern PCs do), you might be interested in the ``-p`` option for plumetrack. Try running the command::

  plumetrack -p -f villarrica.cfg villarrica

This time, there should be a pause before any of the fluxes are printed to your screen, and then they should all be printed at once. This is because plumetrack has launched multiple processes to split the computation of the fluxes across all of your PCs processing cores. No results are printed until all the processes have completed. The time taken to compute all the fluxes should decrease approximately linearly with the number of processors/cores your PC has.

All this is very well, but it would be nice to see what is going on. For this we use the ``--output_pngs`` option. First create a new folder in the examples folder called *output*. Now run the command::

  plumetrack -p -f villarrica.cfg --output_pngs=output villarrica

When the command completes, you should find that the *output* folder now contains images which show plots of the UV images in the villarrica folder. The colour scale on the plots is the pixel values of the raw images (ppm.m in this case). The estimated velocity vectors are plotted as black arrows, and the integration line is shown in white.

You can now play with some of the settings in the configuration file and observe what effect they have on the produced velocity field/fluxes. For example, try using the supplied mask image (villarrica_mask.png) with  ``random_mean=1750`` and ``random_sigma=1000``. See :ref:`section_configuration` for details of the different parameters. 

.. note::

  If you want to write the fluxes to file (rather than printing them to the screen) you can use the ``-o`` option.
