import copy
import math
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
        self.DEFAULT_LEFT_TIME, self.DEFAULT_RIGHT_TIME = 1, 4
        self.DEFAULT_QUANTIZE_WIDTH = 1 / 4
        self.ZOOM_FACTOR_IN, self.ZOOM_FACTOR_OUT = 0.9, 1 / 0.9
        self.DEFAULT_NOTES_BRUSH = wx.Brush(wx.Colour(60, 60, 60))
        self.DEFAULT_NOTES_PEN = wx.Pen("black", width=3)
        self.TENTATIVE_NOTES_BRUSH = wx.Brush(
            wx.Colour(20, 20, 20), style=wx.BRUSHSTYLE_FDIAGONAL_HATCH
        )
        self.TENTATIVE_NOTES_PEN = wx.TRANSPARENT_PEN
        self.BACKGROUND_BRUSH = wx.Brush(wx.Colour(190, 190, 190))
        self.BACKGROUND_PEN = wx.Pen(wx.Colour(140, 140, 140, 64), width=2)
        self.QUANTIZE_LINES_PEN = wx.Pen(
            wx.Colour(140, 140, 140, 64), width=1, style=wx.PENSTYLE_LONG_DASH
        )

        super().__init__(*args, **kw)
        self._notes: list[audio.Note] = []
        self.time_window = (self.DEFAULT_LEFT_TIME, self.DEFAULT_RIGHT_TIME)
        self.quantize_width = self.DEFAULT_QUANTIZE_WIDTH
        self.tentative_note: audio.Note | None = None

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

    def x_len_to_time_len(self, x_len: float):
        return (
            (self.time_window[1] - self.time_window[0]) / self.ClientSize[0]
        ) * x_len

    def draw_note(self, dc: wx.PaintDC, brush: wx.Brush, pen: wx.Pen, note: audio.Note):
        dc.Brush = brush
        dc.Pen = pen
        dc.DrawRectangle(
            x=int(self.time_to_x(note.time)),
            y=0,
            width=max(int(self.time_len_to_x_len(note.length)), 1),
            height=self.ClientSize[1],
        )

    def draw_notes(
        self, dc: wx.PaintDC, brush: wx.Brush, pen: wx.Pen, notes: list[audio.Note]
    ):
        """Helper method to not have to set dc.Brush and dc.Pen repeatedly"""
        dc.Brush = brush
        dc.Pen = pen
        for note in notes:
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
                x1=int(self.time_to_x(time)),
                y1=0,
                x2=int(self.time_to_x(time)),
                y2=self.ClientSize[1],
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
        self.draw_notes(
            dc,
            self.DEFAULT_NOTES_BRUSH,
            self.DEFAULT_NOTES_PEN,
            self._notes,
        )
        # tentative note
        if self.tentative_note is not None:
            self.draw_note(
                dc,
                self.TENTATIVE_NOTES_BRUSH,
                self.TENTATIVE_NOTES_PEN,
                self.tentative_note,
            )
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

    def note_at(self, time: float) -> audio.Note | None:
        """Return result not guaranteed for unvalidated ._notes"""
        for note in self._notes:
            if note.contains(time):
                return note
        return None

    def note_index_at(self, time: float) -> int | None:
        """Return result not guaranteed for unvalidated ._notes"""
        for i in range(len(self._notes)):
            if self._notes[i].contains(time):
                return i
        return None

    def add_note(self, note: audio.Note):
        """May not add notes if there is overlap"""
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
        is_shift = wx.GetKeyState(wx.WXK_SHIFT)
        if is_shift:
            if self.last_position is not None:
                delta = wx.GetMousePosition() - self.last_position
                # invert delta.x to make time window follow cursor
                self.pan_time_window(self.x_len_to_time_len(-delta.x))
        else:
            self.tentative_set_end(event.Position[0])
        self.update_contents()

    def on_right_down(self, event: wx.MouseEvent):
        note_index = self.note_index_at(self.x_to_time(event.Position[0]))
        if note_index is not None:
            self._notes.pop(note_index)
        self.update_contents()

    def pan_time_window(self, time_amount: float):
        new_window = (
            self.time_window[0] + time_amount,
            self.time_window[1] + time_amount,
        )
        self.zoom_to_window(new_window)

    def zoom_time_by_factor(self, factor: float):
        window_center = (self.time_window[0] + self.time_window[1]) / 2
        new_window = (
            factor * (self.time_window[0] - window_center) + window_center,
            factor * (self.time_window[1] - window_center) + window_center,
        )
        self.zoom_to_window(new_window)

    def on_mouse_wheel(self, event: wx.MouseEvent):
        self.zoom_time_by_factor(
            self.ZOOM_FACTOR_IN if event.WheelRotation > 0 else self.ZOOM_FACTOR_OUT
        )


class PitchedNoteInputStrip(NoteInputStrip):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.DEFAULT_PITCH_WINDOW_LOWER, self.DEFAULT_PITCH_WINDOW_HIGHER = 59, 72
        self.PITCH_ZOOM_IN, self.PITCH_ZOOM_OUT = 1, -1
        self.PITCH_LINES_PEN = wx.Pen(wx.Colour(140, 140, 140, 64), width=1)

        self.pitch_window = (
            self.DEFAULT_PITCH_WINDOW_LOWER,
            self.DEFAULT_PITCH_WINDOW_HIGHER,
        )
        self.pitch_width_y = 1
        self.pitch_width_y_update()

        self.delta_y_accumulate = 0  # for panning

    # inherit .time_to_x

    # inherit .x_to_time

    def pitch_to_y(self, pitch: int):
        return map_range(
            from1=self.pitch_window[0],
            from2=self.pitch_window[1],
            to1=self.ClientSize[1],  # height
            to2=0,
            val=pitch,
        )

    def y_to_pitch(self, y: float) -> int:
        return math.ceil(
            map_range(
                from1=0,
                from2=self.ClientSize[1],  # height
                to1=self.pitch_window[1],
                to2=self.pitch_window[0],
                val=y,
            )
        )

    def y_len_to_pitch_len(self, y_len: float) -> int:
        return int(
            ((self.pitch_window[1] - self.pitch_window[0]) / self.ClientSize[1]) * y_len
        )

    # inherit .quantize

    # inherit .time_len_to_x_len

    # inherit .x_len_to_time_len

    def pitch_width_y_update(self):
        self.pitch_width_y = int(
            self.ClientSize[1] / (self.pitch_window[1] - self.pitch_window[0])
        )

    def draw_note(
        self, dc: wx.PaintDC, brush: wx.Brush, pen: wx.Pen, note: audio.PitchedNote
    ):
        dc.Brush = brush
        dc.Pen = pen
        dc.DrawRectangle(
            x=int(self.time_to_x(note.time)),
            y=int(self.pitch_to_y(note.pitch)),
            width=max(int(self.time_len_to_x_len(note.length)), 1),
            height=self.pitch_width_y,
        )

    def draw_notes(
        self,
        dc: wx.PaintDC,
        brush: wx.Brush,
        pen: wx.Pen,
        notes: list[audio.PitchedNote],
    ):
        """Helper method to not have to set dc.Brush and dc.Pen repeatedly"""
        dc.Brush = brush
        dc.Pen = pen
        for note in notes:
            dc.DrawRectangle(
                x=int(self.time_to_x(note.time)),
                y=int(self.pitch_to_y(note.pitch)),
                width=max(int(self.time_len_to_x_len(note.length)), 1),
                height=self.pitch_width_y,
            )

    # inherit .draw_quantize_lines

    def draw_pitch_lines(self, dc: wx.PaintDC):
        dc.Pen = self.PITCH_LINES_PEN
        pitch = self.pitch_window[0]
        while pitch <= self.pitch_window[1]:
            dc.DrawLine(
                x1=0,
                y1=int(self.pitch_to_y(pitch)),
                x2=self.ClientSize[0],  # width
                y2=int(self.pitch_to_y(pitch)),
            )
            pitch += 1

    # inherit .draw_background

    def on_paint(self, event):
        self.pitch_width_y_update()
        dc = wx.PaintDC(self)
        self.draw_background(dc)
        # normal notes
        self.draw_notes(
            dc,
            self.DEFAULT_NOTES_BRUSH,
            self.DEFAULT_NOTES_PEN,
            self._notes,
        )
        # tentative note
        if self.tentative_note is not None:
            self.draw_note(
                dc,
                self.TENTATIVE_NOTES_BRUSH,
                self.TENTATIVE_NOTES_PEN,
                self.tentative_note,
            )
        self.draw_quantize_lines(dc)
        self.draw_pitch_lines(dc)

    # inherit .update_contents

    def zoom_to_time_window(self, time_window: tuple[float, float]):
        self.time_window = time_window
        self.update_contents()

    def zoom_to_pitch_window(self, pitch_window: tuple[int, int]):
        self.pitch_window = pitch_window
        self.pitch_width_y_update()
        self.update_contents()

    # inherit  .pan_time_window

    def pan_pitch_window(self, pitch_amount: int):
        new_window = (
            self.pitch_window[0] + pitch_amount,
            self.pitch_window[1] + pitch_amount,
        )
        self.zoom_to_pitch_window(new_window)

    def zoom_to_window(
        self,
        time_window: tuple[float, float],
        pitch_window: tuple[int, int] | None = None,
    ):
        self.time_window = time_window
        if pitch_window is not None:
            self.pitch_window = pitch_window
            self.pitch_width_y_update()
        self.update_contents()

    # inherit .notes getter and setter

    # inherit .validate_notes()

    # inherit .note_at

    # inherit .note_index_at

    # inherit .add_note

    def tentative_set_beginning(self, x: float, y: float):
        self.tentative_note = audio.PitchedNote(
            time=self.quantize(self.x_to_time(x)),
            length=max(0.01, self.quantize_width),
            pitch=int(self.y_to_pitch(y)),
        )

    # inherit .tentative_set_end

    def on_left_down(self, event: wx.MouseEvent):
        if self.note_at(self.x_to_time(event.Position[0])) is not None:
            return  # don't create notes in already existing notes
        self.tentative_set_beginning(event.Position[0], event.Position[1])
        self.update_contents()

    # inherit .on_left_up

    def on_mouse_move(self, event: wx.MouseEvent):
        is_shift = wx.GetKeyState(wx.WXK_SHIFT)
        if is_shift:
            if self.last_position is not None:
                delta = wx.GetMousePosition() - self.last_position
                # invert delta.x but not delta.y to make window follow cursor
                self.pan_time_window(self.x_len_to_time_len(-delta.x))

                pitch_move = self.y_len_to_pitch_len(delta.y + self.delta_y_accumulate)

                if -1 < pitch_move and pitch_move < 1:
                    self.delta_y_accumulate += delta.y
                    # accumulate to make sensitivity work
                else:
                    self.pan_pitch_window(pitch_move)
                    self.delta_y_accumulate = 0
        else:  # not shift
            self.tentative_set_end(event.Position[0])
        self.update_contents()
        self.last_position = wx.GetMousePosition()

    # inherit .on_right_down

    def zoom_time_by_factor(self, factor: float):
        window_center = (self.time_window[0] + self.time_window[1]) / 2
        new_window = (
            factor * (self.time_window[0] - window_center) + window_center,
            factor * (self.time_window[1] - window_center) + window_center,
        )
        self.zoom_to_time_window(new_window)

    def zoom_pitch_by_level(self, level: int):
        new_window = (self.pitch_window[0] + level, self.pitch_window[1] - level)
        if new_window[1] - new_window[0] <= 0:
            return  # don't set to windows with span <= 0
        self.zoom_to_pitch_window(new_window)

    def on_mouse_wheel(self, event: wx.MouseEvent):
        # ctrl+scroll to zoom pitch
        is_control = wx.GetKeyState(wx.WXK_CONTROL)
        if is_control:
            self.zoom_pitch_by_level(
                self.PITCH_ZOOM_IN if event.WheelRotation > 0 else self.PITCH_ZOOM_OUT
            )
        else:
            self.zoom_time_by_factor(
                self.ZOOM_FACTOR_IN if event.WheelRotation > 0 else self.ZOOM_FACTOR_OUT
            )


class NoteInputGrid(wx.Panel):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)

        self.DEFAULT_LEFT_TIME, self.DEFAULT_RIGHT_TIME = 1, 16
        self.DEFAULT_QUANTIZE_LEVEL = 1 / 4

        self.strips: list[NoteInputStrip] = [NoteInputStrip(self) for _ in range(5)]
        self.time_window = (self.DEFAULT_LEFT_TIME, self.DEFAULT_RIGHT_TIME)
        self.quantize_width = self.DEFAULT_QUANTIZE_LEVEL
        self.init_gui()
        self.sync_to_strips()

    def init_gui(self):
        self.Sizer = wx.BoxSizer(wx.VERTICAL)
        for strip in self.strips:
            self.Sizer.Add(strip, proportion=1, flag=wx.EXPAND)
        self.Layout()

    def sync_to_strips(self):
        for strip in self.strips:
            strip.quantize_width = self.quantize_width
            strip.zoom_to_window(self.time_window)
            # ordering of statements calls repaint on strip


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
