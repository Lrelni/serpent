import copy
import math
import os
import typing

import wx
import wx.lib.intctrl
import wx.lib.newevent
import wx.lib.scrolledpanel

import audio
import instruments
import notes
import settings


def map_range(from1, from2, to1, to2, val):
    return ((to2 - to1) / (from2 - from1)) * (val - from1) + to1


class AboutBox(wx.Dialog):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.panel = wx.Panel(self)
        self.panel.Sizer = wx.BoxSizer(wx.VERTICAL)
        self.panel.Sizer.Add(
            wx.StaticText(self.panel, label="Serpent v" + settings.version)
        )

        samples_license = (
            "You can find the drum sounds used online at"
            "\nfreesound.org/people/Theriavirra/packs/16665/"
        )
        self.panel.Sizer.Add(wx.StaticText(self.panel, label=samples_license))


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


NoteStripUpdateEvent, EVT_NOTE_STRIP_UPDATE = wx.lib.newevent.NewEvent()
NoteStripTimeScrollEvent, EVT_NOTE_STRIP_TIME_SCROLL = wx.lib.newevent.NewEvent()


class NoteInputStrip(wx.Panel):

    def __init__(self, *args, **kw):
        # constants stored here because wx.App needs to be inited first
        self.DEFAULT_LEFT_TIME, self.DEFAULT_RIGHT_TIME = 0, 4
        self.DEFAULT_QUANTIZE_WIDTH = 1 / 4
        self.FLOATING_POINT_END_TOLERANCE = 0.01
        self.DEFAULT_REPEAT_LENGTH = 4
        self.ZOOM_FACTOR_IN, self.ZOOM_FACTOR_OUT = 0.9, 1 / 0.9
        self.DEFAULT_NOTES_BRUSH = wx.Brush(wx.Colour(60, 60, 60))
        self.DEFAULT_NOTES_PEN = wx.Pen("black", width=1)
        self.TENTATIVE_NOTES_BRUSH = wx.Brush(
            wx.Colour(20, 20, 20), style=wx.BRUSHSTYLE_FDIAGONAL_HATCH
        )
        self.TENTATIVE_NOTES_PEN = wx.TRANSPARENT_PEN
        self.BACKGROUND_BRUSH = wx.Brush(wx.Colour(190, 190, 190))
        self.BACKGROUND_PEN = wx.Pen(wx.Colour(140, 140, 140, 64), width=2)
        self.NEGATIVE_BRUSH = wx.Brush(
            wx.Colour(120, 120, 120), style=wx.BRUSHSTYLE_CROSSDIAG_HATCH
        )
        self.NEGATIVE_PEN = self.BACKGROUND_PEN
        self.QUANTIZE_LINES_PEN = wx.Pen(wx.Colour(140, 140, 140, 40), width=1)
        self.BEAT_LINES_PEN = wx.Pen(wx.Colour(130, 130, 130, 90))
        self.TEXT_FONT = wx.Font(wx.FontInfo(8))
        self.TEXT_COLOR = wx.Colour(130, 130, 130, 200)

        super().__init__(*args, **kw, style=wx.FULL_REPAINT_ON_RESIZE)
        self._notes: list[audio.Note] = []
        self.time_window = (self.DEFAULT_LEFT_TIME, self.DEFAULT_RIGHT_TIME)
        self.quantize_width = self.DEFAULT_QUANTIZE_WIDTH
        self._repeat_length = self.DEFAULT_REPEAT_LENGTH
        self.tentative_note: audio.Note | None = None

        self.Bind(wx.EVT_PAINT, self.on_paint)
        self.Bind(wx.EVT_LEFT_DOWN, self.on_left_down)
        self.Bind(wx.EVT_LEFT_UP, self.on_left_up)
        self.Bind(wx.EVT_RIGHT_DOWN, self.on_right_down)
        self.Bind(wx.EVT_MOUSEWHEEL, self.on_mouse_wheel)
        self.Bind(wx.EVT_MOTION, self.on_mouse_move)

        self.SetBackgroundStyle(wx.BG_STYLE_PAINT)

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
        return self.quantize_width * math.floor(time / self.quantize_width)

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
            x = int(self.time_to_x(time))
            dc.DrawLine(
                x1=x,
                y1=0,
                x2=x,
                y2=self.ClientSize[1],
            )
            time += self.quantize_width

    def draw_beat_lines(self, dc: wx.PaintDC):
        dc.Pen = self.BEAT_LINES_PEN
        dc.Font = self.TEXT_FONT
        dc.TextForeground = self.TEXT_COLOR
        time = max(0, math.ceil(self.time_window[0]))
        while time < self.time_window[1]:
            x_location = int(self.time_to_x(time))
            dc.DrawLine(
                x1=x_location,
                y1=0,
                x2=x_location,
                y2=self.ClientSize[1],
            )
            dc.DrawText(
                str(time + 1),  # from zero-indexed to 1-indexed notation
                x_location + 2,
                self.ClientSize[1] - self.TEXT_FONT.PixelSize.y,
            )
            time += 1

    def draw_background(self, dc: wx.PaintDC):
        dc.Brush = self.BACKGROUND_BRUSH
        dc.Pen = self.BACKGROUND_PEN
        dc.DrawRectangle(x=0, y=0, width=self.ClientSize[0], height=self.ClientSize[1])

        dc.Brush = self.NEGATIVE_BRUSH
        dc.Pen = self.NEGATIVE_PEN

        if self.time_window[0] < 0:
            dc.DrawRectangle(
                x=0, y=0, width=int(self.time_to_x(0)), height=self.ClientSize[1]
            )

        if self.time_window[1] > self._repeat_length:
            dc.DrawRectangle(
                wx.Rect(
                    wx.Point(int(self.time_to_x(self._repeat_length)), 0),
                    wx.Point(self.ClientSize[0], self.ClientSize[1]),
                )
            )

    def on_paint(self, event):
        dc = wx.BufferedPaintDC(self)
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
        self.draw_beat_lines(dc)

    def update_contents(self):
        self.Refresh()
        self.Update()

    def zoom_to_time_window(self, window: tuple[float, float]):
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

    @property
    def repeat_length(self) -> int:
        return self._repeat_length

    @repeat_length.setter
    def repeat_length(self, val: int):
        self._repeat_length = val
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

    def event(self):
        wx.PostEvent(self.Parent, NoteStripUpdateEvent())

    def add_note(self, note: audio.Note):
        """May not add notes if there is overlap"""
        for okay_note in self._notes:
            if okay_note.overlaps(note):
                print("Warning: note not added because of overlap")
                return
        self._notes.append(copy.copy(note))
        self.event()

    def tentative_set_beginning(self, x: float):
        if self.x_to_time(x) < 0:
            return
        self.tentative_note = audio.Note(
            time=self.quantize(self.x_to_time(x)),
            length=max(
                0.01, self.quantize_width * (1 - self.FLOATING_POINT_END_TOLERANCE)
            ),
        )

    def tentative_set_end(self, x: float):
        if self.tentative_note is None:
            return  # don't set len if it didn't already exist
        # add .quantize_length to make note cover mouse
        end_time = (
            self.quantize_width
            + self.quantize(self.x_to_time(x))
            - (self.FLOATING_POINT_END_TOLERANCE * self.quantize_width)
        )

        length = max(
            end_time - self.tentative_note.time,
            self.quantize_width
            - (self.FLOATING_POINT_END_TOLERANCE * self.quantize_width),
        )

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
        self.last_position = wx.GetMousePosition()

    def on_right_down(self, event: wx.MouseEvent):
        note_index = self.note_index_at(self.x_to_time(event.Position[0]))
        if note_index is not None:
            self._notes.pop(note_index)
        self.event()
        self.update_contents()

    def pan_time_window(self, time_amount: float):
        new_window = (
            self.time_window[0] + time_amount,
            self.time_window[1] + time_amount,
        )
        self.zoom_to_time_window(new_window)
        wx.PostEvent(self.Parent, NoteStripTimeScrollEvent())

    def zoom_time_by_factor(self, factor: float):
        window_center = (self.time_window[0] + self.time_window[1]) / 2
        new_window = (
            factor * (self.time_window[0] - window_center) + window_center,
            factor * (self.time_window[1] - window_center) + window_center,
        )
        self.zoom_to_time_window(new_window)

    def on_mouse_wheel(self, event: wx.MouseEvent):
        self.zoom_time_by_factor(
            self.ZOOM_FACTOR_IN if event.WheelRotation > 0 else self.ZOOM_FACTOR_OUT
        )
        wx.PostEvent(self.Parent, NoteStripTimeScrollEvent())


class PitchedNoteInputStrip(NoteInputStrip):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.DEFAULT_PITCH_WINDOW_LOWER, self.DEFAULT_PITCH_WINDOW_HIGHER = 59, 72
        self.PITCH_ZOOM_IN, self.PITCH_ZOOM_OUT = 1, -1
        self.PITCH_LINES_PEN = self.BEAT_LINES_PEN

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
        text_location_x = int(max(0, self.time_to_x(0))) + 2
        dc.Font = self.TEXT_FONT
        dc.TextForeground = self.TEXT_COLOR

        pitch = max(self.pitch_window[0], 0)
        while pitch <= self.pitch_window[1]:
            dc.DrawLine(
                x1=0,
                y1=int(self.pitch_to_y(pitch)),
                x2=self.ClientSize[0],  # width
                y2=int(self.pitch_to_y(pitch)),
            )
            dc.DrawText(
                notes.str_from_midi_index(pitch),
                x=text_location_x,
                y=int(self.pitch_to_y(pitch)),
            )
            pitch += 1

    # inherit .draw_background

    def on_paint(self, event):
        self.pitch_width_y_update()
        dc = wx.BufferedPaintDC(self)
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
        self.draw_beat_lines(dc)

    # inherit .update_contents

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

    def zoom_to_windows(
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
        if self.x_to_time(x) < 0:
            return
        self.tentative_note = audio.PitchedNote(
            time=self.quantize(self.x_to_time(x)),
            length=max(
                0.01, self.quantize_width * (1 - self.FLOATING_POINT_END_TOLERANCE)
            ),
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
        wx.PostEvent(self.Parent, NoteStripTimeScrollEvent())


VoiceEditorDestroyEvent, EVT_VOICE_EDITOR_DESTROY = wx.lib.newevent.NewEvent()


class VoiceEditor(wx.Panel):
    """Note: takes ownership of voice given to this control.
    .voice should not be changed once given."""

    def __init__(self, voice: audio.Voice, name: str = "Unnamed Voice", *args, **kw):  # type: ignore
        super().__init__(*args, **kw)
        self.DEFAULT_QUANTIZE_TOP, self.DEFAULT_QUANTIZE_BOTTOM = 1, 2
        PLACEHOLDER_REPEAT_LENGTH = 4

        self.name = name
        self._voice = voice

        self.close_button = wx.Button(
            self, label="x", name="close_button", size=wx.Size(30, 30)
        )

        self.name_label = wx.StaticText(self, label=name)

        self.quantize_top_field = wx.lib.intctrl.IntCtrl(
            self,
            value=self.DEFAULT_QUANTIZE_TOP,
            name="quantize_top_field",
            size=wx.Size(50, 30),
            min=1,
        )
        self.quantize_bottom_field = wx.lib.intctrl.IntCtrl(
            self,
            value=self.DEFAULT_QUANTIZE_BOTTOM,
            name="quantize_top_field",
            size=wx.Size(50, 30),
            min=1,
        )

        self.repeat_length_field = wx.lib.intctrl.IntCtrl(
            self, value=PLACEHOLDER_REPEAT_LENGTH, min=1, size=wx.Size(40, 30)
        )

        self.amplitude_slider = wx.Slider(
            self,
            value=100,
            minValue=0,
            maxValue=100,
            name="amplitude_slider",
            size=wx.Size(200, 30),
        )

        self.time_window_left_field = wx.lib.intctrl.IntCtrl(
            self, value=1, size=wx.Size(40, 30)
        )
        self.time_window_right_field = wx.lib.intctrl.IntCtrl(
            self, value=4, size=wx.Size(40, 30)
        )

        self.input_strip = None

        if voice.pitched:
            self.input_strip = PitchedNoteInputStrip(self)
        else:
            self.input_strip = NoteInputStrip(self)

        self.init_gui()
        self.init_bindings()
        self.sync_all()

    def init_gui(self):
        self.vbox = wx.BoxSizer(wx.VERTICAL)
        self.hbox = wx.BoxSizer(wx.HORIZONTAL)
        self.vbox.Add(self.hbox, proportion=0, flag=wx.EXPAND, border=1)
        self.hbox.Add(self.close_button)
        self.hbox.Add(wx.Size(15, 0))
        self.hbox.Add(self.name_label, flag=wx.CENTER)
        self.hbox.Add(wx.Size(15, 0))
        self.hbox.Add(wx.StaticText(self, label="Quantize: "), flag=wx.CENTER)
        self.hbox.Add(self.quantize_top_field)
        self.hbox.Add(wx.StaticText(self, label="/"), flag=wx.CENTER)
        self.hbox.Add(self.quantize_bottom_field)
        self.hbox.Add(wx.Size(15, 0))
        self.hbox.Add(wx.StaticText(self, label="Repeat at: "), flag=wx.CENTER)
        self.hbox.Add(self.repeat_length_field)
        self.hbox.Add(wx.Size(15, 0))
        self.hbox.Add(wx.StaticText(self, label="Amplitude: "), flag=wx.CENTER)
        self.hbox.Add(wx.Size(15, 0))
        self.hbox.Add(self.amplitude_slider, flag=wx.CENTER)
        self.hbox.Add(wx.Size(15, 0))
        self.hbox.Add(wx.StaticText(self, label="Time window: "), flag=wx.CENTER)
        self.hbox.Add(self.time_window_left_field)
        self.hbox.Add(wx.StaticText(self, label=" to "), flag=wx.CENTER)
        self.hbox.Add(self.time_window_right_field)
        self.vbox.Add(self.input_strip, proportion=1, flag=wx.EXPAND)
        self.Sizer = self.vbox

    def init_bindings(self):
        do_nothing = lambda event: None
        self.Bind(wx.EVT_BUTTON, self.on_button)
        self.Bind(wx.EVT_TEXT, self.on_text)
        self.Bind(EVT_NOTE_STRIP_UPDATE, self.on_notes)
        self.Bind(wx.EVT_SCROLL, self.on_scroll)
        self.Bind(EVT_NOTE_STRIP_TIME_SCROLL, self.update_time_window_from_strip)
        self.quantize_top_field.Bind(wx.EVT_CONTEXT_MENU, do_nothing)
        self.quantize_bottom_field.Bind(wx.EVT_CONTEXT_MENU, do_nothing)
        self.repeat_length_field.Bind(wx.EVT_CONTEXT_MENU, do_nothing)

    def on_button(self, event: wx.Event):
        if event.EventObject.Name == self.close_button.Name:
            self.on_close()

    def on_text(self, event: wx.Event):
        self.update_quantize()
        self.update_repeat_length()
        self.update_amplitude()
        self.update_time_window()

    def on_scroll(self, event: wx.ScrollEvent):
        self.update_amplitude()

    def on_notes(self, event: wx.Event):
        self.update_voice_notes()

    def on_close(self):
        event = VoiceEditorDestroyEvent(obj=self)
        wx.PostEvent(self.Parent.Parent, event)

    def update_quantize(self):
        if self.quantize_top_field.Value < 1 or self.quantize_bottom_field.Value < 1:
            return
        self.input_strip.quantize_width = (
            self.quantize_top_field.Value / self.quantize_bottom_field.Value
        )
        self.input_strip.update_contents()

    def update_repeat_length(self):
        if self.repeat_length_field.Value <= 0:
            return
        self.input_strip.repeat_length = self.repeat_length_field.Value
        self._voice.repeat_length = self.repeat_length_field.Value

    def update_amplitude(self):
        self._voice.amplitude = self.amplitude_slider.Value / self.amplitude_slider.Max

    def update_time_window(self):
        if self.time_window_left_field.Value > self.time_window_right_field.Value:
            # swap values
            old_left = self.time_window_left_field.Value
            self.time_window_left_field.ChangeValue(self.time_window_right_field.Value)

            self.time_window_right_field.ChangeValue(old_left)
        elif self.time_window_left_field.Value == self.time_window_right_field.Value:
            # offset by 1 beat to keep window existent
            self.time_window_right_field.ChangeValue(
                self.time_window_right_field.Value + 1
            )

        new_window = (
            self.time_window_left_field.Value
            - 1,  # convert between notational time and time used by NoteInputStrip
            self.time_window_right_field.Value,
        )
        self.input_strip.zoom_to_time_window(new_window)

    def update_time_window_from_strip(self, event):

        self.time_window_left_field.ChangeValue(
            math.ceil(self.input_strip.time_window[0]) + 1
        )  # convert time

        self.time_window_right_field.ChangeValue(
            math.floor(self.input_strip.time_window[1])
        )

    def update_voice_notes(self):
        self._voice.notes = copy.deepcopy(self.input_strip.notes)

    def sync_all(self):
        self.update_quantize()
        self.update_repeat_length()
        self.update_amplitude()
        self.update_time_window()
        self.update_voice_notes()


class VoiceEntry:
    """.voice should not be changed once initialized"""

    def __init__(self, voice: audio.Voice, name: str):
        self._voice = voice
        self._name = name

    @property
    def voice(self) -> audio.Voice:
        return copy.deepcopy(self._voice)

    @property
    def name(self) -> str:
        return self._name


# helper method
def list_files(path):
    return [os.path.join(path, file) for file in os.listdir(path)]


DEFAULT_VOICE_SET = [
    VoiceEntry(
        audio.Voice(audio.ADSR(instruments.Harmonics()), [], 4, 4, True),
        "Synthesizer 1",
    ),
    VoiceEntry(
        audio.Voice(
            audio.ADSR(
                instruments.RoundRobin(list_files("samples/ride_a")),
                release_len=2,
            ),
            [],
            4,
            4,
        ),
        "Ride cymbal A",
    ),
    VoiceEntry(
        audio.Voice(
            audio.ADSR(
                instruments.RoundRobin(list_files("samples/ride_b")),
                release_len=2,
            ),
            [],
            4,
            4,
        ),
        "Ride cymbal B",
    ),
    VoiceEntry(
        audio.Voice(
            audio.ADSR(
                instruments.RoundRobin(list_files("samples/hihat")),
            ),
            [],
            4,
            4,
        ),
        "Hi-hat",
    ),
    VoiceEntry(
        audio.Voice(
            audio.ADSR(
                instruments.RoundRobin(list_files("samples/snare")),
            ),
            [],
            4,
            4,
        ),
        "Snare drum",
    ),
    VoiceEntry(
        audio.Voice(
            audio.ADSR(
                instruments.RoundRobin(list_files("samples/tom")),
            ),
            [],
            4,
            4,
        ),
        "Toms",
    ),
    VoiceEntry(
        audio.Voice(
            audio.ADSR(
                instruments.RoundRobin(list_files("samples/crash")), release_len=2.5
            ),
            [],
            4,
            4,
        ),
        "Crash cymbals",
    ),
    VoiceEntry(
        audio.Voice(
            audio.ADSR(
                instruments.RoundRobin(list_files("samples/drumstick")),
            ),
            [],
            4,
            4,
        ),
        "Drumstick",
    ),
]


class BackingTrack(wx.Panel):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.title = "Backing Track"
        self.SIZE_NOTE_STRIP, self.SIZE_PITCHED_NOTE_STRIP = 100, 400
        self.DEFAULT_BPM = 130
        self.BPM_MIN, self.BPM_MAX = 1, 1000
        self.BPM_INITIAL = 130
        self.BPM_INCREMENT = 5

        self.new_voice_dropdown = wx.Choice(
            self, name="new_voice_dropdown", choices=[x.name for x in DEFAULT_VOICE_SET]
        )
        self.new_voice_dropdown.Selection = 0
        self.new_voice_button = wx.Button(
            self, label="+", name="new_voice_button", size=wx.Size(30, 30)
        )
        self.bpm_field = wx.SpinCtrl(
            self,
            min=self.BPM_MIN,
            max=self.BPM_MAX,
            initial=self.BPM_INITIAL,
            name="bpm_control",
            size=wx.Size(150, 30),
        )
        self.play_button = wx.Button(self, label="Play/Stop", name="play_button")
        self.voices_window = wx.lib.scrolledpanel.ScrolledPanel(
            self,
            name="voices_window",
        )

        self._voice_editors = []
        self.selected_voice_index = 0

        self.synced_voices = audio.SyncedVoices(voices=[], bpm=self.DEFAULT_BPM)
        self.player = audio.Player(self.synced_voices)

        self.init_gui()
        self.init_bindings()

    def init_gui(self):
        self.Sizer = wx.BoxSizer(wx.VERTICAL)
        self.hbox = wx.BoxSizer(wx.HORIZONTAL)
        self.Sizer.Add(self.voices_window, proportion=1, flag=wx.EXPAND)
        self.Sizer.Add(self.hbox)
        self.hbox.Add(self.new_voice_dropdown)
        self.hbox.Add(self.new_voice_button)
        self.hbox.Add(50, 0)
        self.hbox.Add(wx.StaticText(self, label="BPM:"), flag=wx.CENTER)
        self.hbox.Add(self.bpm_field)
        self.hbox.Add(50, 0)
        self.hbox.Add(self.play_button, proportion=1)
        self.voices_window.Sizer = wx.BoxSizer(wx.VERTICAL)
        self.voices_window.SetupScrolling()

    def init_bindings(self):
        self.Bind(EVT_VOICE_EDITOR_DESTROY, self.on_voice_destroy_event)
        self.Bind(wx.EVT_BUTTON, self.on_button)
        self.Bind(wx.EVT_SPINCTRL, self.on_spin_ctrl)

    def add_new_voice(self, index: int):
        new_voice = DEFAULT_VOICE_SET[index].voice
        new_voice_editor = VoiceEditor(
            new_voice, DEFAULT_VOICE_SET[index].name, self.voices_window
        )
        new_voice_editor.MinSize = wx.Size(
            0,
            self.SIZE_PITCHED_NOTE_STRIP if new_voice.pitched else self.SIZE_NOTE_STRIP,
        )
        self.voices_window.Sizer.Add(
            new_voice_editor, proportion=0, flag=wx.EXPAND | wx.ALL, border=1
        )
        self.voices_window.Layout()

        self._voice_editors.append(new_voice_editor)
        self.synced_voices.voices.append(new_voice)
        self.synced_voices.sync_bpm()

    def on_voice_destroy_event(self, event: wx.Event):
        self._voice_editors.remove(event.obj)
        self.synced_voices.voices.remove(event.obj._voice)
        event.obj.Destroy()
        self.voices_window.Layout()

    def on_button(self, event: wx.Event):
        if event.EventObject == self.new_voice_button:
            self.new_voice_pressed()
        elif event.EventObject == self.play_button:
            self.play_button_pressed()

    def on_spin_ctrl(self, event: wx.Event):
        self.update_bpm()

    def new_voice_pressed(self):
        if self.new_voice_dropdown.Selection == wx.NOT_FOUND:
            return
        self.add_new_voice(self.new_voice_dropdown.Selection)

    def play_button_pressed(self):
        self.synced_voices.enabled = not self.synced_voices.enabled
        self.synced_voices.rewind()

    def update_bpm(self):
        self.synced_voices.bpm = self.bpm_field.Value
