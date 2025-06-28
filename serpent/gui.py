import typing

import wx
import settings


class AboutBox(wx.Dialog):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.panel = wx.Panel(self)
        self.panel.Sizer = wx.BoxSizer(wx.VERTICAL)
        self.panel.Sizer.Add(
            wx.StaticText(self.panel, label="Serpent v" + settings.version)
        )

        samples_license = (
            "You can find the drum sounds used online at"
            "\nfreesound.org/people/Theriavirra/packs/16665/"
        )
        self.panel.Sizer.Add(wx.StaticText(self.panel, label=samples_license))


class MainFrame(wx.Frame):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)

        self.SetSize(1280, 900)
        self.panel = wx.Panel(self)
        self.panel.Sizer = wx.BoxSizer(wx.VERTICAL)

        self.notebook = wx.Notebook(self.panel)
        self.panel.Sizer.Add(self.notebook, proportion=1, flag=wx.EXPAND)

        self.help = wx.Menu()
        self.about = self.help.Append(
            wx.ID_ABOUT, "&About", "About Serpent v" + settings.version
        )

        self.menubar = wx.MenuBar()
        self.menubar.Append(self.help, "&Help")
        self.SetMenuBar(self.menubar)
        self.Bind(wx.EVT_MENU, self.create_about, self.about)

        self.Show(True)

    def create_about(self, event):
        about_box = AboutBox(self, title="About")
        about_box.Show()

    def add_modules(self, modules: list[typing.Type[wx.Panel]]):
        for module in modules:
            instance = module(parent=self.notebook)
            self.notebook.AddPage(instance, instance.title)
