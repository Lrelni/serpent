import copy
import os
import typing

import wx

import audio
import settings


def map_range(from1, from2, to1, to2, val):
    return ((to2 - to1) / (from2 - from1)) * (val - from1) + to1


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


class NoteInputStrip(wx.Panel):

    def __init__(self, *args, **kw):
        # constants stored here because wx.App needs to be inited first
        self.DEFAULT_LEFT_TIME, self.DEFAULT_RIGHT_TIME = 0.05, 4
        self.DEFAULT_QUANTIZE_LEVEL = 0.37
        self.DEFAULT_NOTES_BRUSH = wx.Brush(wx.Colour(60, 60, 60))
        self.DEFAULT_NOTES_PEN = wx.Pen("black", width=3)
        self.TENTATIVE_NOTES_BRUSH = wx.Brush(
            wx.Colour(20, 20, 20), style=wx.BRUSHSTYLE_FDIAGONAL_HATCH
        )
        self.TENTATIVE_NOTES_PEN = wx.TRANSPARENT_PEN
        self.BACKGROUND_BRUSH = wx.Brush(wx.Colour(190, 190, 190))
        self.BACKGROUND_PEN = wx.TRANSPARENT_PEN
        self.QUANTIZE_LINES_PEN = wx.Pen(wx.Colour(140, 140, 140, 64), width=1)

        super().__init__(*args, **kw)
        self._notes: list[audio.Note] = []
        self.time_window = (self.DEFAULT_LEFT_TIME, self.DEFAULT_RIGHT_TIME)
        self.quantize_width = self.DEFAULT_QUANTIZE_LEVEL
        self.tentative_note: audio.Note = None

        self.Bind(wx.EVT_PAINT, self.on_paint)
        self.Bind(wx.EVT_LEFT_DOWN, self.on_left_down)
        self.Bind(wx.EVT_LEFT_UP, self.on_left_up)
        self.Bind(wx.EVT_RIGHT_DOWN, self.on_right_down)
        self.Bind(wx.EVT_MOUSEWHEEL, self.on_mouse_wheel)
        self.Bind(wx.EVT_MOTION, self.on_mouse_move)

    def time_to_x(self, time: float):
        return map_range(
            from1=self.time_window[0],
            from2=self.time_window[1],
            to1=0,
            to2=self.ClientSize[0],  # width
            val=time,
        )

    def x_to_time(self, x: float):
        return map_range(
            from1=0,
            from2=self.ClientSize[0],  # width
            to1=self.time_window[0],
            to2=self.time_window[1],
            val=x,
        )

    def quantize(self, time: float):
        return self.quantize_width * round(time / self.quantize_width)

    def time_len_to_x_len(self, time_len: float):
        return (  # conversion rate: x len per time len
            self.ClientSize[0] / (self.time_window[1] - self.time_window[0])
        ) * time_len

    def draw_note(self, dc: wx.PaintDC, note: audio.Note):
        """Note: caller sets wx Brush and Pen"""
        dc.DrawRectangle(
            x=int(self.time_to_x(note.time)),
            y=0,
            width=max(int(self.time_len_to_x_len(note.length)), 1),
            height=self.ClientSize[1],
        )

    def draw_quantize_lines(self, dc: wx.PaintDC):
        dc.Pen = self.QUANTIZE_LINES_PEN
        time = self.quantize(self.time_window[0])
        while time <= self.time_window[1]:
            dc.DrawLine(
                int(self.time_to_x(time)),
                0,
                int(self.time_to_x(time)),
                self.ClientSize[1],
            )
            time += self.quantize_width

    def draw_background(self, dc: wx.PaintDC):
        dc.Brush = self.BACKGROUND_BRUSH
        dc.Pen = self.BACKGROUND_PEN
        dc.DrawRectangle(x=0, y=0, width=self.ClientSize[0], height=self.ClientSize[1])

    def on_paint(self, event):
        dc = wx.PaintDC(self)
        self.draw_background(dc)
        # normal notes
        dc.Brush = self.DEFAULT_NOTES_BRUSH
        dc.Pen = self.DEFAULT_NOTES_PEN
        for note in self._notes:
            self.draw_note(dc, note)
        # tentative note
        if self.tentative_note is not None:
            dc.Brush = self.TENTATIVE_NOTES_BRUSH
            dc.Pen = self.TENTATIVE_NOTES_PEN
            self.draw_note(dc, self.tentative_note)
        self.draw_quantize_lines(dc)

    def update_contents(self):
        self.Refresh()
        self.Update()

    def zoom_to_window(self, window: tuple[float, float]):
        self.time_window = window
        self.update_contents()

    @property
    def notes(self) -> list[audio.Note]:
        return self._notes

    @notes.setter
    def notes(self, val: list[audio.Note]):
        self._notes = val
        self.validate_notes()
        self.update_contents()

    def validate_notes(self):
        okay: list[audio.Note] = []
        for note in self._notes:
            should_append = True
            for okay_note in okay:
                if okay_note.overlaps(note):
                    should_append = False
            if should_append:
                okay.append(note)
        self._notes = okay

    def note_at(self, time: float) -> audio.Note:
        """Return result not guaranteed for unvalidated ._notes"""
        for note in self._notes:
            if note.contains(time):
                return note
        return None

    def note_index_at(self, time: float) -> int:
        """Return result not guaranteed for unvalidated ._notes"""
        for i in range(len(self._notes)):
            if self._notes[i].contains(time):
                return i
        return None

    def add_note(self, note: audio.Note):
        """Will call .validate_notes() after appending note"""
        for okay_note in self._notes:
            if okay_note.overlaps(note):
                print("Warning: note not added because of overlap")
                return
        self._notes.append(copy.copy(note))

    def tentative_set_beginning(self, x: float):
        self.tentative_note = audio.Note(
            time=self.quantize(self.x_to_time(x)),
            length=max(0.01, self.quantize_width),
        )

    def tentative_set_end(self, x: float):
        if self.tentative_note is None:
            return  # don't set len if it didn't already exist
        end_time = self.quantize(self.x_to_time(x))
        length = max(end_time - self.tentative_note.time, self.quantize_width)

        self.tentative_note.length = abs(length)

    def on_left_down(self, event: wx.MouseEvent):
        if self.note_at(self.x_to_time(event.Position[0])) is not None:
            return  # don't create notes in already existing notes
        self.tentative_set_beginning(event.Position[0])
        self.update_contents()

    def on_left_up(self, event: wx.MouseEvent):
        self.tentative_set_end(event.Position[0])
        if self.tentative_note is not None:
            self.add_note(self.tentative_note)
            self.tentative_note = None
        self.update_contents()

    def on_mouse_move(self, event: wx.MouseEvent):
        self.tentative_set_end(event.Position[0])
        self.update_contents()

    def on_right_down(self, event: wx.MouseEvent):
        note_index = self.note_index_at(self.x_to_time(event.Position[0]))
        if note_index is not None:
            self._notes.pop(note_index)
        self.update_contents()

    def on_mouse_wheel(self, event: wx.MouseEvent):
        window_center = (self.time_window[0] + self.time_window[1]) / 2
        offsets_from_center = (
            self.time_window[0] - window_center,
            self.time_window[1] - window_center,
        )
        SCALING_FACTOR = 0.9 if event.WheelRotation > 0 else 1.1
        new_window = (
            SCALING_FACTOR * (self.time_window[0] - window_center) + window_center,
            SCALING_FACTOR * (self.time_window[1] - window_center) + window_center,
        )
        self.zoom_to_window(new_window)


class BackingTrack(wx.Panel):
    class TimeSignatureControl(wx.Panel):
        def __init__(self, *args, **kw):
            super().__init__(*args, **kw)
            self.Sizer = wx.BoxSizer(wx.VERTICAL)
            INCREMENT = 1
            TOP_INITIAL, BOTTOM_INITIAL = 4, 4
            TOP_MIN, TOP_MAX = 1, 64
            BOTTOM_MIN, BOTTOM_MAX = 1, 64
            LARGE_TEXT_FONT = wx.Font(
                48, wx.DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD
            )

            self.top_field = wx.SpinCtrl(
                self,
                min=TOP_MIN,
                max=TOP_MAX,
                initial=TOP_INITIAL,
                name="time_signature_control_top",
            )
            self.top_field.Increment = INCREMENT
            self.top_field.Font = LARGE_TEXT_FONT

            self.bottom_field = wx.SpinCtrl(
                self,
                min=BOTTOM_MIN,
                max=BOTTOM_MAX,
                initial=BOTTOM_INITIAL,
                name="time_signature_control_bottom",
            )
            self.bottom_field.Increment = INCREMENT
            self.bottom_field.Font = LARGE_TEXT_FONT

            self.Sizer.Add(self.top_field, proportion=1, flag=wx.EXPAND)
            self.Sizer.Add(self.bottom_field, proportion=1, flag=wx.EXPAND)

    class LeftControls(wx.Panel):
        def __init__(self, *args, **kw):
            super().__init__(*args, **kw)
            self.Sizer = wx.BoxSizer(wx.VERTICAL)

            PLAY_BUTTON_Y_HEIGHT = 100
            self.play_button = wx.Button(
                self,
                label="Play/Stop",
                name="play_button",
                size=(0, PLAY_BUTTON_Y_HEIGHT),
            )

            self.bpm_control = BPMControl(self)

            self.time_signature_control = BackingTrack.TimeSignatureControl(self)

            self.Sizer.Add(self.play_button, proportion=5, flag=wx.EXPAND)
            self.Sizer.Add(self.bpm_control, proportion=1, flag=wx.CENTER)
            self.Sizer.Add(self.time_signature_control, proportion=1, flag=wx.CENTER)

    class RightControls(wx.Panel):
        def __init__(self, *args, **kw):
            super().__init__(*args, **kw)
            self.Sizer = wx.BoxSizer(wx.VERTICAL)

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.title = "Backing Track"

        self.Sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.left_controls = BackingTrack.LeftControls(parent=self)
        self.right_controls = BackingTrack.RightControls(parent=self)

        self.Sizer.Add(self.left_controls, proportion=1, flag=wx.EXPAND)
        self.Sizer.Add(self.right_controls, proportion=4, flag=wx.EXPAND)
