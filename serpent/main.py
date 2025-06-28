import wx

import gui
import settings


from gui_modules import backing_track


def main():
    print("Serpent v" + settings.version)
    app = wx.App()

    frame = gui.MainFrame(None, title="Serpent")
    frame.add_modules([backing_track.BackingTrack])

    app.MainLoop()


if __name__ == "__main__":
    main()
