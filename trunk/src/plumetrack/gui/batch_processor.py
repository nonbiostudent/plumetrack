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
import os
import plumetrack
from plumetrack import persist, settings, main_script

class BatchProcessor(wx.Dialog):
    def __init__(self, parent, config_file):
        super(BatchProcessor, self).__init__(parent, -1, "Batch Process Images "
                                             "- %s"%plumetrack.PROG_SHORT_NAME)
        
        self.config_file = config_file
        
        top_panel = wx.Panel(self, wx.ID_ANY)
        vsizer = wx.BoxSizer(wx.VERTICAL)
        top_sizer = wx.BoxSizer(wx.VERTICAL)
        vsizer.AddSpacer(10)
        
        #add the image directory options
        vsizer.Add(wx.StaticText(top_panel, -1, "Image folder:"), 0, wx.ALIGN_LEFT| wx.LEFT, border=5)
        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        self.im_dir_box = wx.TextCtrl(top_panel, -1, size=(350,-1))
        self.ims_browse_button = wx.Button(top_panel, -1, "Browse")
        hsizer.Add(self.im_dir_box, 1, wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL | wx.LEFT, border=5)
        hsizer.Add(self.ims_browse_button, 0, wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, border=5)
        vsizer.Add(hsizer, 1, wx.EXPAND)
        
        self.recursive_chkbx = wx.CheckBox(top_panel, -1, "Search folder recursively")
        vsizer.Add(self.recursive_chkbx, 0, wx.ALL | wx.ALIGN_LEFT, border=5)
        
        wx.EVT_BUTTON(self, self.ims_browse_button.GetId(), self.on_images_browse)
        
        vsizer.AddSpacer(10)
        
        #add the output file options
        vsizer.Add(wx.StaticText(top_panel, -1, "Results file:"), 0, wx.ALIGN_LEFT| wx.LEFT, border=5)
        hsizer2 = wx.BoxSizer(wx.HORIZONTAL)
        self.output_file_bx = wx.TextCtrl(top_panel, -1, size=(350,-1))
        self.output_browse_button = wx.Button(top_panel, -1, "Browse")
        hsizer2.Add(self.output_file_bx, 1, wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL| wx.LEFT, border=5)
        hsizer2.Add(self.output_browse_button, 0, wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL| wx.RIGHT, border=5)
        vsizer.Add(hsizer2, 1, wx.EXPAND)
        
        wx.EVT_BUTTON(self, self.output_browse_button.GetId(), self.on_output_browse)
        
        vsizer.AddSpacer(20)
        
        #add the buttons
        self.ok_button = wx.Button(top_panel, -1, "Ok")
        self.cancel_button = wx.Button(top_panel, -1, "Cancel")
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        button_sizer.Add(self.ok_button, 0, wx.ALIGN_BOTTOM|wx.ALIGN_RIGHT)
        button_sizer.Add(self.cancel_button, 0, wx.ALIGN_BOTTOM|wx.ALIGN_RIGHT)
        wx.EVT_BUTTON(self, self.cancel_button.GetId(), self.on_cancel)
        wx.EVT_BUTTON(self, self.ok_button.GetId(), self.on_process)
        
        vsizer.Add(button_sizer, 1, wx.ALIGN_BOTTOM| wx.ALIGN_RIGHT)
        
        top_sizer.Add(top_panel, 1, wx.EXPAND| wx.ALIGN_TOP)
        
        top_panel.SetSizer(vsizer)
        top_panel.SetAutoLayout(True)
        vsizer.Fit(self)
        
        self.SetSizer(top_sizer)
        self.SetAutoLayout(True)
        top_sizer.Layout() #this fixes the problem of the frame being created too small
        top_sizer.Fit(top_panel)
        
        self.ShowModal()
        
        
        
    def on_images_browse(self, evnt):
        
        current_dir = self.im_dir_box.GetValue()
        
        if current_dir != "" and os.path.isdir(current_dir):
            prev_dir = current_dir
            
        else:
            try:
                prev_dir = persist.PersistentStorage().get_value("prev_image_dir")
            except KeyError:
                prev_dir = ""
        
        im_dir = wx.DirSelector("Select directory containing images to process",
                                 defaultPath=prev_dir)
        
        if im_dir == "":
            return
        
        self.im_dir_box.SetValue(im_dir)
            
        persist.PersistentStorage().set_value("prev_image_dir", im_dir)
        
    
    
    def on_output_browse(self, evnt):
        
        current_dir = os.path.dirname(self.output_file_bx.GetValue())
        current_filename = os.path.basename(self.output_file_bx.GetValue())
        
        if current_dir != "" and os.path.isdir(current_dir):
            prev_dir = current_dir
            
        else:
            try:
                prev_dir = persist.PersistentStorage().get_value("prev_output_dir")
            except KeyError:
                prev_dir = ""
        
        if current_filename != "" and os.path.exists(current_dir):
            prev_filename = current_filename
        
        else:
            try:
                prev_filename = persist.PersistentStorage().get_value("prev_output_file")
            except KeyError:
                prev_filename = ""
        
        output_file = wx.FileSelector("Select output file", default_path=prev_dir, 
                                 default_filename=prev_filename,
                                 flags=wx.FD_SAVE|wx.FD_OVERWRITE_PROMPT)
        
        if output_file == "":
            return
        
        self.output_file_bx.SetValue(output_file)
            
        persist.PersistentStorage().set_value("prev_output_dir", 
                                              os.path.dirname(output_file))
        persist.PersistentStorage().set_value("prev_output_file",
                                              os.path.basename(output_file))
    
    
    def on_process(self, evnt):
        
        cmd_args = ["-f", self.config_file, 
                    "-p", #parallel process by default
                    "-o", self.output_file_bx.GetValue(),
                    self.im_dir_box.GetValue()]
        
        try:
            options, args = settings.parse_cmd_line(cmd_args, exception_on_error=True)
        except settings.OptionError,ex:
            wx.MessageBox(ex.args[0],plumetrack.PROG_SHORT_NAME,wx.ICON_ERROR)
            return
        
        dialog = wx.ProgressDialog("Processing... - Plumetrack", 
                                   "Processing images. Please Wait.", 
                                   parent=self, style=wx.PD_CAN_ABORT | wx.PD_REMAINING_TIME | wx.PD_AUTO_HIDE)
        
        progress_handler = lambda x: dialog.Update(100*x)[0]
        success = main_script.run_mainloop(options, args, progress_handler)
        dialog.Destroy()
        wx.Yield()
        
        if success:
            self.EndModal(wx.CANCEL)
            wx.MessageBox("Finished processing. Results saved to %s"%self.output_file_bx.GetValue())
            self.Destroy()
        
    
    def on_cancel(self, evnt):
        self.EndModal(wx.CANCEL)
        
        