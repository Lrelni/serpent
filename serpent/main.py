import wx

import gui
import audio
import settings


def main():
    app = wx.App()

    frame = gui.Serpent()

    app.MainLoop()


if __name__ == "__main__":
    main()
