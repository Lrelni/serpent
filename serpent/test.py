import wx
import time

import main
import gui
import audio
import notes
import settings


def wait():
    while True:
        time.sleep(2)


def gui_test():
    app = wx.App()
    frame = wx.Frame(None, title="test.py")
    frame.Size = wx.Size(900, 200)
    frame.Show(True)

    testpanel = gui.BackingTrack(frame)

    frame.Layout()

    app.MainLoop()


def audio_test():
    voice = audio.AudioFile("samples/ride.wav")
    player = audio.Player(voice)
    time.sleep(0.1)
    voice.notes = []
    print(voice.notes)
    wait()


if __name__ == "__main__":
    print("test.py")
    audio_test()
