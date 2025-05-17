import wx
import time

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


def wait():
    while True:
        time.sleep(2)


def gui_test():
    app = wx.App()
    frame = wx.Frame(None, title="test.py")
    frame.Size = wx.Size(900, 200)
    frame.Show(True)

    # testpanel = gui.VoiceEditor(
    #    frame,
    #    audio.Voice(
    #        audio.ADSR(audio.Harmonics(), attack_len=0.05), [], 4, 120, pitched=True
    #    ),
    #    "Test Voice",
    # )
    testpanel = gui.VoiceEditorList(frame)

    # player = audio.Player(testpanel._voice)

    frame.Layout()

    app.MainLoop()


def audio_test():
    voice = audio.Voice(
        audio.ADSR(audio.Sine(amplitude=0.5)),
        [audio.Note(0.1, 1)],
        4,
        120,
        pitched=True,
    )

    player = audio.Player(voice)
    time.sleep(0.1)
    voice.notes = []
    print(voice.notes)
    wait()


if __name__ == "__main__":
    print("test.py")
    gui_test()
