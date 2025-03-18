import wx
import pyaudio 
import numpy as np 

import serpent_audio as srpt_audio
import settings

class BackingTrack(wx.Panel):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.title = "Backing Track"

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
