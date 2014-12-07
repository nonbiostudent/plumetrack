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
from matplotlib.pyplot import subplot2grid, figure
import wx
import os
from plumetrack import dir_iter
from plumetrack import motion, output
import cv2


class ConfigTestFrame(wx.Frame):
    def __init__(self, parent, image_dir, config):
        super(ConfigTestFrame, self).__init__(parent, -1,"Configuration test - plumetrack")
        self.image_dir = image_dir
        self.config = config
        
        splitter = wx.SplitterWindow(self, -1)
        self.motion_figure = MotionFigure(splitter, config)
        self.file_list = ImageFileList(splitter, image_dir, config, self.motion_figure)
        splitter.SplitVertically(self.file_list,self.motion_figure )
        
        wx.EVT_CLOSE(self, self.on_close)
        
        self.Show()
    
    def on_close(self, evnt):
        self.motion_figure.Destroy()
        self.file_list.Destroy()
        self.Destroy()
        self.Parent.config_test_frame = None
    
    
    def set_config(self, config):
        self.motion_figure.set_config(config) 



class MotionFigure(wx.Panel):
    def __init__(self, parent, config):
        super(MotionFigure, self).__init__(parent)
          
        self._mpl_figure = figure()
        self.canvas = FigureCanvasWxAgg(self, -1, self._mpl_figure)
        
        self.cur_im = None
        self.next_im = None
        self.cur_im_masked = None
        self.next_im_masked = None
        
        self.cur_filename = None
        self.next_filename = None
        
        self.set_config(config)
        
        #setup the subplots
        
        self.cur_im_ax = subplot2grid((4,2), (0,0))
        self.next_im_ax = subplot2grid((4,2), (0,1))
        self.motion_ax = subplot2grid((4,2), (1,0), rowspan=3, colspan=2)
        
        #turn off all the tick marks
        self.cur_im_ax.set_xticks([])
        self.cur_im_ax.set_yticks([])
        self.next_im_ax.set_xticks([])
        self.next_im_ax.set_yticks([])
        self.motion_ax.set_xticks([])
        self.motion_ax.set_yticks([])
        
        self.cur_im_plot = None
        self.next_im_plot = None
        self.masked_im_plot = None
        self.quiver_plot = None
        
        vsizer = wx.BoxSizer(wx.VERTICAL)
        vsizer.Add(self.canvas, 1, wx.EXPAND)
        self.SetSizer(vsizer)
        vsizer.Fit(self)
        
        
    def set_config(self, config):
        self.config = config
        try:
            self.motion_engine = motion.GPUMotionEngine(config)
        except AttributeError:
            self.motion_engine = motion.MotionEngine(config)
        
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
            
        
        if self.cur_im_plot is None:
            self.cur_im_plot = self.cur_im_ax.imshow(self.cur_im.copy())
        else:
            self.cur_im_plot.set_data(self.cur_im.copy())
         
        if self.next_im_plot is None:
            self.next_im_plot = self.next_im_ax.imshow(self.next_im.copy())
        else:
            self.next_im_plot.set_data(self.next_im.copy()) 
        
        
        #do the motion analysis
        flow = self.motion_engine.compute_flow(self.cur_im_masked, self.next_im_masked)
        
        x_shifts, y_shifts, extent = output.resample_velocities(self.cur_im_masked, flow, 64)
        
        if self.masked_im_plot is None:
            self.masked_im_plot = self.motion_ax.imshow(self.cur_im_masked, extent=extent)
        else:
            self.masked_im_plot.set_data(self.cur_im_masked)
            self.masked_im_plot.set_extent(extent)
        
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
        vsizer.Add(self.im_list_box, 1, wx.EXPAND|wx.ALL, border=5)
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
        
        self.im_list_box.SetItems([os.path.basename(f) for f in self.images]) 
        
        #select the first image in the directory
        self.im_list_box.SetSelection(0)
        self.on_select_image(None)
        
        
    
    def on_select_image(self, evnt):
        filename_idx = self.im_list_box.GetSelection()
        filename = self.images[filename_idx]
        
        self.plot_panel.set_images(filename, self.images[filename_idx + 1])
