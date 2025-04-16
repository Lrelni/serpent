import os
import typing

import wx

import audio
import settings


class AboutBox(wx.Dialog):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.panel = wx.Panel(self)
        text = wx.StaticText(self.panel, label="Serpent v" + settings.version)


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


class BPMControl(wx.Panel):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.Sizer = wx.BoxSizer(wx.HORIZONTAL)

        BPM_MIN, BPM_MAX = 1, 1000
        BPM_INITIAL = 130
        BPM_INCREMENT = 5
        self.field = wx.SpinCtrl(
            self, min=BPM_MIN, max=BPM_MAX, initial=BPM_INITIAL, name="bpm_control"
        )
        self.field.Increment = BPM_INCREMENT

        LARGE_TEXT_FONT = wx.Font(
            48, wx.DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD
        )
        self.field.Font = LARGE_TEXT_FONT

        self.label = wx.StaticText(self, label="BPM")
        MEDIUM_TEXT_FONT = wx.Font(
            30, wx.DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL
        )
        self.label.Font = MEDIUM_TEXT_FONT

        self.Sizer.Add(self.field, proportion=2, flag=wx.CENTER)
        self.Sizer.Add(self.label, proportion=1, flag=wx.CENTER)


class BackingTrack(wx.Panel):
    class LeftControls(wx.Panel):
        def __init__(self, *args, **kw):
            super().__init__(*args, **kw)
            self.Sizer = wx.BoxSizer(wx.VERTICAL)

            PLAY_BUTTON_Y_HEIGHT = 350
            self.play_button = wx.Button(
                self,
                label="Play/Stop",
                name="play_button",
                size=(0, PLAY_BUTTON_Y_HEIGHT),
            )

            self.bpm_control = BPMControl(self)

            self.Sizer.Add(self.play_button, proportion=5, flag=wx.EXPAND)
            self.Sizer.Add(self.bpm_control, proportion=1, flag=wx.CENTER)

    class RightControls(wx.Panel):
        def __init__(self, *args, **kw):
            super().__init__(*args, **kw)

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.title = "Backing Track"

        self.Sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.left_controls = BackingTrack.LeftControls(parent=self)
        self.right_controls = BackingTrack.RightControls(parent=self)

        self.Sizer.Add(self.left_controls, proportion=1)
        self.Sizer.Add(self.right_controls, proportion=4)
