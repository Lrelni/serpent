import os

import wx
import pyaudio 
import numpy as np 

import serpent_audio as srpt_audio
import settings


class Utils:
    def __init__(self):
        self.large_text = wx.Font(48, wx.DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
        self.medium_text = wx.Font(30, wx.DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)

class BackingTrack(wx.Panel):

    class SpinCtrlLabel(wx.Panel):
        # control a BPM
        def __init__(self, *args, **kw):
            super().__init__(*args, **kw)
            self.SetSizer(wx.BoxSizer(wx.HORIZONTAL))
            self.field = wx.SpinCtrl(self, -1, min=0, max=1000, initial=175)
            self.field.SetFont(Utils().large_text)
            self.label = wx.StaticText(self, -1, "BPM")
            self.label.SetFont(Utils().medium_text)
            self.GetSizer().Add(self.field, 2, wx.EXPAND)
            self.GetSizer().Add(self.label, 1, wx.CENTER)
        
        def get_bpm(self):
            return self.field.GetValue()
    
    class TSigSpinCtrlLabel(wx.Panel):
        # control time signature
        def __init__(self, *args, **kw):
            super().__init__(*args, **kw)
            self.SetSizer(wx.BoxSizer(wx.HORIZONTAL))
            self.field = wx.SpinCtrl(self, -1, min=1, max=32, initial=4)
            self.field.SetFont(Utils().large_text)
            self.GetSizer().Add(self.field, 2, wx.EXPAND)
        
        def get(self):
            return self.field.GetValue()
        
    class BPMBox(wx.Panel):
        # control BPM, play button, and show flashing light
        def __init__(self, *args, **kw):
            super().__init__(*args, **kw)
           # self.SetBackgroundColour((255,0,0))
            self.SetSizer(wx.BoxSizer(wx.VERTICAL))

            self.bpm_ctrl = BackingTrack.SpinCtrlLabel(self)
            self.play_button = wx.Button(self, -1, "Play")

            self.GetSizer().Add(self.bpm_ctrl, 1, wx.CENTER)
            self.GetSizer().AddSpacer(30)
            self.GetSizer().Add(self.play_button, 5, wx.EXPAND)
        
        def get_bpm(self):
            return self.bpm_ctrl.get_ctrl()
    
    class TSigBox(wx.Panel):
        def __init__(self, *args, **kw):
            super().__init__(*args, **kw)
            self.SetSizer(wx.BoxSizer(wx.VERTICAL))

            self.top = BackingTrack.TSigSpinCtrlLabel(self)
            self.bottom = BackingTrack.TSigSpinCtrlLabel(self)

            self.GetSizer().AddStretchSpacer(1)
            self.GetSizer().Add(self.top, 0, wx.CENTER)
            self.GetSizer().Add(self.bottom, 0, wx.CENTER)
            self.GetSizer().AddStretchSpacer(1)
        
        def get_tsig(self):
            return (self.top.get(), self.bottom.get())

    class StaveBox(wx.Panel):
        def __init__(self, *args, **kw):
            super().__init__(*args, **kw)

    class ControlsBox(wx.Panel):
        def __init__(self, *args, **kw):
            super().__init__(*args, **kw)
            #self.SetBackgroundColour((0,0,255))
            self.SetSizer(wx.BoxSizer(wx.VERTICAL))

            self.bpm_box = BackingTrack.BPMBox(self)
            self.tsig_box = BackingTrack.TSigBox(self)

            self.GetSizer().Add(self.tsig_box, 1, wx.EXPAND)
            self.GetSizer().Add(self.bpm_box, 1, wx.EXPAND)

        def get_bpm(self):
            return self.bpm_box.get_bpm()
        
        def get_tsig(self):
            return self.tsig_box.get_tsig()
    
    class StaveBox(wx.Panel):
        def __init__(self, *args, **kw):
            super().__init__(*args, **kw)
            #self.SetBackgroundColour((255,255,0))

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.title = "Backing Track"
        self.SetSizer(wx.BoxSizer(wx.HORIZONTAL))

        self.controls_box = BackingTrack.ControlsBox(self)
        self.stave_box = BackingTrack.StaveBox(self)

        self.GetSizer().Add(self.controls_box, 1, wx.EXPAND)
        self.GetSizer().Add(self.stave_box, 3, wx.EXPAND)
    
    def get_bpm(self):
        return self.controls_box.get_bpm()
    
    def get_tsig(self):
        return self.controls_box.get_bpm()

class SightReading(wx.Panel):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.title = "Sight Reading"

class AboutBox(wx.Dialog):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.panel = wx.Panel(self)
        text = wx.StaticText(self.panel, label="Serpent v" + settings.version)

class SerpentFrame(wx.Frame):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)

        self.SetSize(1280,900)
        self.panel = wx.Panel(self)
        self.CreateStatusBar()
        
        self.notebook = wx.Notebook(self.panel)
        self.notebook.SetWindowStyleFlag(wx.NB_TOP)
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.sizer.Add(self.notebook, 1, wx.ALL | wx.EXPAND)
        self.panel.SetSizer(self.sizer)


        self.help_menu = wx.Menu()
        self.about_menu_item = self.help_menu.Append(wx.ID_ABOUT, "&About", "About Serpent v"+settings.version)

        self.menu_bar = wx.MenuBar()
        self.menu_bar.Append(self.help_menu, "&Help")
        self.SetMenuBar(self.menu_bar)
        self.Show(True)

        self.Bind(wx.EVT_MENU, self._about, self.about_menu_item)
    
    def _about(self, event):
        about_box = AboutBox(self, title="About")
        about_box.Show()

    def add_modules(self, modules):
        for module in modules:
            m = module(self.notebook)
            self.notebook.AddPage(m, m.title)

def main():
    # test module
    print("serpent_gui.py")

if __name__ == "__main__":
    main()
