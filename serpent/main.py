import wx

import gui
import settings


from gui_modules import backing_track
from gui_modules import interval_training


def main():
    print("Serpent v" + settings.version)
    app = wx.App()

    frame = gui.MainFrame(None, title="Serpent")
    frame.add_modules([backing_track.BackingTrack, interval_training.IntervalTraining])

    app.MainLoop()


if __name__ == "__main__":
    main()
