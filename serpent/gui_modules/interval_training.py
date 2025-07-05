import random
import copy
import wx
import wx.lib.newevent
import audio
import instruments
import notes
import typing

intervals = [
    "1",
    "1#\n2b",
    "2",
    "2#\n3b",
    "3",
    "4",
    "4#\n5b",
    "5",
    "5#\n6b",
    "6",
    "6#\n7b",
    "7",
]

scales = [
    ("Major", [1, 0, 1, 0, 1, 1, 0, 1, 0, 1, 0, 1]),
    ("Minor", [1, 0, 1, 1, 0, 1, 0, 1, 1, 0, 1, 0]),
    ("Chromatic", [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]),
    ("Pentatonic", [1, 0, 1, 0, 1, 0, 0, 1, 0, 1, 0, 0]),
    ("Whole tone", [1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0]),
]

IntervalSelectEvent, EVT_INTERVAL_SELECT = wx.lib.newevent.NewEvent()


class IntervalSelector(wx.Panel):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.Sizer = wx.BoxSizer(wx.HORIZONTAL)

        BUTTON_FONT = wx.Font().MakeBold().MakeLarger().MakeLarger()
        self.buttons = [
            wx.Button(
                self,
                label=x[1],
                name=f"{x[0]}",
                size=wx.Size(40, 30),
                style=wx.BU_EXACTFIT,
            )
            for x in enumerate(intervals)
        ]

        for button in self.buttons:
            button.SetFont(BUTTON_FONT)
            self.Sizer.Add(button, proportion=1, flag=wx.EXPAND)
            button.Bind(wx.EVT_BUTTON, self.on_button)

    def on_button(self, event):
        interval = int(event.GetEventObject().Name)
        wx.PostEvent(self.Parent, IntervalSelectEvent(interval=interval))


class IntervalOptionsCheckbox(wx.Panel):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.Sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.checkboxes = [
            wx.CheckBox(self, label=x[1], name=f"{x[0]}") for x in enumerate(intervals)
        ]
        for checkbox in self.checkboxes:
            self.Sizer.Add(checkbox, proportion=1, flag=wx.CENTER)

    @property
    def choices(self):
        return [checkbox.Value for checkbox in self.checkboxes]

    @choices.setter
    def choices(self, values):
        for checkbox, value in zip(self.checkboxes, values):
            checkbox.Value = value


class ScaleSelector(wx.Panel):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.Sizer = wx.BoxSizer(wx.VERTICAL)
        self.checkbox = IntervalOptionsCheckbox(self)
        self.presets_choice = wx.Choice(self, choices=[x[0] for x in scales])
        self.Sizer.Add(self.checkbox, proportion=1, flag=wx.EXPAND)
        self.Sizer.Add(self.presets_choice, proportion=1, flag=wx.EXPAND)
        self.presets_choice.Bind(wx.EVT_CHOICE, self.on_preset_select)

    def on_preset_select(self, event):
        preset_index = self.presets_choice.GetSelection()
        if preset_index != wx.NOT_FOUND:
            scale = scales[preset_index][1]
            self.checkbox.choices = scale


class TopLabeledChoice(wx.Panel):
    def __init__(self, parent, label, choices=[], **kwargs):
        super().__init__(parent, **kwargs)
        self.Sizer = wx.BoxSizer(wx.VERTICAL)
        self.label = wx.StaticText(self, label=label)
        self.choice = wx.Choice(self, choices=choices)
        self.Sizer.Add(self.label, flag=wx.ALIGN_LEFT | wx.BOTTOM)
        self.Sizer.Add(self.choice, proportion=1, flag=wx.EXPAND)

    @property
    def Selection(self):
        return self.choice.Selection

    @Selection.setter
    def Selection(self, val: int):
        self.choice.Selection = val

    def Bind(self, event, handler, *args, **kwargs):
        self.choice.Bind(event, handler, *args, **kwargs)


class TopControls(wx.Panel):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.Sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.SetMinSize(wx.Size(0, 100))

        self.start_button = wx.Button(self, label="Start/Stop", name="start_stop")
        self.scale_selector = ScaleSelector(self)
        self.root_choice = TopLabeledChoice(
            self,
            label="Root:",
            choices=[
                "C",
                "C#Db",
                "D",
                "D#Eb",
                "E",
                "F",
                "F#Gb",
                "G",
                "G#Ab",
                "A",
                "A#Bb",
                "B",
                "Random",
            ],
        )
        self.root_choice.Selection = 12  # choice "Random"
        self.mode_choice = TopLabeledChoice(
            self,
            label="Identify:",
            choices=[
                "Scale degree (relative to root)",
                "Interval (relative to last note)",
            ],
        )
        self.mode_choice.Selection = 0
        self.init_gui()

    def init_gui(self):
        self.Sizer.Add(self.start_button, proportion=2, flag=wx.EXPAND)
        self.Sizer.Add(self.scale_selector, proportion=2, flag=wx.EXPAND)
        self.Sizer.Add(self.root_choice, proportion=1, flag=wx.EXPAND)
        self.Sizer.Add(self.mode_choice, proportion=2, flag=wx.EXPAND)


MIDDLE_C = 60


def root_convert(index: int):
    if index < 12:
        return index + MIDDLE_C
    else:
        return random.randint(MIDDLE_C, MIDDLE_C + 11)


class NoteGenerator:
    """@scale: list of bool or int, where 1 or True means the note is in the scale,
    and 0 or False means it is not.
    @mode: int, the mode of the training (0 for scale degree, 1 for interval)"""

    def __init__(self, scale: list[bool] | list[int], mode: int):
        self.choosable_notes = []
        self._scale = scale
        self.mode = mode
        self.update_choosable_notes()
        self.last_degree = 0  # root
        self.current_degree = random.choice(self.choosable_notes)

    def update_choosable_notes(self):
        self.choosable_notes = []
        for i, is_note in enumerate(self._scale):
            if is_note:
                self.choosable_notes.append(i)
        if len(self.choosable_notes) == 0:
            self.choosable_notes = [0]  # default to root if none are selected

    @property
    def scale(self):
        return self._scale

    @scale.setter
    def scale(self, val):
        self._scale = val
        self.update_choosable_notes()

    def answer(self, interval: int):
        if self.mode == 0:
            # Scale degree mode
            if interval == self.current_degree:
                self.correct()
                return True
        elif self.mode == 1:
            # Interval mode
            if interval == abs(self.current_degree - self.last_degree):
                self.correct()
                return True
        return False

    def correct(self):
        self.last_degree = self.current_degree
        self.current_degree = random.choice(
            (
                [x for x in self.choosable_notes if x != self.current_degree]
                if len(self.choosable_notes) > 1
                else self.choosable_notes
            )
        )


DEFAULT_SYNTH = audio.ADSR(
    instruments.Harmonics([1 / (x + 1) for x in range(10)]),
    attack_len=0.01,
    decay_len=2,
    sustain_amp=0.5,
    note_length=1,
)


class AudioHandler:
    """@root: int, midi index of root note"""

    def __init__(self, root: int):
        self.synth = copy.deepcopy(DEFAULT_SYNTH)
        self.player = audio.Player([self.synth])
        self.root = root

    def play_note(self, degree: int):
        self.synth.source.frequency = notes.freq_from_midi_index(self.root + degree)
        self.synth.rewind()


class IntervalTraining(wx.Panel):
    class State:
        def __init__(self, parent: "IntervalTraining"):
            self.parent: IntervalTraining = parent

        def on_interval_select(self, event: wx.Event):
            raise NotImplementedError

        def on_start_stop(self, event: wx.Event):
            raise NotImplementedError

    class Stopped(State):
        def on_interval_select(self, event: wx.Event):
            pass  # do nothing

        def on_start_stop(self, event: wx.Event):
            self.parent.update_all_properties()
            self.parent.state = IntervalTraining.PlayingRootNote(self.parent)

    class PlayingRootNote(State):
        def __init__(self, parent: "IntervalTraining"):
            super().__init__(parent)
            self.parent.audio_handler.play_note(0)  # root

        def on_interval_select(self, event: wx.Event):
            self.parent.state = IntervalTraining.Running(self.parent)

        def on_start_stop(self, event: wx.Event):
            self.parent.state = IntervalTraining.Stopped(self.parent)

    class Running(State):
        def on_interval_select(self, event: wx.Event):
            self.parent.note_generator.answer(event.interval)
            self.parent.audio_handler.play_note(
                self.parent.note_generator.current_degree
            )

        def on_start_stop(self, event: wx.Event):
            self.parent.state = IntervalTraining.Stopped(self.parent)

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)

        self.title = "Interval Training"
        self.Sizer = wx.BoxSizer(wx.VERTICAL)

        self.interval_selector = IntervalSelector(self)
        self.top_controls = TopControls(self)
        self.note_generator: NoteGenerator = NoteGenerator(
            scale=self.top_controls.scale_selector.checkbox.choices,
            mode=self.top_controls.mode_choice.Selection,
        )

        self.audio_handler: AudioHandler = AudioHandler(
            root=root_convert(self.top_controls.root_choice.Selection)
        )
        self.state: IntervalTraining.State = IntervalTraining.Stopped(self)

        self.Sizer.Add(self.top_controls, proportion=0, flag=wx.EXPAND)
        self.Sizer.Add(self.interval_selector, proportion=1, flag=wx.EXPAND)

        self.Bind(EVT_INTERVAL_SELECT, self.on_interval_select)
        self.Bind(wx.EVT_BUTTON, self.on_start_stop)

    def update_scale(self) -> None:
        self.note_generator.scale = self.top_controls.scale_selector.checkbox.choices

    def update_root(self) -> None:
        self.audio_handler.root = root_convert(self.top_controls.root_choice.Selection)

    def update_mode(self) -> None:
        self.note_generator.mode = self.top_controls.mode_choice.Selection

    def update_all_properties(self) -> None:
        self.update_scale()
        self.update_root()
        self.update_mode()

    def on_interval_select(self, event: wx.Event) -> None:
        self.state.on_interval_select(event)

    def on_start_stop(self, event: wx.Event) -> None:
        self.state.on_start_stop(event)
