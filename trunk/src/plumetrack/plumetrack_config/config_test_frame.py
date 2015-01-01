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
from matplotlib.backends.backend_wx import NavigationToolbar2Wx
from matplotlib.pyplot import subplot, figure
import wx
import math
import os
from plumetrack import dir_iter
from plumetrack import persist
from plumetrack import motion, output, main_script
import cv2


class ConfigTestFrame(wx.Frame):
    def __init__(self, parent, image_dir, config):
        super(ConfigTestFrame, self).__init__(parent, -1,"Configuration test - plumetrack")
        self.image_dir = image_dir
        self.config = config
        
        vsizer = wx.BoxSizer(wx.VERTICAL)
        
        splitter = wx.SplitterWindow(self, -1)
        self.motion_figure = MotionFigure(splitter, self, config)
        self.file_list = ImageFileList(splitter, image_dir, config, self.motion_figure)
        splitter.SplitVertically(self.file_list,self.motion_figure, sashPosition=self.file_list.GetBestSizeTuple()[0])
        
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
        self.Parent._on_config_test_frame_close()
        self.motion_figure.Destroy()
        self.file_list.Destroy()
        self.Destroy()
        
    
    
    def set_config(self, config):
        if self.file_list.set_config(config):
            return
        
        #this is a horrible hack to force the motion figure to update its stored
        #filenames on config updates
        cur_im, next_im = self.file_list.get_current_selection()
        self.motion_figure.cur_filename = cur_im
        self.motion_figure.next_filename = next_im
        
        self.motion_figure.set_config(config)
    
        
    
    
    def set_status(self, pix_value,xvel, yvel):
        self.status_bar.SetStatusText("Pixel value: %0.2f"%pix_value, 1)
        self.status_bar.SetStatusText("Velocity: %0.2f m/s     (xvel: %0.2f m/s, yvel: %0.2f m/s)"%(math.sqrt((xvel*xvel) + (yvel*yvel)), xvel, yvel), 2)
    
    
    def clear_status(self):
        self.status_bar.SetStatusText("", 1)
        self.status_bar.SetStatusText("", 2)


class NavBar(NavigationToolbar2Wx):
    toolitems = ((None, None, None, None), #divider
                 ('Home', 'Reset original view', 'home', 'home'), 
                 ('Back', 'Back to  previous view', 'back', 'back'), 
                 ('Forward', 'Forward to next view', 'forward', 'forward'), 
                 (None, None, None, None), 
                 ('Pan', 'Pan axes with left mouse, zoom with right', 'move', 'pan'), 
                 ('Zoom', 'Zoom to rectangle', 'zoom_to_rect', 'zoom'), 
                 (None, None, None, None), 
                 ('Save', 'Save the figure', 'filesave', 'save_figure'))


class MotionFigureControls(wx.Panel):
    def __init__(self, parent):
        super(MotionFigureControls, self).__init__(parent)
        
        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        
        self.show_intline_chkbx = wx.CheckBox(self, -1, "Show integration lines")
        
        hsizer.Add(self.show_intline_chkbx, 0, wx.ALIGN_TOP)
        hsizer.AddSpacer(10)
        sizer = wx.GridSizer(2,2,0,5)
        
        sizer.Add(wx.StaticText(self, -1, "Vector density"),0,wx.ALIGN_CENTRE_HORIZONTAL)
        sizer.Add(wx.StaticText(self, -1, "Vector scale"),0,wx.ALIGN_CENTRE_HORIZONTAL)
        self.density_slider = wx.Slider(self, -1, 64, 10, 100)
        sizer.Add(self.density_slider, 1, wx.EXPAND)
        
        hsizer.Add(sizer,1,wx.EXPAND)
        hsizer.AddSpacer(10)
        wx.EVT_COMMAND_SCROLL_THUMBRELEASE(self, self.density_slider.GetId(), self.on_density)
        
        self.scale_slider = wx.Slider(self, -1, 25, -50, 50)
        sizer.Add(self.scale_slider, 1, wx.EXPAND)
        wx.EVT_COMMAND_SCROLL_THUMBRELEASE(self, self.scale_slider.GetId(), self.on_scale)
        
        self.SetSizer(hsizer)
        hsizer.Fit(self)
    
    
    def on_scale(self, evnt):
        new_scale = 50 - self.scale_slider.GetValue()
        self.Parent.vector_scale = (new_scale/25.0)*1.5
        self.Parent.redraw_plot()
    
    
    def on_density(self, evnt):
        
        new_density = self.density_slider.GetValue()
        self.Parent._quiver_density = new_density
        
        #clear the zoom history - otherwise it causes problems
        self.Parent.tb._views._elements = []
        self.Parent.tb._views._pos = 0
        
        self.Parent.redraw_plot()
        


class MotionFigure(wx.Panel):
    def __init__(self, parent, main_frame, config):
        super(MotionFigure, self).__init__(parent)
          
        self._mpl_figure = figure()
        self.canvas = FigureCanvasWxAgg(self, -1, self._mpl_figure)
        self.main_frame = main_frame
        
        self._quiver_density = 64
        self.vector_scale = 1.5
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
        
        self.controls = MotionFigureControls(self)
        
        #setup the subplot
        self.motion_ax = subplot(111)
        
        #turn off all the tick marks
        self.motion_ax.set_xticks([])
        self.motion_ax.set_yticks([])
        
        #setup the callback handler for mouse move events
        self.motion_ax.figure.canvas.mpl_connect('motion_notify_event', self.on_mouse_move)
        
        self.masked_im_plot = None
        self.quiver_plot = None
        
        #create the matplotlib toolbar
        self.tb = NavBar(self.motion_ax.figure.canvas)
        
        vsizer = wx.BoxSizer(wx.VERTICAL)
        vsizer.Add(self.tb,0,wx.EXPAND)
        vsizer.Add(self.canvas, 1, wx.EXPAND)
        vsizer.Add(self.controls, 0, wx.EXPAND)
        
        self.SetSizer(vsizer)
        vsizer.Fit(self)
        
    
    def clear_plot(self):
        self.__visible = False
        if self.masked_im_plot is not None:
            self.masked_im_plot.set_visible(False)
        if self.quiver_plot is not None:
            self.quiver_plot.set_visible(False)
        self.canvas.draw() 
        
    
    def on_mouse_move(self, evnt):
        if evnt.inaxes != self.motion_ax or self.__cur_flow is None or not self.__visible:
            self.main_frame.clear_status()
        
        else:
            x, y = evnt.xdata, evnt.ydata
            x *= (self.cur_im_masked.shape[0] - 1) / self.extent[1]
            y *= (self.cur_im_masked.shape[1] - 1) / self.extent[2]
            
            x = round(x)
            y = round(y)
            try:
                xvel, yvel = (self.__cur_flow[y, x] * self.__pix_size) / self.__delta_t
            except IndexError:
                #cursor is outside range of image - possible when the zoom tools have been used
                self.main_frame.clear_status()

            self.main_frame.set_status(self.cur_im_masked[y, x], xvel, -yvel)
        
             
    def set_config(self, config):
        self.config = config
        #try:
        #    self.motion_engine = motion.GPUMotionEngine(config)
        #except AttributeError:
        self.motion_engine = motion.MotionEngine(config)
        
        self.__pix_size = self.config['pixel_size'] * self.config['downsizing_factor']
        
        #now update the plots to reflect the new config
        #clear cached images
        self.extent = None
        self.cur_im = None
        self.next_im = None
        self.cur_im_masked = None
        self.next_im_masked = None
        self.__cur_flow = None
        self.__delta_t = None
        
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
        
        self.__visible = True
        
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
        
        self.redraw_plot()
    
    
    def redraw_plot(self):
        
        x_shifts, y_shifts, self.extent = output.resample_velocities(self.cur_im_masked, self.__cur_flow, self._quiver_density)
        
        if self.masked_im_plot is None:
            self.masked_im_plot = self.motion_ax.imshow(self.cur_im_masked, extent=self.extent)
        else:
            self.masked_im_plot.remove()
            self.masked_im_plot = self.motion_ax.imshow(self.cur_im_masked, extent=self.extent)
        
        if self.quiver_plot is None:
            self.quiver_plot = self.motion_ax.quiver(x_shifts, y_shifts, width=1.6, units='dots', scale_units='xy',angles='xy',scale=self.vector_scale)
        else:
            self.quiver_plot.remove()
            self.quiver_plot = self.motion_ax.quiver(x_shifts, y_shifts, width=1.6, units='dots',scale_units='xy',angles='xy',scale=self.vector_scale)

        self.masked_im_plot.axes.set_xlim(self.extent[:2])
        self.masked_im_plot.axes.set_ylim(self.extent[2:])    

        self.masked_im_plot.set_visible(True)
        self.quiver_plot.set_visible(True)
        
        self.canvas.draw()

        



class ImageFileList(wx.Panel):
    def __init__(self, parent, image_dir,config, plot_panel):
        super(ImageFileList, self).__init__(parent)
        self.config = config
        self.file_extension = config['file_extension']
        self.filename_format = config['filename_format']
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
        
        
        try:
            prev_dir = persist.PersistentStorage().get_value("config_test_frame_image_dir")
        except KeyError:
            prev_dir = ""
        
        im_dir = wx.DirSelector("Select directory containing images to test the "
                                "configuration on", defaultPath=prev_dir)
        
        if im_dir == "":
            return
        
        self.im_dir_box.SetValue(im_dir)
            
        persist.PersistentStorage().set_value("config_test_frame_image_dir", im_dir)
        
        self.set_image_dir(im_dir, self.config)
    
    
    def set_config(self, config):
        self.config = config
        if config['file_extension'] != self.file_extension:
            self.set_image_dir(self.im_dir, self.config)
            self.file_extension = config['file_extension']
        
        if config['filename_format'] != self.filename_format:
            self.filename_format = config['filename_format']
            
            if self.on_select_image(None):
                return 1
                      
        wx.Yield()
        
    
    def set_image_dir(self, im_dir, config):
        self.images = sorted(dir_iter.find_files(im_dir, pattern='*'+config['file_extension']))
        
        self.im_list_box.SetItems([os.path.basename(f) for f in self.images[:-1]]) 
        
        #select the first image in the directory
        self.im_list_box.SetSelection(0)
        self.on_select_image(None)
        self.im_dir = im_dir
        
    
    def get_current_selection(self):
        try:
            filename_idx = self.im_list_box.GetSelection()
            filename = self.images[filename_idx]
            next_filename = self.images[filename_idx + 1]
            return filename, next_filename
        except IndexError:
            return None,None
    
           
    def on_select_image(self, evnt):
        
        filename, next_filename = self.get_current_selection()
        
        if filename is None or next_filename is None:
            self.plot_panel.clear_plot()
            return
        
        if not main_script.is_uv_image_file(filename, self.config):
            wx.Yield()
            self.plot_panel.clear_plot()
            wx.MessageBox("Filename \"%s\"does not match the filename format specified."%filename,"",wx.ICON_WARNING)
            return 1
        
        if not main_script.is_uv_image_file(next_filename, self.config):
            wx.Yield()
            self.plot_panel.clear_plot()
            wx.MessageBox("Filename \"%s\"does not match the filename format specified."%next_filename,"",wx.ICON_WARNING)
            return 1
        
        if evnt is None:
            self.plot_panel.set_config(self.config)
        
        #use CallAfter to get better response on the selection updating
        wx.CallAfter(self.plot_panel.set_images, filename, next_filename)
        
        return 0
