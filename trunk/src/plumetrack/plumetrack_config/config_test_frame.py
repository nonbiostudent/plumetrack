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
import math
import numpy
import os

from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg
from matplotlib.backends.backend_wx import NavigationToolbar2Wx
from matplotlib.pyplot import subplot, figure, colorbar
from mpl_toolkits.axes_grid1 import make_axes_locatable

from plumetrack import dir_iter
from plumetrack import image_loader
from plumetrack import persist
from plumetrack import motion, output, main_script
from plumetrack import flux


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
        vsizer.Add(self.status_bar, 0, wx.ALIGN_BOTTOM | wx.EXPAND)
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
    

    def set_vel_status(self, x, y,pix_value,xvel, yvel):
        self.status_bar.SetStatusText("x,y = %0.2f, %0.2f"%(x,y),0)
        self.status_bar.SetStatusText("Pixel value: %0.2f"%pix_value, 1)
        self.status_bar.SetStatusText("Velocity: %0.2f m/s     (xvel: %0.2f m/s, yvel: %0.2f m/s)"%(math.sqrt((xvel*xvel) + (yvel*yvel)), xvel, yvel), 2)
    
    
    def set_err_status(self, x,y, error_val):
        self.status_bar.SetStatusText("x,y = %0.2f, %0.2f"%(x,y),0)
        self.status_bar.SetStatusText("%% Error: %0.2f"%error_val, 1)
        self.status_bar.SetStatusText("", 2)
    
    
    def clear_status(self):
        self.status_bar.SetStatusText("", 0)
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
        vsizer = wx.BoxSizer(wx.VERTICAL)
        
        self.show_error_chkbx = wx.CheckBox(self, -1, "Show error plot")
        wx.EVT_CHECKBOX(self, self.show_error_chkbx.GetId(), self.on_error_plot_chkbx)
        
        self.show_intline_chkbx = wx.CheckBox(self, -1, "Show integration lines")
        wx.EVT_CHECKBOX(self, self.show_intline_chkbx.GetId(), self.on_int_line_chkbx)
        
        vsizer.Add(self.show_error_chkbx,0, wx.ALL, border=5)
        vsizer.Add(self.show_intline_chkbx,0, wx.ALL, border=5)
        
        hsizer.Add(vsizer, 0, wx.ALIGN_TOP)
        hsizer.AddSpacer(10)
        sizer = wx.GridSizer(2,3,0,5)
        
        sizer.Add(wx.StaticText(self, -1, "Vector density"),0,wx.ALIGN_CENTRE_HORIZONTAL|wx.ALIGN_TOP)
        sizer.Add(wx.StaticText(self, -1, "Vector scale"),0,wx.ALIGN_CENTRE_HORIZONTAL|wx.ALIGN_TOP)
        self.err_sat_txt = wx.StaticText(self, -1, "Error saturation")
        self.err_sat_txt.Enable(False)
        sizer.Add(self.err_sat_txt,0,wx.ALIGN_CENTRE_HORIZONTAL|wx.ALIGN_TOP)
        
        self.density_slider = wx.Slider(self, -1, 64, 10, 100)
        h_txt = ("Change the number of motion vectors that are plotted. This "
                 "has no effect on the accuracy of the motion field calculated "
                 "- it only effects the visualisation.")
        self.density_slider.SetToolTipString(h_txt)
        sizer.Add(self.density_slider, 1, wx.EXPAND)
        
        hsizer.Add(sizer,1,wx.EXPAND)
        hsizer.AddSpacer(10)
        wx.EVT_COMMAND_SCROLL_CHANGED(self, self.density_slider.GetId(), self.on_density)
        
        self.scale_slider = wx.Slider(self, -1, 25, -50, 49)
        h_txt = ("Change the length of the plotted motion vectors.")
        self.scale_slider.SetToolTipString(h_txt)
        sizer.Add(self.scale_slider, 1, wx.EXPAND)
        wx.EVT_COMMAND_SCROLL_CHANGED(self, self.scale_slider.GetId(), self.on_scale)
        
        self.err_sat_slider = wx.Slider(self, -1, self.Parent.cb_clip_limit, 50, 600)
        self.err_sat_slider.Enable(False)
        h_txt = ("Change the value at which the error plot colour palette saturates.")
        self.err_sat_slider.SetToolTipString(h_txt)
        sizer.Add(self.err_sat_slider, 1, wx.EXPAND)
        wx.EVT_COMMAND_SCROLL_CHANGED(self, self.err_sat_slider.GetId(), self.on_err_sat)
        
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
    
    
    def on_err_sat(self, evnt):
        new_sat = self.err_sat_slider.GetValue()
        self.Parent.cb_clip_limit = new_sat
        self.Parent.redraw_plot()
    
    
    def on_int_line_chkbx(self, evnt):
        for p in self.Parent.int_line_plots:
            p.set_visible(self.show_intline_chkbx.IsChecked())
        self.Parent.canvas.draw()
        
    
    def on_error_plot_chkbx(self, evnt):
        self.err_sat_txt.Enable(self.show_error_chkbx.IsChecked())
        self.err_sat_slider.Enable(self.show_error_chkbx.IsChecked())
        self.Parent.show_error_plot(self.show_error_chkbx.IsChecked())
        
        

class MotionFigure(wx.Panel):
    def __init__(self, parent, main_frame, config):
        super(MotionFigure, self).__init__(parent)
          
        self._mpl_figure = figure()
        self.canvas = FigureCanvasWxAgg(self, -1, self._mpl_figure)
        self.main_frame = main_frame
        
        self.cb_clip_limit = 500
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
        
        self.error_plot = None
        self.errors = None
        self.show_errors = False
        
        self.set_config(config)
        
        self.controls = MotionFigureControls(self)
        
        #setup the subplots - this needs to be done in this order in order for 
        #inaxes events to be received correctly
        self.error_ax = subplot(122)
        divider = make_axes_locatable(self.error_ax)
        self.error_cb_ax = divider.append_axes("right", size="5%", pad=0.05)
        self.motion_ax = subplot(121)
        
        #turn off all the tick marks
        self.motion_ax.set_xticks([])
        self.motion_ax.set_yticks([])
        self.error_ax.set_xticks([])
        self.error_ax.set_yticks([])
        
        self.show_error_plot(False)
        
        #setup the callback handler for mouse move events
        self.motion_ax.figure.canvas.mpl_connect('motion_notify_event', self.on_mouse_move)
        
        self.masked_im_plot = None
        self.quiver_plot = None
        self.int_line_plots = []
        
        #create the matplotlib toolbar
        self.tb = NavBar(self.motion_ax.figure.canvas)
        
        vsizer = wx.BoxSizer(wx.VERTICAL)
        vsizer.Add(self.tb,0,wx.EXPAND)
        vsizer.Add(self.canvas, 1, wx.EXPAND)
        vsizer.Add(self.controls, 0, wx.EXPAND)
        
        self.SetSizer(vsizer)
        vsizer.Fit(self)
        
    
    def show_error_plot(self, state):
        self.show_errors = state
        if state:
            self.motion_ax.change_geometry(1,2,1)
            self.error_ax.set_visible(True)
            self.error_cb_ax.set_visible(True)
            
            self.redraw_plot()
            
        else:
            self.motion_ax.change_geometry(1,1,1)
            self.error_ax.set_visible(False)
            self.error_cb_ax.set_visible(False)
            self.error_cb_ax.clear()
            
            if self.error_plot is not None:
                self.error_plot.remove()
                self.error_plot = None
        
            self.canvas.draw() 
    
    
    def clear_plot(self):
        self.__visible = False
        if self.masked_im_plot is not None:
            self.masked_im_plot.set_visible(False)
        if self.quiver_plot is not None:
            self.quiver_plot.set_visible(False)
        self.canvas.draw() 
        
    
    def on_mouse_move(self, evnt):
        if ((evnt.inaxes != self.motion_ax and evnt.inaxes != self.error_ax) or
            self.__cur_flow is None or not self.__visible):
            self.main_frame.clear_status()
            return
        
        
        x, y = evnt.xdata, evnt.ydata
        x -= self.extent[3]
        y -= self.extent[0]
        
        if evnt.inaxes == self.motion_ax:     
            x *= (self.cur_im_masked.shape[1] - 1) / (self.extent[1] - self.extent[0]) 
            y *= (self.cur_im_masked.shape[0] - 1) / (self.extent[2] - self.extent[3])
            
            x = round(x)
            y = round(y)
            
            if x < 0 or x >= self.cur_im_masked.shape[1]:
                self.main_frame.clear_status()
                return
            
            if y < 0 or y >= self.cur_im_masked.shape[0]:
                self.main_frame.clear_status()
                return

            xvel, yvel = (self.__cur_flow[y, x] * self.__pix_size) / self.__delta_t

            self.main_frame.set_vel_status(x, y, self.cur_im_masked[y, x], xvel, -yvel)
        
        else:
            x = round(x)
            y = round(y)
            if x < 0 or x >= self.cur_im_masked.shape[1]:
                self.main_frame.clear_status()
                return
            
            if y < 0 or y >= self.cur_im_masked.shape[0]:
                self.main_frame.clear_status()
                return
            self.main_frame.set_err_status(x, y, self.errors[y, x])
             
    def set_config(self, config):
        self.config = config
        self.im_loader = image_loader.get_image_loader(config)
        
        try:
            self.motion_engine = motion.GPUMotionEngine(config)
        except AttributeError:
            self.motion_engine = motion.MotionEngine(config)
        
        self.__pix_size = self.config['pixel_size'] * self.config['downsizing_factor']
        
        #now update the plots to reflect the new config
        #clear cached images
        self.extent = None
        self.cur_im = None
        self.cur_time = None
        self.next_im = None
        self.next_time = None
        self.cur_im_masked = None
        self.next_im_masked = None
        self.__cur_flow = None
        self.__delta_t = None
        self.errors = None
        
        if self.cur_filename is not None:
            self.set_images(self.cur_filename, self.next_filename)
    
    
    def __new_cur_im(self, cur_filename):
        self.cur_im, self.cur_time = self.im_loader._load_and_check(cur_filename)
        self.cur_filename = cur_filename
        self.cur_im_masked = self.cur_im.copy()
        self.motion_engine.preprocess(self.cur_im_masked)
    
    
    def __new_next_im(self, next_filename):
        self.next_im, self.next_time = self.im_loader._load_and_check(next_filename)
        self.next_filename = next_filename
        self.next_im_masked = self.next_im.copy()
        self.motion_engine.preprocess(self.next_im_masked)
    
    
    def set_images(self, cur_filename, next_filename):
        
        self.__visible = True
        
        if cur_filename == self.next_filename:
            self.cur_filename = cur_filename
            self.cur_im = self.next_im
            self.cur_im_masked = self.next_im_masked
            self.cur_time = self.next_time
            self.__new_next_im(next_filename)
            
        elif self.cur_filename == next_filename:
            self.next_filename = next_filename
            self.next_im = self.cur_im
            self.next_im_masked = self.cur_im_masked
            self.next_time = self.cur_time
            self.__new_cur_im(cur_filename)
        
        else:
            self.__new_next_im(next_filename)
            self.__new_cur_im(cur_filename)
            
        self.__delta_t = (main_script.date2secs(self.next_time) - 
                          main_script.date2secs(self.cur_time))
        
        #do the motion analysis
        self.__cur_flow = self.motion_engine.compute_flow(self.cur_im_masked, self.next_im_masked)
        
        #reset the stored error map
        self.errors = None
        
        self.redraw_plot()
    
    
    def redraw_plot(self):
        
        x_shifts, y_shifts, self.extent = output.resample_velocities(self.__cur_flow * self.config['downsizing_factor'], self._quiver_density)
        
        if self.masked_im_plot is None:
            self.masked_im_plot = self.motion_ax.imshow(self.cur_im_masked, extent=self.extent)
        else:
            self.masked_im_plot.remove()
            self.masked_im_plot = self.motion_ax.imshow(self.cur_im_masked, extent=self.extent)

        if self.quiver_plot is None:
            self.quiver_plot = self.motion_ax.quiver(x_shifts, y_shifts, 
                                                     width=1.6, units='dots', 
                                                     scale_units='xy',angles='xy',
                                                     scale=self.vector_scale)
        else:
            self.quiver_plot.remove()
            self.quiver_plot = self.motion_ax.quiver(x_shifts, y_shifts, width=1.6, 
                                                     units='dots',scale_units='xy',
                                                     angles='xy',
                                                     scale=self.vector_scale)
        
        #draw integration lines
        for p in self.int_line_plots:
            p.remove()
        self.int_line_plots = []    
        
        for l in self.config['integration_lines']:
            pts = numpy.array(l['integration_points'])
            
            pts[:,0] *= self.extent[1]/float(self.cur_im.shape[1])
            pts[:,1] *= self.extent[2]/float(self.cur_im.shape[0])

            p, =   self.motion_ax.plot(pts[:,0], pts[:,1], 'w-', linewidth=2)
            self.int_line_plots.append(p)
            
            p.set_visible(self.controls.show_intline_chkbx.IsChecked())
        
        self.masked_im_plot.axes.set_xlim(self.extent[:2])
        self.masked_im_plot.axes.set_ylim(self.extent[2:])    

        self.masked_im_plot.set_visible(True)
        self.quiver_plot.set_visible(True)
        
        #draw the error plot
        if self.show_errors:
            if self.error_plot is not None:
                self.error_plot.remove()
            if self.errors is None:
                self.errors = flux.compute_error_map(self.cur_im_masked, self.next_im_masked, self.__cur_flow)
            self.error_plot = self.error_ax.imshow(numpy.clip(self.errors,0,self.cb_clip_limit))
            self.error_cb_ax.clear()
            cb = colorbar(self.error_plot, cax=self.error_cb_ax)
            cb.set_label('Error (%)')
            
        self.canvas.draw()



class ImageFileList(wx.Panel):
    def __init__(self, parent, image_dir,config, plot_panel):
        super(ImageFileList, self).__init__(parent)
        self.config = config
        self.im_loader = image_loader.get_image_loader(config)
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
        
        if not self.im_loader.can_load(filename):
            wx.Yield()
            self.plot_panel.clear_plot()
            wx.MessageBox("Image \"%s\" cannot be loaded using the current image loader class."%filename,"",wx.ICON_WARNING)
            return 1
        
        if not self.im_loader.can_load(next_filename):
            wx.Yield()
            self.plot_panel.clear_plot()
            wx.MessageBox("Image \"%s\" cannot be loaded using the current image loader class."%next_filename,"",wx.ICON_WARNING)
            return 1
        
        if evnt is None:
            self.plot_panel.set_config(self.config)
        
        #use CallAfter to get better response on the selection updating
        wx.CallAfter(self.plot_panel.set_images, filename, next_filename)
        
        return 0
