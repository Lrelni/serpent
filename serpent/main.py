import wx

import gui
import audio
import settings


def main():
    print("Serpent v" + settings.version)
    app = wx.App()

    frame = gui.MainFrame(None, title="Serpent")
    frame.add_modules([gui.BackingTrack])

    app.MainLoop()


if __name__ == "__main__":
    main()
