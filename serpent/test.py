import wx
import time
import unittest

import main
import gui
import audio
import notes
import settings


class TestPanel(wx.Panel):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.Bind(wx.EVT_PAINT, self.on_paint)

    def on_paint(self, event):
        dc = wx.PaintDC(self)
        dc.SetBrush(wx.Brush(wx.Colour(200, 128, 64), wx.BRUSHSTYLE_CROSSDIAG_HATCH))
        dc.SetPen(wx.Pen("black", 2))
        dc.DrawRectangle(40, 20, 100, 200)
        dc.DrawLine(40, 20, 40 + 100, 20 + 200)


def gui_test():
    app = wx.App()

    frame = wx.Frame(None, title="test.py")
    frame.Show(True)

    testpanel = gui.NoteInputGrid(frame)

    frame.Layout()

    app.MainLoop()


def interactive_test():
    gui_test()


if __name__ == "__main__":
    print("test.py")
    interactive_test()
