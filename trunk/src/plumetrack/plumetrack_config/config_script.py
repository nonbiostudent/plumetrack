#Copyright (C) Nial Peters 2014
#
#This file is part of plumetrack.
#
#plumetrack is free software: you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.
#
#_plumetrack is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with plumetrack.  If not, see <http://www.gnu.org/licenses/>.

import wx
import wx.html
import os
import json
import cv2
import sys
import numpy
from optparse import OptionParser
import matplotlib
matplotlib.use('wxagg')
import matplotlib.cm

from wx.lib.agw import floatspin
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg
from matplotlib.figure import Figure

import plumetrack
from plumetrack import plumetrack_config
from plumetrack import settings, flux,  persist
from plumetrack.plumetrack_config import config_test_frame


def main():
    """
    Runs the main program - this is set as the entry point for the configuration
    utility in the setup.py file.
    """
    
    app = PlumetrackConfigApp()
    app.MainLoop()
    


###############################################################
# Here we subclass a bunch of wx widgets so that when their values
# change they call the on_config_change method of the main frame to trigger
# an update to the config_test_frame (if it exists).
class AutoUpdate:
    def on_change(self, evnt):
        wx.GetApp().main_frame.on_config_change()
        evnt.Skip()    


class AutoUpdateCheckbox(wx.CheckBox, AutoUpdate):
    def __init__(self,*args, **kwargs):
        super(AutoUpdateCheckbox, self).__init__(*args, **kwargs)
        wx.EVT_CHECKBOX(self, self.GetId(), self.on_change)


class AutoUpdateFloatspin(floatspin.FloatSpin, AutoUpdate):
    def __init__(self,*args, **kwargs):
        super(AutoUpdateFloatspin, self).__init__(*args, **kwargs)
        floatspin.EVT_FLOATSPIN(self, self.GetId(), self.on_change)


class AutoUpdateSpinCtrl(wx.SpinCtrl, AutoUpdate):
    def __init__(self,*args, **kwargs):
        super(AutoUpdateSpinCtrl, self).__init__(*args, **kwargs)
        wx.EVT_SPINCTRL(self, self.GetId(), self.on_change) 


class AutoUpdateTextCtrl(wx.TextCtrl, AutoUpdate):
    def __init__(self,*args, **kwargs):
        super(AutoUpdateTextCtrl, self).__init__(*args, **kwargs)
        self._text_updated = False
        wx.EVT_TEXT_ENTER(self, self.GetId(), self.on_change)
        wx.EVT_KILL_FOCUS(self, self.on_lose_focus)
        wx.EVT_TEXT(self, self.GetId(), self.on_text_change)
    
    def on_change(self, evnt):
        self._text_updated = False
        AutoUpdate.on_change(self, evnt)
    
    def on_lose_focus(self, evnt):
        if self._text_updated:
            self.on_change(evnt)
    
    def on_text_change(self, evnt):
        self._text_updated=True

########################################################################


class PlumetrackConfigApp(wx.App):
    def __init__(self):
        """
        wxApp for the plumetrack configuration program. 
        """
        self.main_frame = None
        
        super(PlumetrackConfigApp, self).__init__()
    
    
    def OnInit(self):
        
        options, args = self._parse_cmd_line()
        
        #launch the GUI!
        self.main_frame = MainFrame()
        self.SetTopWindow(self.main_frame)
        
        if len(args) == 0:
            try:
                prev_cfg_file = persist.PersistentStorage().get_value("config_script_prev_file")
                
                if not os.path.exists(prev_cfg_file):
                    prev_cfg_file = None
                     
            except KeyError:
                prev_cfg_file = None
        else:
            prev_cfg_file = os.path.abspath(args[0])
            
        
        self.main_frame.launch(prev_cfg_file)
        return True


    def _parse_cmd_line(self):
        """
        Function parses the command line input and returns a tuple
        of (options, args)
        """
        usage = ("%prog [options] [config. file]")
        
        parser = OptionParser()
        
        parser.prog = plumetrack_config.PROG_SHORT_NAME
        parser.usage = usage
        parser.description = plumetrack_config.LONG_DESCRIPTION
        
        parser.add_option("", "--version", action="callback", 
                  callback=self.__print_version_and_exit, help=("Print plumetrack"
                  " version number and license information and exit."))
        
        
        (options, args) = parser.parse_args()
        
        if len(args) > 1:
            parser.error("Only one config file can be specified. Files with "
                         "spaces in their names should be enclosed in quotation marks")
        
        if len(args) == 1:
            if not os.path.exists(args[0]):
                parser.error("Cannot open config file \'%s\'. No such file."%(args[0]))
        
        
        return (options, args)
        

    def __print_version_and_exit(self, *args):
        """
        Prints the version number and license information for plumetrack.
        """
        print "%s (version %s)"%(plumetrack_config.PROG_SHORT_NAME, plumetrack_config.VERSION)
        print plumetrack_config.COPYRIGHT
        print plumetrack_config.LICENSE_SHORT
        print ""
        print "Written by %s."%plumetrack_config.AUTHOR
        sys.exit(0)



class ConfigFileSelect(wx.Panel):
    def __init__(self, parent, main_frame, filename):
        super(ConfigFileSelect, self).__init__(parent)
        
        self.main_frame = main_frame
        vsizer = wx.BoxSizer(wx.VERTICAL)
        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        
        self.im_dir_box = wx.TextCtrl(self, -1, size=(250,-1))
        self.browse_button = wx.Button(self, -1, "Browse")
        h_txt = ("Select an existing configuration file to load parameters from."
                 " This can be either a \'.cfg\' configuration file, or a "
                 "results file produced by a previous plumetrack run.")
        self.im_dir_box.SetToolTipString(h_txt)
        self.browse_button.SetToolTipString(h_txt)
        wx.EVT_BUTTON(self, self.browse_button.GetId(), self.on_browse)
        
        hsizer.Add(self.im_dir_box, 1, wx.EXPAND|wx.ALIGN_LEFT|wx.ALIGN_CENTRE_VERTICAL)
        hsizer.AddSpacer(5)
        hsizer.Add(self.browse_button, 0, wx.ALIGN_LEFT|wx.ALIGN_CENTRE_VERTICAL)
        
        self.load_button = wx.Button(self, -1, "Load")
        h_txt = ("Load the configuration parameters from the currently "
                 "selected file. This will overwrite any parameters already "
                 "defined below.")
        self.load_button.SetToolTipString(h_txt)
        wx.EVT_BUTTON(self, self.load_button.GetId(), self.on_load)
        
        #set the default config file to load
        self.im_dir_box.SetValue(filename)
        
        vsizer.Add(hsizer, 0, wx.EXPAND)
        vsizer.AddSpacer(5)
        vsizer.Add(self.load_button, 0, wx.ALIGN_BOTTOM|wx.ALIGN_RIGHT)
        self.SetSizer(vsizer)
        vsizer.Fit(self)
    
    
    def on_browse(self, evnt):
        filename = wx.FileSelector("Select configuration file")
        if filename != "":
            self.im_dir_box.SetValue(filename)
    
    
    def on_load(self, evnt):
        filename = self.im_dir_box.GetValue()
        
        try:
            config = settings.load_config_file(filename)
            self.main_frame.set_configs(config)
        except settings.ConfigError, ex:
            wx.MessageBox(ex.args[0])
        except IOError, ex:
            wx.MessageBox(ex.args[0])



class InputFilesConfig(wx.Panel):
    def __init__(self, parent):
        super(InputFilesConfig, self).__init__(parent)
        
        vsizer = wx.BoxSizer(wx.VERTICAL)
        
        sizer = wx.FlexGridSizer(2, 5, 10, 0)
        sizer.AddGrowableCol(1,1)
        
        self.filename_format_box = AutoUpdateTextCtrl(self, -1, size=(250,-1), style=wx.TE_PROCESS_ENTER)
        h_txt = ("The format of the filenames of the images to be processed. "
                 "The filenames must include the capture time of the images, "
                 "and the format must be described using the Python strftime "
                 "format. Click the Help button for details of the format. "
                 "The filename format entered here should include "
                 "the file extension.")
        self.filename_format_box.SetToolTipString(h_txt)
        
        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        hsizer.Add(wx.StaticText(self, -1, "Filename format:"), 0, 
                  wx.ALIGN_RIGHT | wx.ALIGN_CENTRE_VERTICAL)
        hsizer.Add(self.filename_format_box, 1, 
                  wx.EXPAND | wx.ALIGN_LEFT | wx.ALIGN_CENTRE_VERTICAL)
        
        format_help_button = wx.Button(self, -1, "Help")
        hsizer.Add(format_help_button, 0, wx.ALIGN_LEFT | wx.ALIGN_CENTRE_VERTICAL)
        vsizer.Add(hsizer, 0, wx.EXPAND | wx.ALIGN_LEFT | wx.ALIGN_CENTRE_VERTICAL)
        wx.EVT_BUTTON(self, format_help_button.GetId(), self.on_help)
        
        sizer.Add(wx.StaticText(self, -1, "File extension:"), 0, 
                  wx.ALIGN_RIGHT | wx.ALIGN_CENTRE_VERTICAL)
        self.file_extension_box = AutoUpdateTextCtrl(self, -1, size=(100,-1), style=wx.TE_PROCESS_ENTER)
        h_txt = ("The file extension of your image files to be processed e.g. "
                 "'.png' or '.jpg'. This may be specified with or without the "
                 "preceding dot. It must match the file extension given in the "
                 "filename format box above.")
        self.file_extension_box.SetToolTipString(h_txt)
        sizer.Add(self.file_extension_box, 0, wx.ALIGN_LEFT|wx.ALIGN_CENTRE_VERTICAL)
        
        sizer.AddSpacer((10, 1))
        
        sizer.Add(wx.StaticText(self, -1, "Pixel size (metres):"), 0, 
                  wx.ALIGN_RIGHT | wx.ALIGN_CENTRE_VERTICAL)
        self.pixel_size_box = AutoUpdateFloatspin(self, wx.ID_ANY, min_val=0.01, 
                                                  max_val=50.0, increment=0.1, 
                                                  digits=2)
        h_txt = ("The size of the pixels in the images. Note that this is the "
                 "length in metres along one pixel dimension, not the area of "
                 "the pixel.")
        self.pixel_size_box.SetToolTipString(h_txt)
        sizer.Add(self.pixel_size_box, 0, wx.ALIGN_LEFT|wx.ALIGN_CENTRE_VERTICAL)
        
        
        sizer.Add(wx.StaticText(self, -1, "Downsizing factor:"), 0, wx.ALIGN_RIGHT|wx.ALIGN_CENTRE_VERTICAL)
        self.downsizing_factor = AutoUpdateFloatspin(self, wx.ID_ANY, min_val=1.0,
                                                          increment=0.5, digits=1)
        h_txt = ("A downsizing factor of >1.0 means that images will be"
                 " scaled (resized) by this factor before being processed. This "
                 "results in a less accurate flux estimate, but increased "
                 "processing speed.")
        self.downsizing_factor.SetToolTipString(h_txt)
        sizer.Add(self.downsizing_factor, 0, wx.ALIGN_LEFT|wx.ALIGN_CENTRE_VERTICAL)
        
        sizer.AddSpacer((10, 1))
        
        sizer.Add(wx.StaticText(self, -1, "Units conversion factor:"), 0, wx.ALIGN_RIGHT|wx.ALIGN_CENTRE_VERTICAL)
        self.flux_conversion_factor = AutoUpdateTextCtrl(self, -1, size=(150,-1), style=wx.TE_PROCESS_ENTER)
        h_txt = ("This is used in conjunction with the pixel_size parameter to "
                 "convert the pixel values in your images into SO2 masses. You "
                 "need to select a value for this parameter such that SO2_mass "
                 "= pixel_value * pixel_size^2 * flux_conversion_factor. The "
                 "fluxes returned will then have units of SO2-mass-units per "
                 "second.")
        self.flux_conversion_factor.SetToolTipString(h_txt)
        sizer.Add(self.flux_conversion_factor, 0, wx.ALIGN_LEFT|wx.ALIGN_CENTRE_VERTICAL)
        
        vsizer.AddSpacer(10)
        vsizer.Add(sizer, 1, wx.ALIGN_LEFT)
        
        self.SetSizer(vsizer)
        vsizer.Fit(self)
    
    
    def on_help(self, evnt):
        help_frame = wx.Frame(self, -1, "Filename format help - plumetrack-config ")
        w = wx.html.HtmlWindow(help_frame, -1)
        w.SetPage(html_help_str)
        help_frame.Show()
    
     
    def get_configs(self):
        
        file_extension = self.file_extension_box.GetValue()
        
        if file_extension.isspace() or file_extension == "":
            raise settings.ConfigError("File extension not specified.")
        
        #make sure that the filename extension includes the dot
        if not file_extension.startswith('.'):
            file_extension = '.'+file_extension
        
        filename_format = self.filename_format_box.GetValue()
        if filename_format.isspace() or filename_format == "":
            raise settings.ConfigError("Filename format not specified")
        
        flux_conversion_factor = self.flux_conversion_factor.GetValue()
        if flux_conversion_factor.isspace() or flux_conversion_factor == "":
            raise settings.ConfigError("Units conversion factor not specified. "
                                       "Use a value of 1.0 if you do not "
                                       "require any conversion.")
        
        downsizing_factor = self.downsizing_factor.GetValue()
        
        return {
                'filename_format':filename_format,
                'file_extension':file_extension,
                'pixel_size':self.pixel_size_box.GetValue(),
                'flux_conversion_factor':flux_conversion_factor,
                'downsizing_factor': downsizing_factor
                }
    
    
    def set_configs(self, configs):
        self.filename_format_box.SetValue(configs['filename_format'])
        self.file_extension_box.SetValue(configs['file_extension'])
        self.pixel_size_box.SetValue(configs['pixel_size'])
        self.flux_conversion_factor.SetValue("%0.3e"%configs['flux_conversion_factor'])
        self.downsizing_factor.SetValue(configs['downsizing_factor'])



class MaskingConfig(wx.Panel):
    def __init__(self, parent):
        super(MaskingConfig, self).__init__(parent)
        
        vsizer = wx.BoxSizer(wx.VERTICAL)
        
        sizer = wx.FlexGridSizer(2, 5, 10, 0)
        
        self.low_thresh_chkbx = AutoUpdateCheckbox(self, -1, "Low pixel threshold:")
        sizer.Add(self.low_thresh_chkbx, 0, wx.ALIGN_RIGHT|wx.ALIGN_CENTRE_VERTICAL)
        self.low_thresh_box = AutoUpdateFloatspin(self, wx.ID_ANY, increment=1.0,
                                                   digits=0, min_val=0)
        h_txt = ("Any pixels that are below this threshold will be masked using"
                 " random noise during the motion estimation and will be "
                 "excluded from the flux calculation.")
        self.low_thresh_chkbx.SetToolTipString(h_txt)
        self.low_thresh_box.SetToolTipString(h_txt)
        sizer.Add(self.low_thresh_box, 0,wx.ALIGN_LEFT|wx.ALIGN_CENTRE_VERTICAL)
        wx.EVT_CHECKBOX(self, self.low_thresh_chkbx.GetId(), self.on_low_thresh)
        
        sizer.AddSpacer((20,-1))
        
        self.high_thresh_chkbx = AutoUpdateCheckbox(self, -1, "High pixel threshold:")
        sizer.Add(self.high_thresh_chkbx, 0, wx.ALIGN_RIGHT|wx.ALIGN_CENTRE_VERTICAL)
        self.high_thresh_box = AutoUpdateFloatspin(self, wx.ID_ANY, increment=1.0,
                                                   digits=0, min_val=0)
        h_txt = ("Any pixels that are above this threshold will be masked using"
                 " random noise during the motion estimation and will be "
                 "excluded from the flux calculation.")
        self.high_thresh_chkbx.SetToolTipString(h_txt)
        self.high_thresh_box.SetToolTipString(h_txt)
        sizer.Add(self.high_thresh_box, 0, wx.ALIGN_LEFT|wx.ALIGN_CENTRE_VERTICAL)
        wx.EVT_CHECKBOX(self, self.high_thresh_chkbx.GetId(), self.on_high_thresh)
        
        sizer.Add(wx.StaticText(self, -1, "Mask value mean:"), 0, 
                  wx.ALIGN_RIGHT|wx.ALIGN_CENTRE_VERTICAL)
        self.random_mean_box = AutoUpdateFloatspin(self, wx.ID_ANY, increment=1, 
                                                   digits=1, min_val=0.0)
        h_txt = ("Masked pixels (either due to thresholding or a mask image) "
                 "are replaced by Gaussian distributed white noise. This "
                 "parameter controls the mean value of this noise.")
        self.random_mean_box.SetToolTipString(h_txt)
        sizer.Add(self.random_mean_box, 0, wx.ALIGN_LEFT|wx.ALIGN_CENTRE_VERTICAL)
        
        sizer.AddSpacer((20,1))
        
        sizer.Add(wx.StaticText(self, -1, "Mask value Std. Dev.:"), 0, 
                  wx.ALIGN_RIGHT|wx.ALIGN_CENTRE_VERTICAL)
        self.random_sigma_box = AutoUpdateFloatspin(self, wx.ID_ANY, increment=1,
                                                     min_val=0.0, digits=1)
        h_txt = ("Masked pixels (either due to thresholding or a mask image) "
                 "are replaced by Gaussian distributed white noise. This "
                 "parameter controls the standard-deviation of this noise. It "
                 "can be set to 0 if masking with a single value is required.")
        self.random_sigma_box.SetToolTipString(h_txt)
        sizer.Add(self.random_sigma_box, 0, wx.ALIGN_LEFT|wx.ALIGN_CENTRE_VERTICAL)
        
        vsizer.Add(sizer, 1, wx.EXPAND|wx.ALIGN_TOP|wx.ALIGN_LEFT)
        
        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        self.mask_im_chkbx = AutoUpdateCheckbox(self, -1, "Mask image:")
        hsizer.Add(self.mask_im_chkbx, 0, wx.ALIGN_RIGHT|wx.ALIGN_CENTRE_VERTICAL)
        self.mask_im_box = AutoUpdateTextCtrl(self, -1, style=wx.TE_PROCESS_ENTER)
        h_txt = ("Regions of the image which you do not want to contribute to "
                 "the flux, or that might interfere with the motion estimation "
                 "(for example high-contrast boudaries of the volcanic edifice)"
                 " can be excluded from the calculations by creating a mask "
                 "image. This should be a greyscale image of the same size as "
                 "the UV images to be processed. Any pixels that are black "
                 "(pixel value of 0) in the mask image will be replaced with "
                 "random noise and excluded from the flux calculations. Enter "
                 "the filename of the mask image here.")
        self.mask_im_box.SetToolTipString(h_txt)
        hsizer.Add(self.mask_im_box, 1, wx.ALIGN_LEFT|wx.ALIGN_CENTRE_VERTICAL)
        self.browse_button = wx.Button(self, -1, "Browse")
        h_txt = ("Select an existing mask image to use.")
        self.browse_button.SetToolTipString(h_txt)
        hsizer.Add(self.browse_button, 0, wx.ALIGN_LEFT|wx.ALIGN_CENTRE_VERTICAL)
        
        wx.EVT_CHECKBOX(self, self.mask_im_chkbx.GetId(), self.on_mask_im)
        wx.EVT_BUTTON(self, self.browse_button.GetId(), self.on_browse)
        
        vsizer.Add(hsizer, 1, wx.EXPAND|wx.ALIGN_TOP|wx.ALIGN_LEFT)
        
        self.SetSizer(vsizer)
        vsizer.Fit(self)
    
    
    def on_browse(self, evnt):
        filename = wx.FileSelector("Select mask image")
        if filename != "":
            self.mask_im_box.SetValue(filename)
            
    
    def on_mask_im(self, evnt):
        self.browse_button.Enable(self.mask_im_chkbx.IsChecked())
        self.mask_im_box.Enable(self.mask_im_chkbx.IsChecked())
        self.update_threshold_visibility()
    
    
    def on_low_thresh(self, evnt):
        self.low_thresh_box.Enable(self.low_thresh_chkbx.IsChecked())
        self.update_threshold_visibility()
    
    
    def on_high_thresh(self, evnt):
        self.high_thresh_box.Enable(self.high_thresh_chkbx.IsChecked()) 
        self.update_threshold_visibility()
        
        
    def update_threshold_visibility(self):
        enabled = (self.mask_im_chkbx.IsChecked() or 
                   self.low_thresh_chkbx.IsChecked() or 
                   self.high_thresh_chkbx.IsChecked())
        self.random_mean_box.Enable(enabled)
        self.random_sigma_box.Enable(enabled)
    
    
    def set_configs(self, configs):
        self.low_thresh_box.SetValue(configs['motion_pix_threshold_low'])
        self.high_thresh_box.SetValue(configs['motion_pix_threshold_high'])
        self.mask_im_box.SetValue(configs['mask_image'])
        self.random_mean_box.SetValue(configs['random_mean'])
        self.random_sigma_box.SetValue(configs['random_sigma'])
        
        self.low_thresh_chkbx.SetValue(configs['motion_pix_threshold_low']!=0)
        self.low_thresh_box.Enable(configs['motion_pix_threshold_low']!=0)
                                   
        self.high_thresh_chkbx.SetValue(configs['motion_pix_threshold_high']!=-1)
        self.high_thresh_box.Enable(configs['motion_pix_threshold_high']!=-1)
        
        self.mask_im_chkbx.SetValue(configs['mask_image'] != "")
        self.mask_im_box.Enable(configs['mask_image'] != "")
        self.browse_button.Enable(configs['mask_image'] != "")
        
        self.update_threshold_visibility()
    
    
    def get_configs(self):
        configs = {
                   'random_mean': self.random_mean_box.GetValue(),
                   'random_sigma': self.random_sigma_box.GetValue()
                   }
        
        if self.mask_im_chkbx.IsChecked():
            configs['mask_image'] = self.mask_im_box.GetValue()
        else:
            configs['mask_image'] = unicode("")
        
        if self.low_thresh_chkbx.IsChecked():
            configs['motion_pix_threshold_low'] = self.low_thresh_box.GetValue()
        else:
            configs['motion_pix_threshold_low'] = -1
        
        if self.high_thresh_chkbx.IsChecked():
            configs['motion_pix_threshold_high'] = self.high_thresh_box.GetValue()
        else:
            configs['motion_pix_threshold_high'] = -1
    
        return configs



class MotionTrackingConfig(wx.Panel):
    def __init__(self, parent):
    
        super(MotionTrackingConfig, self).__init__(parent)
        
        sizer = wx.FlexGridSizer(2, 8, 10, 0)
        
        sizer.Add(wx.StaticText(self, -1, "Pyramid scale:"), 0, 
                  wx.ALIGN_RIGHT | wx.ALIGN_CENTRE_VERTICAL)
        self.pyr_scale_box = AutoUpdateFloatspin(self, wx.ID_ANY, min_val=0.01, max_val=1.0,
                                                  increment=0.1, digits=2)
        h_txt = ("Farneback algorithm parameter: the image scale (<1.0) to "
                 "build pyramids for each image; setting this to 0.5 means a "
                 "classical pyramid, where each next layer is half the size "
                 "of the previous one.")
        self.pyr_scale_box.SetToolTipString(h_txt)
        sizer.Add(self.pyr_scale_box, 0, wx.ALIGN_LEFT|wx.ALIGN_CENTRE_VERTICAL)
        
        sizer.AddSpacer((10,1))
        
        sizer.Add(wx.StaticText(self, -1, "Pyramid levels:"), 0, 
                  wx.ALIGN_RIGHT|wx.ALIGN_CENTRE_VERTICAL)
        self.levels_box = AutoUpdateSpinCtrl(self, wx.ID_ANY, min=1)
        h_txt = ("Farneback algorithm parameter: number of pyramid layers "
                 "including the initial image; setting this to 1 means that no "
                 "extra layers are created and only the original images "
                 "are used.")
        self.levels_box.SetToolTipString(h_txt)
        sizer.Add(self.levels_box, 0, wx.ALIGN_LEFT|wx.ALIGN_CENTRE_VERTICAL)
        
        sizer.AddSpacer((10,1))       
        
        sizer.Add(wx.StaticText(self, -1, "Window size:"), 0, 
                  wx.ALIGN_RIGHT|wx.ALIGN_CENTRE_VERTICAL)
        self.winsize_box = AutoUpdateSpinCtrl(self, wx.ID_ANY, min=1, max=1000)
        h_txt = ("Farneback algorithm parameter: averaging window size; larger "
                 "values increase the algorithm robustness to image noise and "
                 "give more chances for fast motion detection, but yield more "
                 "blurred motion field.")
        self.winsize_box.SetToolTipString(h_txt)
        sizer.Add(self.winsize_box, 0, wx.ALIGN_LEFT|wx.ALIGN_CENTRE_VERTICAL)
        
        
        sizer.Add(wx.StaticText(self, -1, "Iterations:"), 0, 
                  wx.ALIGN_RIGHT|wx.ALIGN_CENTRE_VERTICAL)
        self.iterations_box = AutoUpdateSpinCtrl(self, wx.ID_ANY, min=1, max=1000)
        h_txt = ("Farneback algorithm parameter: number of iterations the "
                 "algorithm performs at each pyramid level.")
        self.iterations_box.SetToolTipString(h_txt)
        sizer.Add(self.iterations_box, 0, wx.ALIGN_LEFT|wx.ALIGN_CENTRE_VERTICAL)
        
        sizer.AddSpacer((10,1))
        
        sizer.Add(wx.StaticText(self, -1, "Polynomial size:"), 0, 
                  wx.ALIGN_RIGHT|wx.ALIGN_CENTRE_VERTICAL)
        self.poly_n_box = AutoUpdateSpinCtrl(self, wx.ID_ANY, min=3, max=100)
        h_txt = ("Farneback algorithm parameter: size of the pixel neighborhood"
                 " used to find polynomial expansion in each pixel; larger "
                 "values mean that the image will be approximated with smoother"
                 " surfaces, yielding more robust algorithm and more blurred "
                 "motion field, typically values of 5 or 7 are used.")
        self.poly_n_box.SetToolTipString(h_txt)
        sizer.Add(self.poly_n_box, 0, wx.ALIGN_LEFT|wx.ALIGN_CENTRE_VERTICAL)
        
        sizer.AddSpacer((10,1))
        
        sizer.Add(wx.StaticText(self, -1, "Gaussian smoothing:"), 0, 
                  wx.ALIGN_RIGHT|wx.ALIGN_CENTRE_VERTICAL)
        self.poly_sigma_box = AutoUpdateFloatspin(self, wx.ID_ANY, min_val=0.0,
                                                  increment=0.1, digits=3)
        h_txt = ("Farneback algorithm parameter: standard deviation of the "
                 "Gaussian that is used to smooth derivatives used as a basis "
                 "for the polynomial expansion; for polynomial sizes of 5 and "
                 "7, reasonable choices of this parameter would be 1.1 and 1.5 "
                 "respectively.")
        self.poly_sigma_box.SetToolTipString(h_txt)
        sizer.Add(self.poly_sigma_box, 0, wx.ALIGN_LEFT|wx.ALIGN_CENTRE_VERTICAL)
    
        self.SetSizer(sizer)
        sizer.Fit(self)
    
    
    def get_configs(self):
        return {
                'farneback_pyr_scale': self.pyr_scale_box.GetValue(),
                'farneback_levels': self.levels_box.GetValue(),
                'farneback_winsize': self.winsize_box.GetValue(),
                'farneback_iterations': self.iterations_box.GetValue(),
                'farneback_poly_n': self.poly_n_box.GetValue(),
                'farneback_poly_sigma': self.poly_sigma_box.GetValue(),
                }
    
    
    def set_configs(self, configs):
        self.pyr_scale_box.SetValue(configs['farneback_pyr_scale'])
        self.levels_box.SetValue(configs['farneback_levels'])
        self.winsize_box.SetValue(configs['farneback_winsize'])
        self.iterations_box.SetValue(configs['farneback_iterations'])
        self.poly_n_box.SetValue(configs['farneback_poly_n'])
        self.poly_sigma_box.SetValue(configs['farneback_poly_sigma'])
 
class IntegrationLineConfig(wx.Panel):
    def __init__(self, parent, num):
        super(IntegrationLineConfig, self).__init__(parent)
        self._num = num
        
        vsizer = wx.BoxSizer(wx.VERTICAL)
      
        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        
        hsizer.Add(wx.StaticText(self, -1, "Name:"),0,
                   wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT)
        self.name_box = wx.TextCtrl(self, -1, style=wx.TE_PROCESS_ENTER)
        self.name_box.SetValue("Integration Line %d"%num)
        
        h_txt =  ("Descriptive name for this integration line. This will appear"
                  " as a column heading in plumetrack results files")
        self.name_box.SetToolTipString(h_txt)
        hsizer.Add(self.name_box,1, wx.ALIGN_CENTER_VERTICAL)
        hsizer.AddSpacer(10)
        hsizer.Add(wx.StaticText(self, -1, "Points:"),0,
                   wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT)
        self.integration_line_box = AutoUpdateTextCtrl(self, -1, style=wx.TE_PROCESS_ENTER)
        h_txt =  ("List of [x, y] points (e.g. [[x1, y1], [x2, y2],...]) "
                  "defining the integration line for the flux calculation. x "
                  "and y are in pixel coordinates - the origin is in the top "
                  "left of an image.")
        self.integration_line_box.SetToolTipString(h_txt)
        hsizer.Add(self.integration_line_box,1, wx.ALIGN_CENTER_VERTICAL)
        self.draw_button = wx.Button(self, -1, "Draw")
        h_txt = ("Opens a dialog in which the integration line can be chosen by"
                 " drawing it onto an image.")
        self.draw_button.SetToolTipString(h_txt)
        hsizer.Add(self.draw_button,0,wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_LEFT)
        wx.EVT_BUTTON(self, self.draw_button.GetId(), self.on_draw)
         
        vsizer.Add(hsizer, 1, wx.ALIGN_LEFT|wx.ALIGN_TOP|wx.EXPAND)
        vsizer.AddSpacer(10)
         
        self.direction_chkbx = AutoUpdateCheckbox(self, -1, "Reverse integration direction")
        h_txt = ("Defines which way is positive across the integration line. "
                 "This is easier to set in the 'Draw' dialog (click button "
                 "above).")
        self.direction_chkbx.SetToolTipString(h_txt)
        vsizer.Add(self.direction_chkbx, 0 , wx.ALIGN_LEFT)
        
        self.SetSizer(vsizer)
        vsizer.Fit(self)
    
            
    def on_draw(self, evnt):
        image_file = wx.FileSelector("Choose image file to draw integration line on")
        
        if image_file == "":
            return
        
        try:
            im = cv2.imread(image_file, cv2.IMREAD_UNCHANGED) 
        except Exception, ex:
            wx.MessageBox("Failed to open '%s'. Error was: %s"%(image_file, ex.args[0]))
        
        if self.direction_chkbx.IsChecked():
            direction = -1
        else:
            direction = 1
        
        try:
            pts = numpy.array(json.loads(self.integration_line_box.GetValue()))
        except:
            pts = None
        
        int_line_dialog = IntegrationLineSelectDialog(self.Parent, im, pts, direction)
        
        if int_line_dialog.ShowModal() == wx.OK:
            int_line = int_line_dialog.get_integration_line()
            if int_line is None:
                self.integration_line_box.SetValue("")
            else:
                self.integration_line_box.SetValue(json.dumps(int_line))
                
            direction = int_line_dialog.get_integration_direction()
            if direction == -1:
                self.direction_chkbx.SetValue(True)
            else:
                self.direction_chkbx.SetValue(False)
    
    def set_configs(self, configs):
        if configs['integration_direction'] == -1:
            self.direction_chkbx.SetValue(True)
        elif configs['integration_direction'] == 1:
            self.direction_chkbx.SetValue(False)
        else:
            raise ValueError("Unexpected value (%d) for integration_direction. "
                             "Expected -1 or 1."%(configs['integration_direction']))
            
        self.integration_line_box.SetValue(str(configs['integration_points']))
        self.name_box.SetValue(configs['name'])
    
    
    def get_configs(self):
        if self.direction_chkbx.IsChecked():
            direction = -1
        else:
            direction = 1
        
        name = self.name_box.GetValue()
        
        int_line_str = self.integration_line_box.GetValue()
        if int_line_str == "" or int_line_str.isspace():
           raise settings.ConfigError("No points specified for integration "
                                      "line %d."%self._num)
        
        try:
            integration_points = json.loads(int_line_str)
        except ValueError:
            raise settings.ConfigError("Invalid format for integration line %d "
                                       "points. Expecting [[x1, y1], "
                                       "[x2, y2],...]"%self._num)
        
        return {
                'name' : name,
                'integration_points': integration_points,
                'integration_direction': direction
                }


class FluxCalculationConfig(wx.Panel):
    def __init__(self, parent):
        super(FluxCalculationConfig, self).__init__(parent)
        
        self.__integration_methods = [u'2d', u'1d']
        self._int_lines = []
        self._int_line_szrs = []
        
        self.vsizer = wx.BoxSizer(wx.VERTICAL)
        
        gsizer = wx.FlexGridSizer(1,5,10,0)
        
        gsizer.Add(wx.StaticText(self, -1, "Integration method:"),0,
                         wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT)
        self.integration_method_choice = wx.Choice(self, -1, choices=self.__integration_methods)
        h_txt = ("Method used to calculate the flux. '1d' is marginally faster,"
                 " but '2d' is more robust, especially for images with a large "
                 "time gaps between them.")
        self.integration_method_choice.SetToolTipString(h_txt)
        gsizer.Add(self.integration_method_choice,1, wx.ALIGN_CENTER_VERTICAL)
        
        gsizer.AddSpacer((10, 1))
        
        self.low_thresh_chkbx = AutoUpdateCheckbox(self, -1, "Low pixel threshold:")
        gsizer.Add(self.low_thresh_chkbx, 0, wx.ALIGN_RIGHT|wx.ALIGN_CENTRE_VERTICAL)
        self.low_thresh_box = AutoUpdateFloatspin(self, wx.ID_ANY, increment=1.0,
                                                   digits=0, min_val=0)
        self.low_thresh_box.Enable(self.low_thresh_chkbx.IsChecked())
        h_txt = ("Any pixels that are below this threshold will be excluded "
                 "from the flux calculation. However, this does not affect their"
                 "visibility to the motion estimation algorithm (unlike the "
                 "threshold in the Image Masking section above).")
        self.low_thresh_chkbx.SetToolTipString(h_txt)
        self.low_thresh_box.SetToolTipString(h_txt)
        gsizer.Add(self.low_thresh_box, 0,wx.ALIGN_LEFT|wx.ALIGN_CENTRE_VERTICAL)
        wx.EVT_CHECKBOX(self, self.low_thresh_chkbx.GetId(), self.on_low_thresh)
        
        self.vsizer.Add(gsizer, 1, wx.ALIGN_LEFT|wx.ALIGN_TOP)
        self.vsizer.AddSpacer(10)
        
        self.button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        self.add_button = wx.Button(self, -1, "Add")
        h_txt = ("Add an extra integration line.")
        self.add_button.SetToolTipString(h_txt)
        
        self.remove_button = wx.Button(self, -1, "Remove")
        h_txt = ("Remove the last integration line.")
        self.remove_button.SetToolTipString(h_txt)
        
        self.button_sizer.Add(self.add_button, 0, wx.EXPAND|wx.ALIGN_RIGHT)
        self.button_sizer.Add(self.remove_button, 0, wx.EXPAND|wx.ALIGN_RIGHT)
        self.button_sizer.AddSpacer(5)
        wx.EVT_BUTTON(self, self.add_button.GetId(), self.on_add_int_line)
        wx.EVT_BUTTON(self, self.remove_button.GetId(), self.on_remove_int_line)
        self.remove_button.Enable(False)
        
        self.vsizer.Add(self.button_sizer, 1 , wx.ALIGN_RIGHT)
        
        self.SetSizer(self.vsizer)
        self.vsizer.Fit(self)
        
        self.on_add_int_line(None)
        
        
    def on_low_thresh(self, evnt):
        self.low_thresh_box.Enable(self.low_thresh_chkbx.IsChecked())
    
    
    def on_add_int_line(self, evnt):
        num_of_int_lines = len(self._int_lines) + 1
        
        self._int_lines.append(IntegrationLineConfig(self, num_of_int_lines))
        
        #create the configuration panels and add them to the top panel using a 
        #box sizer to control the layout
        static_szr = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, 'Integration Line %d'%num_of_int_lines), wx.VERTICAL)
        static_szr.Add(self._int_lines[-1], 0 , wx.EXPAND|wx.ALIGN_TOP|wx.ALIGN_RIGHT)
        idx = self.vsizer.GetItemIndex(self.button_sizer)
        self.vsizer.Insert(idx, static_szr, 0, wx.EXPAND|wx.ALL, border=5)
        self._int_line_szrs.append(static_szr)
        
        if len(self._int_lines) > 1:
            self.remove_button.Enable(True)
        
        static_szr.Layout()
        self.vsizer.Layout()
        self.Parent.SendSizeEvent()
        
        
    def on_remove_int_line(self, evnt):
        self.vsizer.Remove(self._int_line_szrs[-1])
        self._int_line_szrs.pop()
        line = self._int_lines.pop()
        line.Destroy()
        if len(self._int_lines) == 1:
            self.remove_button.Enable(False)
        
        self.button_sizer.Layout()
        self.vsizer.Layout()
        self.Parent.SendSizeEvent()
    
    
    def get_configs(self):

        if self.low_thresh_chkbx.IsChecked():
            low_thresh = self.low_thresh_box.GetValue()
        else:
            low_thresh = -1
                 
        int_method = self.__integration_methods[self.integration_method_choice.GetSelection()]
        
        integration_lines = [l.get_configs() for l in self._int_lines]
        
        return {
                'integration_pix_threshold_low': low_thresh,
                'integration_method': int_method,
                'integration_lines': integration_lines
                }
    
    
    def set_configs(self, configs):
        #set the flux calculation configs
        int_method_idx = self.__integration_methods.index(configs['integration_method'])
        self.integration_method_choice.SetSelection(int_method_idx)
        
        if configs['integration_pix_threshold_low'] >= 0:
            self.low_thresh_chkbx.SetValue(True)
            self.low_thresh_box.SetValue(configs['integration_pix_threshold_low'])
        else:
            self.low_thresh_chkbx.SetValue(False)
        
        #now set the configs for all the integration lines that are defined
        
        #first remove any extra lines
        while len(self._int_lines) > 1:
            self.on_remove_int_line(None)
        
        #now set the configs for the first one
        self._int_lines[0].set_configs(configs['integration_lines'][0])
        
        #and now for the rest (if there are any more)
        if len(configs['integration_lines']) > 1:
            for i in range(1, len(configs['integration_lines'][1:])+1):
                self.on_add_int_line(None)
                self._int_lines[i].set_configs(configs['integration_lines'][i])
 
 
 
class MainFrame(wx.Frame):
    """
    Main frame of the configuration utility GUI.
    """   
    def __init__(self):
        wx.Frame.__init__(self, None, wx.ID_ANY, " Configuration Utility - "+plumetrack.PROG_SHORT_NAME)
        self.config_panels = []
        self.config_test_frame = None
    
    
    def launch(self, prev_cfg_file):
        """
        Create all the GUI elements and show the main window. Note that this 
        needs to be separate from the __init__ method, since we need to set the top
        level window for wx before calling launch().
        """ 
        top_sizer = wx.BoxSizer(wx.VERTICAL)
        top_panel = wx.ScrolledWindow(self, wx.ID_ANY)
        vsizer = wx.BoxSizer(wx.VERTICAL)
        top_panel.SetScrollRate(8,8)
        top_sizer.Add(top_panel, 1, wx.EXPAND| wx.ALIGN_TOP)
        
        if prev_cfg_file is None:
            prev_cfg_file = os.path.join(plumetrack.get_plumetrack_rw_dir(),
                                         "plumetrack.cfg")
        
        #create the configuration panels and add them to the top panel using a 
        #box sizer to control the layout
        config_select_static_szr = wx.StaticBoxSizer(wx.StaticBox(top_panel, wx.ID_ANY, 'Load Existing Configuration'), wx.VERTICAL)
        self.config_file_chooser = ConfigFileSelect(top_panel, self, prev_cfg_file)
        config_select_static_szr.Add(self.config_file_chooser, 0 , wx.EXPAND|wx.ALIGN_TOP|wx.ALIGN_RIGHT)
        vsizer.Add(config_select_static_szr, 0, wx.EXPAND|wx.ALL, border=5)
        config_select_static_szr.Layout()
        
        vsizer.AddSpacer(10)
        vsizer.AddStretchSpacer()
        
        input_files_static_szr = wx.StaticBoxSizer(wx.StaticBox(top_panel, wx.ID_ANY, 'Input Files'), wx.VERTICAL)
        self.input_files_config = InputFilesConfig(top_panel)
        input_files_static_szr.Add(self.input_files_config, 0 , wx.EXPAND|wx.ALIGN_TOP|wx.ALIGN_RIGHT)
        vsizer.Add(input_files_static_szr, 0, wx.EXPAND|wx.ALL, border=5)
        self.config_panels.append(self.input_files_config)
        input_files_static_szr.Layout()
        
        vsizer.AddSpacer(10)
        vsizer.AddStretchSpacer()
        
        masking_static_szr = wx.StaticBoxSizer(wx.StaticBox(top_panel, wx.ID_ANY, 'Image Masking'), wx.VERTICAL)
        self.masking_config = MaskingConfig(top_panel)
        masking_static_szr.Add(self.masking_config, 0 , wx.EXPAND|wx.ALIGN_TOP|wx.ALIGN_RIGHT)
        vsizer.Add(masking_static_szr, 0, wx.EXPAND|wx.ALL, border=5)
        self.config_panels.append(self.masking_config)
        masking_static_szr.Layout()
        
        vsizer.AddSpacer(10)
        vsizer.AddStretchSpacer()
        
        motion_static_szr = wx.StaticBoxSizer(wx.StaticBox(top_panel, wx.ID_ANY, 'Motion Estimation'), wx.VERTICAL)
        self.motion_config = MotionTrackingConfig(top_panel)
        motion_static_szr.Add(self.motion_config, 0 , wx.EXPAND|wx.ALIGN_TOP|wx.ALIGN_RIGHT)
        vsizer.Add(motion_static_szr, 0, wx.EXPAND|wx.ALL, border=5)
        self.config_panels.append(self.motion_config)
        motion_static_szr.Layout()
        
        vsizer.AddSpacer(10)
        vsizer.AddStretchSpacer()
        
        integration_static_szr = wx.StaticBoxSizer(wx.StaticBox(top_panel, wx.ID_ANY, 'Flux Calculation'), wx.VERTICAL)
        self.integration_config = FluxCalculationConfig(top_panel)
        integration_static_szr.Add(self.integration_config, 0 , wx.EXPAND|wx.ALIGN_TOP|wx.ALIGN_RIGHT)
        vsizer.Add(integration_static_szr, 0, wx.EXPAND|wx.ALL, border=5)
        self.config_panels.append(self.integration_config)
        integration_static_szr.Layout()
        
        vsizer.AddSpacer(10)
        
        #create the save and cancel button
        buttons_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        self.test_button = wx.Button(self, wx.ID_ANY, "Test")
        buttons_sizer.Add(self.test_button, 0, wx.ALIGN_BOTTOM|wx.ALIGN_RIGHT|wx.TOP|wx.BOTTOM, border=10)
        wx.EVT_BUTTON(self, self.test_button.GetId(), self.on_test)
        
        self.cancel_button = wx.Button(self, wx.ID_CANCEL, "Cancel")
        buttons_sizer.Add(self.cancel_button, 0, wx.ALIGN_BOTTOM|wx.ALIGN_RIGHT|wx.TOP|wx.BOTTOM, border=10)
        wx.EVT_BUTTON(self, self.cancel_button.GetId(), self.on_cancel)
        
        self.save_button = wx.Button(self, wx.ID_SAVEAS, "Save As")
        buttons_sizer.Add(self.save_button, 0, wx.ALIGN_BOTTOM|wx.ALIGN_RIGHT|wx.TOP|wx.BOTTOM|wx.RIGHT, border=10)
        wx.EVT_BUTTON(self, self.save_button.GetId(), self.on_save)
        
        top_sizer.Add(buttons_sizer, 0, wx.ALIGN_BOTTOM|wx.ALIGN_RIGHT)
        
        #set the configs to those in the default config file (if we can - otherwise
        #they are just left blank)
        try:
            self.set_configs(settings.load_config_file(prev_cfg_file))
        except settings.ConfigError:
            #if this configuration is unloadable, then just give up
            pass
            
        #do the layout       
        top_panel.SetSizer(vsizer)
        top_panel.SetAutoLayout(True)
        vsizer.Fit(self)
        
        self.SetSizer(top_sizer)
        self.SetAutoLayout(True)
        top_sizer.Fit(top_panel)
        
        wx.EVT_CLOSE(self, self.on_close)
            
        self.Show()


    def get_configs(self):
        configs = {}
        for p in self.config_panels:
            configs.update(p.get_configs())
        
        return configs
    
    
    def set_configs(self, configs):
        for p in self.config_panels:
            p.set_configs(configs)    
    
    
    def on_config_change(self):
        
        if self.config_test_frame is not None:
            try:
                #read the configs from the various input panels        
                configs = self.get_configs() 
                
                #check that the configuration is valid
                settings.validate_config(configs, None)
                
            except settings.ConfigError, ex:
                wx.CallAfter(wx.MessageBox,str(ex.args[0]), plumetrack.PROG_SHORT_NAME, wx.ICON_ERROR)
                return
            
            self.config_test_frame.set_config(configs)
    
    
    def on_test(self, evnt):
        """
        Event handler for Test button events. Opens a directory choice dialog
        to choose an image directory to test the configs on and then launches 
        a config_test_frame. Note that if a config test frame already exists
        then clicking test simply updates the configuration that the config test
        frame is displaying
        """
        try:
            #read the configs from the various input panels        
            configs = self.get_configs() 
            
            #check that the configuration is valid
            settings.validate_config(configs, None)
            
        except settings.ConfigError, ex:
            wx.MessageBox(str(ex.args[0]), plumetrack.PROG_SHORT_NAME, wx.ICON_ERROR)
            return
        
        try:
            prev_dir = persist.PersistentStorage().get_value("config_test_frame_image_dir")
        except KeyError:
            prev_dir = ""
        
        im_dir = wx.DirSelector("Select directory containing images to test the "
                                "configuration on", defaultPath=prev_dir)
        if im_dir == "":
            return
        
        persist.PersistentStorage().set_value("config_test_frame_image_dir", im_dir)
        self.test_button.Enable(False)
        self.config_test_frame = config_test_frame.ConfigTestFrame(self, im_dir, configs)
    
    
    def _on_config_test_frame_close(self):
        #called from inside the on_close handler of the config test frame
        self.config_test_frame = None
        self.test_button.Enable(True)
        wx.Yield()
    
    
    def on_cancel(self, evnt):
        """
        Event handler for cancel button events. Exits the program.
        """
        self.on_close(None)
        
    
    def on_close(self, evnt):
        """
        Event handler for close events - exits the program.
        """
        #this is a hack for now, since I can't figure out what component of the 
        #ConfigTestFrame is not being destroyed properly and is preventing the
        #main application from closing.
        wx.GetApp().ExitMainLoop()
    
    
    def on_save(self, evnt):
        """
        Event handler for Save button events. Opens a file selection dialog, 
        reads the configs from the various panels and saves them to the selected
        file.
        """
         
        try:
            #read the configs from the various input panels        
            configs = self.get_configs() 
            
            #check that the configuration is valid
            settings.validate_config(configs, None)
            
        except settings.ConfigError, ex:
            wx.MessageBox(str(ex.args[0]), plumetrack.PROG_SHORT_NAME, wx.ICON_ERROR)
            return
                
        filename = wx.FileSelector("Select file to save configuration to", flags=wx.FD_SAVE|wx.FD_OVERWRITE_PROMPT)
        
        if filename.isspace() or filename == "":
            return
                
        with open(filename, 'w') as ofp:
            json.dump(configs, ofp, indent=2)
        
        persist.PersistentStorage().set_value("config_script_prev_file", filename)
        
        

class IntegrationLineSelectDialog(wx.Dialog):
    
    def __init__(self, parent, image_array, pts, direction):
        super(IntegrationLineSelectDialog, self).__init__(parent, wx.ID_ANY, plumetrack.PROG_SHORT_NAME+" Integration Line Selection Tool",
                                                         style=wx.RESIZE_BORDER|wx.DEFAULT_DIALOG_STYLE)
        
        if pts is None:
            self.line_xpts = numpy.array([], dtype='float')
            self.line_ypts = numpy.array([], dtype='float')
        else:
            self.line_xpts = numpy.array(pts[:,0], dtype='float')
            self.line_ypts = numpy.array(pts[:,1], dtype='float')
            
        self.int_direction = direction
        
        top_sizer = wx.BoxSizer(wx.VERTICAL)
        
        fig_panel = wx.ScrolledWindow(self)
        fig_panel.SetScrollRate(2, 2)
        fig_sizer = wx.BoxSizer(wx.VERTICAL)
        
        self.mpl_figure = Figure(figsize=(4, 2))
        
        self.canvas = FigureCanvasWxAgg(fig_panel, -1, self.mpl_figure)
        fig_sizer.Add(self.canvas, 1, wx.ALIGN_LEFT | wx.ALIGN_TOP | wx.EXPAND)
        
        #plot the image data into the figure
        self.mpl_axes = self.mpl_figure.add_subplot(111)
        self.mpl_axes.imshow(image_array, cmap=matplotlib.cm.gray)
        self.mpl_axes.set_xticks([])
        self.mpl_axes.set_yticks([])
        self.canvas.draw()
        
        #create blank plots of the integration line
        self.line_plt, = self.mpl_axes.plot([],[],'b-', linewidth=2)
        self.points_plt, = self.mpl_axes.plot([],[],'r.',markersize=10)
        self.int_direction_lines = []
        
        self.redraw_integration_lines()
        
        top_sizer.Add(fig_panel, 1, wx.ALIGN_TOP|wx.EXPAND)
        
        #add the buttons to the dialog       
        buttons_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        self.clear_button = wx.Button(self, wx.ID_ANY, 'Clear')
        buttons_sizer.Add(self.clear_button, 0, wx.ALIGN_BOTTOM|wx.ALIGN_LEFT)
        wx.EVT_BUTTON(self, self.clear_button.GetId(), self.on_clear)
        
        self.direction_chkbx = wx.CheckBox(self, -1, "Reverse integration direction")
        buttons_sizer.Add(self.direction_chkbx, 0,wx.ALIGN_BOTTOM|wx.ALIGN_LEFT)
        wx.EVT_CHECKBOX(self, self.direction_chkbx.GetId(), self.on_reverse)
        
        if self.int_direction == -1:
            self.direction_chkbx.SetValue(True)
        else:
            self.direction_chkbx.SetValue(False)
        
        buttons_sizer.AddStretchSpacer()
        self.help_button = wx.Button(self, wx.ID_HELP, "Help")
        self.cancel_button = wx.Button(self, wx.ID_CANCEL, "Cancel")
        self.ok_button = wx.Button(self, wx.ID_OK, "Ok")
        buttons_sizer.Add(self.help_button, 0, wx.ALIGN_BOTTOM|wx.ALIGN_RIGHT)
        buttons_sizer.Add(self.cancel_button,0,wx.ALIGN_BOTTOM|wx.ALIGN_RIGHT)
        buttons_sizer.Add(self.ok_button,0,wx.ALIGN_BOTTOM|wx.ALIGN_RIGHT)
        wx.EVT_BUTTON(self, self.help_button.GetId(), self.on_help)
        wx.EVT_BUTTON(self, self.cancel_button.GetId(), self.on_cancel)
        wx.EVT_BUTTON(self, self.ok_button.GetId(), self.on_ok)
        top_sizer.Add(buttons_sizer, 0, wx.ALIGN_BOTTOM|wx.ALIGN_RIGHT|wx.EXPAND)
        
        
        #set up the event handling for the line drawing
        self.canvas.mpl_connect('button_press_event', self.on_click)
        
        
        fig_panel.SetSizer(fig_sizer)
        fig_sizer.Fit(fig_panel)
        self.SetSizer(top_sizer)
        top_sizer.Fit(self)
        self.SetSize(self.Parent.GetSize())
        
    
    def redraw_integration_lines(self):
        
        self.points_plt.set_data(self.line_xpts, self.line_ypts)
        self.line_plt.set_data(self.line_xpts, self.line_ypts)
        
        #remove any old lines
        while len(self.int_direction_lines) > 0:
            l = self.int_direction_lines.pop()
            l.remove()
        
        if len(self.line_xpts) > 1:        
            #now draw the new ones
            start_pts_x = 0.5 * (self.line_xpts[:-1] + self.line_xpts[1:])
            start_pts_y = 0.5 * (self.line_ypts[:-1] + self.line_ypts[1:])
            
            int_line = flux.IntegrationLine(self.line_xpts, self.line_ypts, self.int_direction)
            
            normals = int_line.get_poly_approx()[2]
            
            end_pts_x = start_pts_x + (20*normals[:,0])
            end_pts_y = start_pts_y + (20* normals[:,1])
            
            for i in range(len(end_pts_x)):
                self.int_direction_lines.append(self.mpl_axes.plot([start_pts_x[i], end_pts_x[i]],[start_pts_y[i], end_pts_y[i]],'b-')[0])
        
        self.canvas.draw()
        
        
    def on_reverse(self, evnt):
        self.int_direction *= -1
        self.redraw_integration_lines()
    
    
    def on_click(self, evnt):
        
        if evnt.inaxes != self.mpl_axes:
            return
        
        if evnt.button == 1:

            self.line_xpts = numpy.append(self.line_xpts, round(evnt.xdata,0))
            self.line_ypts = numpy.append(self.line_ypts, round(evnt.ydata,0))
            
        if evnt.button == 3:
            d = numpy.sqrt((self.line_xpts - evnt.xdata)**2 + (self.line_ypts - evnt.ydata)**2)
            
            if d.min() < 10.0:
                idx = d.argmin()
                mask = numpy.ones_like(self.line_xpts, dtype='bool')
                mask[idx] = False
                self.line_xpts = self.line_xpts[mask]
                self.line_ypts = self.line_ypts[mask]
                
                self.points_plt.set_data(self.line_xpts,self.line_ypts)
                self.line_plt.set_data(self.line_xpts,self.line_ypts)
            
        self.redraw_integration_lines()
             
    
    def on_help(self, evnt):
        wx.MessageBox("Left click on the image to add points to the integration"
                      " line. Right clicking on points will remove them. The "
                      "tick marks on the integration line should point in the "
                      "positive flux direction, select \"Reverse integration "
                      "direction\" if they do not.", 
                      "plumetrack Integration line help")
    
    
    def on_cancel(self,evnt):
        self.EndModal(wx.CANCEL)
    
    
    def on_ok(self, evnt):
        self.EndModal(wx.OK)
    
    
    def on_clear(self, evnt):
        self.line_xpts = numpy.array([], dtype='float')
        self.line_ypts = numpy.array([], dtype='float')
        self.redraw_integration_lines()
    
    
    def get_integration_line(self):
        if len(self.line_xpts) > 0:
            return zip(self.line_xpts, self.line_ypts)
        else:
            return None
    
    
    def get_integration_direction(self):
        
        return self.int_direction



html_help_str = """
<p>The filenames used for the image files must encode the capture time of the image. The format used to express the capture time is flexible and can be specified using the directives in the table below.</p>
<p>A few example filenames and their corresponding format strings:</p>
<p>2013_08_25_234632.png  => %Y_%m_%d_%H%M%S.png</p>
<p>24Jan13_164700_235.png => %d%b%y_%H%M%S_%f.png</p>
<p></p>
<p>A complete list of available format specifiers:</p>
<table border="1" class="docutils">
<colgroup>
<col width="22%" />
<col width="64%" />
</colgroup>
<thead valign="bottom">
<tr><th class="head">Directive</th>
<th class="head">Meaning</th>
</tr>
</thead>
<tbody valign="top">
<tr><td><tt class="docutils literal"><span class="pre">%a</span></tt></td>
<td>Locale&#8217;s abbreviated weekday
name.</td>
</tr>
<tr><td><tt class="docutils literal"><span class="pre">%A</span></tt></td>
<td>Locale&#8217;s full weekday name.</td>
</tr>
<tr><td><tt class="docutils literal"><span class="pre">%b</span></tt></td>
<td>Locale&#8217;s abbreviated month
name.</td>
</tr>
<tr><td><tt class="docutils literal"><span class="pre">%B</span></tt></td>
<td>Locale&#8217;s full month name.</td>
</tr>
<tr><td><tt class="docutils literal"><span class="pre">%c</span></tt></td>
<td>Locale&#8217;s appropriate date and
time representation.</td>
</tr>
<tr><td><tt class="docutils literal"><span class="pre">%d</span></tt></td>
<td>Day of the month as a decimal
number [01,31].</td>
</tr>
<tr><td><tt class="docutils literal"><span class="pre">%f</span></tt></td>
<td>Microsecond as a decimal
number [0,999999], zero-padded
on the left</td>
</tr>
<tr><td><tt class="docutils literal"><span class="pre">%H</span></tt></td>
<td>Hour (24-hour clock) as a
decimal number [00,23].</td>
</tr>
<tr><td><tt class="docutils literal"><span class="pre">%I</span></tt></td>
<td>Hour (12-hour clock) as a
decimal number [01,12].</td>
</tr>
<tr><td><tt class="docutils literal"><span class="pre">%j</span></tt></td>
<td>Day of the year as a decimal
number [001,366].</td>
</tr>
<tr><td><tt class="docutils literal"><span class="pre">%m</span></tt></td>
<td>Month as a decimal number
[01,12].</td>
</tr>
<tr><td><tt class="docutils literal"><span class="pre">%M</span></tt></td>
<td>Minute as a decimal number
[00,59].</td>
</tr>
<tr><td><tt class="docutils literal"><span class="pre">%p</span></tt></td>
<td>Locale&#8217;s equivalent of either
AM or PM.</td>
</tr>
<tr><td><tt class="docutils literal"><span class="pre">%S</span></tt></td>
<td>Second as a decimal number
[00,61].</td>
</tr>
<tr><td><tt class="docutils literal"><span class="pre">%U</span></tt></td>
<td>Week number of the year
(Sunday as the first day of
the week) as a decimal number
[00,53].  All days in a new
year preceding the first
Sunday are considered to be in
week 0.</td>
</tr>
<tr><td><tt class="docutils literal"><span class="pre">%w</span></tt></td>
<td>Weekday as a decimal number
[0(Sunday),6].</td>
</tr>
<tr><td><tt class="docutils literal"><span class="pre">%W</span></tt></td>
<td>Week number of the year
(Monday as the first day of
the week) as a decimal number
[00,53].  All days in a new
year preceding the first
Monday are considered to be in
week 0.</td>
</tr>
<tr><td><tt class="docutils literal"><span class="pre">%x</span></tt></td>
<td>Locale&#8217;s appropriate date
representation.</td>
</tr>
<tr><td><tt class="docutils literal"><span class="pre">%X</span></tt></td>
<td>Locale&#8217;s appropriate time
representation.</td>
</tr>
<tr><td><tt class="docutils literal"><span class="pre">%y</span></tt></td>
<td>Year without century as a
decimal number [00,99].</td>
</tr>
<tr><td><tt class="docutils literal"><span class="pre">%Y</span></tt></td>
<td>Year with century as a decimal
number.</td>
</tr>
<tr><td><tt class="docutils literal"><span class="pre">%z</span></tt></td>
<td>UTC offset in the form +HHMM
or -HHMM (empty string if the
the object is naive).</td>
</tr>
<tr><td><tt class="docutils literal"><span class="pre">%Z</span></tt></td>
<td>Time zone name (empty string
if the object is naive).</td>
</tr>
<tr><td><tt class="docutils literal"><span class="pre">%%</span></tt></td>
<td>A literal <tt class="docutils literal"><span class="pre">'%'</span></tt> character.</td>
</tr>
</tbody>
</table>"""           
        