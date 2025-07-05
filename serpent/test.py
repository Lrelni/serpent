import wx
import time

import main
import gui
import audio
import notes
import settings

from gui_modules import backing_track
from gui_modules import interval_training


def wait():
    while True:
        time.sleep(2)


def gui_test():
    app = wx.App()
    frame = wx.Frame(None, title="test.py")
    frame.Size = wx.Size(900, 200)
    frame.Show(True)

    frame.Sizer = wx.BoxSizer(wx.VERTICAL)

    testpanel = interval_training.IntervalTraining(frame)

    frame.Sizer.Add(testpanel, proportion=1, flag=wx.EXPAND)

    frame.Layout()

    app.MainLoop()


def audio_test():
    pass


if __name__ == "__main__":
    print("test.py")
    gui_test()
