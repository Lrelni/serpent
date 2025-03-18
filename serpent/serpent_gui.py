import wx
import pyaudio 
import numpy as np 

import serpent_audio as srpt_audio
import settings

class BackingTrack(wx.Panel):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.title = "Backing Track"
        self.SetSizer(wx.BoxSizer(wx.HORIZONTAL))

        self.controls_box = wx.Panel(self)
        self.controls_box.SetBackgroundColour((0,0,255))
        self.controls_box.SetSizer(wx.BoxSizer(wx.VERTICAL))

        self.bpm_box = wx.Panel(self.controls_box)
        self.bpm_box.SetBackgroundColour((255,0,0))
        self.bpm_box.SetSizer(wx.BoxSizer(wx.HORIZONTAL))

        self.bpm_entry = wx.TextCtrl(self.bpm_box, value="175")
        self.bpm_label = wx.StaticText(self.bpm_box, label="BPM")

        self.tsig_box = wx.Panel(self.controls_box)
        self.tsig_box.SetBackgroundColour((0,255,0))
        self.tsig_box.SetSizer(wx.BoxSizer(wx.VERTICAL))

        self.tsig_box_l1 = wx.StaticText(self.tsig_box, label="3")
        self.tsig_box_l2 = wx.StaticText(self.tsig_box, label="4")

        self.stave_box = wx.Panel(self)
        self.stave_box.SetBackgroundColour((255,255,0))

        self.tsig_box.GetSizer().Add(self.tsig_box_l1)
        self.tsig_box.GetSizer().Add(self.tsig_box_l2)
        self.bpm_box.GetSizer().Add(self.bpm_entry)
        self.bpm_box.GetSizer().Add(self.bpm_label)

        self.controls_box.GetSizer().Add(self.tsig_box, 1, wx.EXPAND)
        self.controls_box.GetSizer().Add(self.bpm_box, 1, wx.EXPAND)

        self.GetSizer().Add(self.controls_box, 1, wx.EXPAND)
        self.GetSizer().Add(self.stave_box, 3, wx.EXPAND)

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
