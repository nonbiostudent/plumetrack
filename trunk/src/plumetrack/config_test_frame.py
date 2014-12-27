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
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg
from matplotlib.pyplot import subplot, figure
import wx
import math
import os
from plumetrack import dir_iter
from plumetrack import motion, output, main_script
import cv2
import datetime

class ConfigTestFrame(wx.Frame):
    def __init__(self, parent, image_dir, config):
        super(ConfigTestFrame, self).__init__(parent, -1,"Configuration test - plumetrack")
        self.image_dir = image_dir
        self.config = config
        
        vsizer = wx.BoxSizer(wx.VERTICAL)
        
        splitter = wx.SplitterWindow(self, -1)
        self.motion_figure = MotionFigure(splitter, self, config)
        self.file_list = ImageFileList(splitter, image_dir, config, self.motion_figure)
        splitter.SplitVertically(self.file_list,self.motion_figure )
        
        vsizer.Add(splitter, 1, wx.EXPAND)
        
        wx.EVT_CLOSE(self, self.on_close)
        
        #create a status bar to show the velocity values 
        self.status_bar = wx.StatusBar(self, -1)
        vsizer.Add(self.status_bar,0,wx.ALIGN_BOTTOM)
        self.status_bar.SetFieldsCount(3)
        
        self.SetSizer(vsizer)
        vsizer.Fit(self)
        
        self.Show()
    
    def on_close(self, evnt):
        self.motion_figure.Destroy()
        self.file_list.Destroy()
        self.Destroy()
        self.Parent.config_test_frame = None
    
    
    def set_config(self, config):
        self.motion_figure.set_config(config) 
    
    
    def set_status(self, pix_value,xvel, yvel):
        
        #self.status_bar.SetStatusText("x velocity: %0.2f m/s"%xvel, 0)
        self.status_bar.SetStatusText("Pixel value: %0.2f"%pix_value, 1)
        self.status_bar.SetStatusText("Velocity: %0.2f m/s     (xvel: %0.2f m/s, yvel: %0.2f m/s)"%(math.sqrt((xvel*xvel) + (yvel*yvel)), xvel, yvel), 2)
    
    
    def clear_status(self):
        self.status_bar.SetStatusText("", 0)
        self.status_bar.SetStatusText("", 1)
        self.status_bar.SetStatusText("", 2)



class MotionFigure(wx.Panel):
    def __init__(self, parent, main_frame, config):
        super(MotionFigure, self).__init__(parent)
          
        self._mpl_figure = figure()
        self.canvas = FigureCanvasWxAgg(self, -1, self._mpl_figure)
        self.main_frame = main_frame
        
        self._quiver_density = 64
        self.extent = None
        
        self.cur_im = None
        self.next_im = None
        self.cur_im_masked = None
        self.next_im_masked = None
        self.__cur_flow = None
        self.__delta_t = None
        
        self.cur_filename = None
        self.next_filename = None
        
        self.set_config(config)
        
        #setup the subplot
        self.motion_ax = subplot(111)
        
        #turn off all the tick marks
        self.motion_ax.set_xticks([])
        self.motion_ax.set_yticks([])
        
        #setup the callback handler for mouse move events
        self.motion_ax.figure.canvas.mpl_connect('motion_notify_event', self.on_mouse_move)
        
        self.masked_im_plot = None
        self.quiver_plot = None
        
        vsizer = wx.BoxSizer(wx.VERTICAL)
        vsizer.Add(self.canvas, 1, wx.EXPAND)
        self.SetSizer(vsizer)
        vsizer.Fit(self)
        
    
    def on_mouse_move(self, evnt):
        if evnt.inaxes != self.motion_ax or self.__cur_flow is None:
            self.main_frame.clear_status()
        
        else:
            x, y = evnt.xdata, evnt.ydata
            x *= (self.cur_im_masked.shape[0] - 1) / self.extent[1]
            y *= (self.cur_im_masked.shape[1] - 1) / self.extent[2]
            
            x = round(x)
            y = round(y)
            
            xvel, yvel = (self.__cur_flow[y, x] * self.__pix_size) / self.__delta_t

            self.main_frame.set_status(self.cur_im_masked[y, x], xvel, -yvel)
        
             
    def set_config(self, config):
        self.config = config
        try:
            self.motion_engine = motion.GPUMotionEngine(config)
        except AttributeError:
            self.motion_engine = motion.MotionEngine(config)
        
        self.__pix_size = self.config['pixel_size'] * self.config['downsizing_factor']
        
        #now update the plots to reflect the new config
        if self.cur_filename is not None:
            self.set_images(self.cur_filename, self.next_filename)
    
    
    def __new_cur_im(self, cur_filename):
        self.cur_im = cv2.imread(cur_filename, cv2.IMREAD_UNCHANGED)
        self.cur_filename = cur_filename
        self.cur_im_masked = self.cur_im.copy()
        self.motion_engine.preprocess(self.cur_im_masked)
    
    
    def __new_next_im(self, next_filename):
        self.next_im = cv2.imread(next_filename, cv2.IMREAD_UNCHANGED)
        self.next_filename = next_filename
        self.next_im_masked = self.next_im.copy()
        self.motion_engine.preprocess(self.next_im_masked)
    
    
    def set_images(self, cur_filename, next_filename):
        
        if cur_filename == self.next_filename:
            self.cur_filename = cur_filename
            self.cur_im = self.next_im
            self.cur_im_masked = self.next_im_masked
            
            self.__new_next_im(next_filename)
            
        elif self.cur_filename == next_filename:
            self.next_filename = next_filename
            self.next_im = self.cur_im
            self.next_im_masked = self.cur_im_masked
            
            self.__new_cur_im(cur_filename)
        
        else:
            self.__new_next_im(next_filename)
            self.__new_cur_im(cur_filename)
            
        self.__delta_t = (main_script.date2secs(main_script.time_from_fname(next_filename, self.config)) - 
                          main_script.date2secs(main_script.time_from_fname(cur_filename, self.config)))
          
        #do the motion analysis
        self.__cur_flow = self.motion_engine.compute_flow(self.cur_im_masked, self.next_im_masked)
        
        x_shifts, y_shifts, self.extent = output.resample_velocities(self.cur_im_masked, self.__cur_flow, self._quiver_density)
        
        if self.masked_im_plot is None:
            self.masked_im_plot = self.motion_ax.imshow(self.cur_im_masked, extent=self.extent)
        else:
            self.masked_im_plot.set_data(self.cur_im_masked)
            self.masked_im_plot.set_extent(self.extent)
        
        if self.quiver_plot is None:
            self.quiver_plot = self.motion_ax.quiver(x_shifts, -y_shifts, units='xy', scale_units='xy',scale=1.5)
        else:
            self.quiver_plot.set_UVC(x_shifts, -y_shifts)
        
        self.canvas.draw()

        



class ImageFileList(wx.Panel):
    def __init__(self, parent, image_dir,config, plot_panel):
        super(ImageFileList, self).__init__(parent)
        self.config = config
        self.plot_panel = plot_panel
        vsizer = wx.BoxSizer(wx.VERTICAL)
        
        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        
        self.im_dir_box = wx.TextCtrl(self, -1, image_dir)
        self.browse_button = wx.Button(self, -1, "Browse")
        h_txt = "Select a directory containing images to test the configuration on."
        self.im_dir_box.SetToolTipString(h_txt)
        self.browse_button.SetToolTipString(h_txt)
        wx.EVT_BUTTON(self, self.browse_button.GetId(), self.on_browse)
        
        hsizer.Add(self.im_dir_box, 1, wx.EXPAND|wx.ALIGN_LEFT|wx.ALIGN_CENTRE_VERTICAL|wx.ALL, border=5)
        hsizer.Add(self.browse_button, 0, wx.ALIGN_LEFT|wx.ALIGN_CENTRE_VERTICAL)
        hsizer.AddSpacer(5)
        
        vsizer.Add(hsizer, 0 , wx.EXPAND)
        
        self.im_list_box = wx.ListBox(self, -1, choices=[])
        vsizer.Add(self.im_list_box, 1, wx.EXPAND|wx.LEFT|wx.RIGHT|wx.TOP, border=5)
        wx.EVT_LISTBOX(self, self.im_list_box.GetId(), self.on_select_image)
        
        self.set_image_dir(image_dir, config)
        
        self.SetSizer(vsizer)
        vsizer.Fit(self)
    
    
    def on_browse(self, evnt):
        im_dir = wx.DirSelector("Select directory containing images to test the configuration on")
        if im_dir != "":
            self.im_dir_box.SetValue(im_dir)
        
        self.set_image_dir(im_dir, self.config)
    
    
    def set_image_dir(self, im_dir, config):
        self.images = sorted(dir_iter.find_files(im_dir, pattern='*'+config['file_extension']))
        
        self.im_list_box.SetItems([os.path.basename(f) for f in self.images[:-1]]) 
        
        #select the first image in the directory
        self.im_list_box.SetSelection(0)
        self.on_select_image(None)
        
           
    def on_select_image(self, evnt):
        filename_idx = self.im_list_box.GetSelection()
        filename = self.images[filename_idx]
        
        #use CallAfter to get better response on the selection updating
        wx.CallAfter(self.plot_panel.set_images, filename, self.images[filename_idx + 1])
        
