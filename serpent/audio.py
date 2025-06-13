import math
import librosa
import pyaudio
import numpy as np

import settings
import notes


def lerp(a: float, b: float, t: float) -> float:
    return t * (b - a) + a


def powerlerp(
    start_t: float,
    end_t: float,
    start_amp: float,
    end_amp: float,
    power: float,
    time: float,
) -> float:
    if end_t - start_t == 0:
        return end_amp  # protect against div by zero
    return (end_amp - start_amp) * pow(
        (time - start_t) / (end_t - start_t), power
    ) + start_amp


class Player:
    """PyAudio wrapper for objects with next()"""

    class SourceCombiner:

        def __init__(self, sources: list):
            self._sources = Player.SourceCombiner.arrayify(sources)

        def __next__(self):
            total = 0
            for source in self._sources:
                total += next(source)
            return total

        @staticmethod
        def arrayify(x):
            is_iterable = None
            try:
                iterable = iter(x)
                is_iterable = True
            except TypeError:
                is_iterable = False
            return x if is_iterable else [x]

    class Bufferer:
        """Wrap single sample generators into
        pyAudio compatible data"""

        def __init__(self, source, chunksize: int):
            self._source = source
            self._chunksize = chunksize
            self.MIN_LEVEL, self.MAX_LEVEL = -1, 1

        def __next__(self):
            samples = []
            for _ in range(self._chunksize):
                samples.append(
                    min(max(self.MIN_LEVEL, next(self._source)), self.MAX_LEVEL)
                )
            return samples

        @staticmethod
        def format_samples(samples):
            return (np.float32(np.array(samples)).tobytes(), pyaudio.paContinue)

        def callback(self, in_data, frame_count, time_info, status_flags):
            return self.format_samples(next(self))

    def __init__(
        self,
        sources: list,
        samplerate=settings.samplerate,
        chunksize=settings.chunksize,
    ):
        self._pyaudio = pyaudio.PyAudio()
        self._sources = sources
        self._combined_sources = Player.SourceCombiner(sources)
        self._bufferer = Player.Bufferer(self._combined_sources, chunksize)
        self._stream = self._pyaudio.open(
            format=pyaudio.paFloat32,
            channels=1,
            rate=samplerate,
            output=True,
            frames_per_buffer=chunksize,
            stream_callback=self._bufferer.callback,
        )


class Sampleable:
    """Base class for audio objects that can be
    randomly sampled. Not meant to be instantiated."""

    def __init__(self, samplerate=settings.samplerate):
        self.samplerate = samplerate
        self.sample_index = 0

    def get_sample_at_index(self, index: int):
        raise NotImplementedError

    def __next__(self):
        self.sample_index += 1
        return self.get_sample_at_index(self.sample_index)

    def rewind(self):
        self.sample_index = 0


# specific instruments below #


class Noise(Sampleable):

    def __init__(self, pitch=12000, amplitude: float = 1, *args, **kw):
        super().__init__(*args, **kw)
        self.pitch = pitch
        self.amplitude = amplitude

    @staticmethod
    def garble(x):
        return (x + 20) ** 3.5 % 25 / 25

    @staticmethod
    def rough_random(x):
        # run i though garble() a few times to randomize
        return Noise.garble(1 + Noise.garble(1 + Noise.garble(x)))

    def get_sample_at_index(self, index):
        # linearly interpolate between noise points
        # to avoid bad-sounding bitcrushing without interpolation
        x = (index / self.samplerate) * self.pitch
        return (
            lerp(
                self.rough_random(math.floor(x)), self.rough_random(math.ceil(x)), x % 1
            )
            * self.amplitude
        )


class Sine(Sampleable):

    def __init__(
        self, frequency=settings.concert_a_freq, amplitude: float = 1, *args, **kw
    ):
        super().__init__(*args, **kw)
        self.frequency = frequency
        self.amplitude = amplitude

    def get_sample_at_index(self, index):
        return (
            math.sin(math.tau * self.frequency * index / self.samplerate)
            * self.amplitude
        )


class Square(Sampleable):

    def __init__(
        self, frequency=settings.concert_a_freq, amplitude: float = 1, *args, **kw
    ):
        super().__init__(*args, **kw)
        self.frequency = frequency
        self.amplitude = amplitude

    def get_sample_at_index(self, index):
        return (
            1 if (self.frequency * index / self.samplerate) % 2 > 1 else 0
        ) * self.amplitude


class Saw(Sampleable):

    def __init__(
        self, frequency=settings.concert_a_freq, amplitude: float = 1, *args, **kw
    ):
        super().__init__(*args, **kw)
        self.frequency = frequency
        self.amplitude = amplitude

    def get_sample_at_index(self, index):
        return ((self.frequency * index / self.samplerate) % 1) * self.amplitude


class Harmonics(Sampleable):

    def __init__(
        self,
        harmonics: list = [1, 0.5, 0.25],
        frequency=settings.concert_a_freq,
        amplitude=1,
        normalize=True,
        *args,
        **kw
    ):
        super().__init__(*args, **kw)
        self._harmonics = harmonics
        self.frequency = frequency
        self.amplitude = amplitude
        self.normalize = normalize
        self.lut = Harmonics.generate_lut(
            harmonics, settings.harmonics_lut_resolution, self.normalize
        )

    @property
    def harmonics(self):
        return self._harmonics

    @harmonics.setter
    def harmonics(self, val):
        self._harmonics = val
        self.lut = Harmonics.generate_lut(
            val, settings.harmonics_lut_resolution, self.normalize
        )

    @staticmethod
    def generate_lut(harmnonics, resolution, normalize):
        times = np.arange(0, 1, 1 / resolution)
        samples = []
        for time in times:
            total = 0
            harmonic = 1
            for harmonic_amp in harmnonics:
                total += math.sin(math.tau * time * harmonic) * harmonic_amp
                harmonic += 1
            samples.append(total)

        if normalize:
            max_level = max(samples)
            samples = [sample / max_level for sample in samples]

        return samples

    def lut_lookup(self, time):
        """'Sine' function that looks up the table"""
        lut_index = math.floor(len(self.lut) * (time % 1))
        return self.lut[lut_index]

    def get_sample_at_index(self, index):
        return self.amplitude * self.lut_lookup(
            self.frequency * index / self.samplerate
        )


class AudioFile(Sampleable):
    def __init__(self, file, amplitude: float = 1, *args, **kw):
        super().__init__(*args, **kw)
        self.frames, _ = librosa.core.load(file, sr=self.samplerate)

    def get_sample_at_index(self, index):
        rounded = round(index)
        if rounded >= len(self.frames) or rounded < 0:
            return 0
        return self.frames[rounded]


class BassDrum(Sampleable):
    def __init__(self, amplitude: float = 1, *args, **kw):
        super().__init__(*args, **kw)
        self.harmonics = Harmonics(
            harmonics=list(np.power(np.divide(0.7, list(range(1, 20))), 4)),
            frequency=60,
        )
        self.amplitude = amplitude

    def get_sample_at_index(self, index):
        envelope = math.pow(((index / self.samplerate) * 0.6) + 1, -20)
        return envelope * self.amplitude * self.harmonics.get_sample_at_index(index)


class HiHatDrum(Sampleable):
    def __init__(self, amplitude: float = 1, *args, **kw):
        super().__init__(*args, **kw)
        self.noise = Noise(pitch=100000)
        self.amplitude = amplitude

    def get_sample_at_index(self, index):
        envelope = 0.5 * math.pow((index / self.samplerate) + 1, -40)
        return envelope * self.amplitude * self.noise.get_sample_at_index(index)


class SnareDrum(Sampleable):
    def __init__(self, amplitude: float = 1, *args, **kw):
        super().__init__(*args, **kw)
        self.noise = Noise(pitch=20000, amplitude=0.5)
        self.harmonics = Harmonics(
            harmonics=list(np.power(np.divide(0.8, list(range(1, 20))), 3)),
            frequency=125,
        )
        self.amplitude = amplitude

    def get_sample_at_index(self, index):
        envelope = np.clip(
            1.25 * math.pow((index / self.samplerate * 0.8) + 1, -40), 0, 1
        )
        return envelope * (
            self.harmonics.get_sample_at_index(index)
            + self.noise.get_sample_at_index(index)
        )


class ADSR(Sampleable):
    def __init__(
        self,
        source: Sampleable,
        attack_len: float = 0,
        decay_len: float = 0,
        release_len: float = 0.1,
        sustain_amp: float = 1,
        attack_power: float = 1,
        decay_power: float = 1,
        release_power: float = 1,
        note_length: float = 1,
        *args,
        **kw
    ):
        super().__init__(*args, **kw)
        self.source = source
        self.attack_len = attack_len
        self.decay_len = decay_len
        self.release_len = release_len
        self.sustain_amp = sustain_amp
        self.attack_power = attack_power
        self.decay_power = decay_power
        self.release_power = release_power
        self.note_length = note_length
        self.enabled = True

    def attack_envelope(self, time: float) -> float:
        """Helper function. Returns
        envelope at time without
        release (synth played
        indefinitely)"""

        envelope = 0
        # attack
        if time < self.attack_len:
            envelope = powerlerp(
                start_t=0,
                end_t=self.attack_len,
                start_amp=0,
                end_amp=1,
                power=self.attack_power,
                time=time,
            )
        # decay
        elif time < self.attack_len + self.decay_len:
            envelope = powerlerp(
                start_t=self.attack_len,
                end_t=self.attack_len + self.decay_len,
                start_amp=1,
                end_amp=self.sustain_amp,
                power=self.decay_power,
                time=time,
            )
        # sustain
        else:
            envelope = self.sustain_amp
        return envelope

    def release_envelope(self, time: float) -> float:
        envelope = powerlerp(
            start_t=self.note_length,
            end_t=self.note_length + self.release_len,
            start_amp=self.attack_envelope(
                self.note_length
            ),  # handle release before attack is finished
            end_amp=0,
            power=self.release_power,
            time=time,
        )
        return envelope

    def get_sample_at_index(self, index):
        if not self.enabled:
            return 0

        time = index / self.samplerate

        envelope = 0

        # order of if statements matter

        # attack, decay, dustain
        if time < self.note_length:
            envelope = self.attack_envelope(time)
        # release
        elif time < self.note_length + self.release_len:
            envelope = self.release_envelope(time)

        # envelope defaults to zero after release
        return envelope * self.source.get_sample_at_index(index)


class Note:
    def __init__(
        self, time: float, length: float, frequency: float = settings.concert_a_freq
    ):
        """.time and .length are in the units of beats"""
        self.time = time
        self.length = length
        self.frequency = frequency

        if self.length <= 0:
            raise ValueError("Length of Notes must be positive")

    @property
    def start(self) -> float:
        return self.time

    @property
    def end(self) -> float:
        return self.time + self.length

    def overlaps(self, other) -> bool:
        return (
            (other.start < self.start and self.start < other.end)
            or (other.start < self.end and self.end < other.end)
            or other.start == self.start
            or other.end == self.end
        )

    def contains(self, time: float) -> bool:
        return self.start < time and time < self.end

    def __lt__(self, other) -> bool:
        return self.time < other.time

    def __gt__(self, other) -> bool:
        return self.time > other.time

    def __le__(self, other) -> bool:
        return self.time <= other.time

    def __ge__(self, other) -> bool:
        return self.time >= other.time


class PitchedNote(Note):
    """Wrapper for string note frequencies with ints instead of float"""

    def __init__(self, time, length, pitch: int = settings.default_note):
        super().__init__(time, length, frequency=notes.freq_from_midi_index(pitch))
        self._pitch = pitch

    @property
    def pitch(self):
        return self._pitch

    @pitch.setter
    def pitch(self, val: int):
        self._pitch = val
        self.frequency = notes.freq_from_midi_index(val)


class Voice(Sampleable):
    def __init__(
        self,
        synth: ADSR,
        notes: list[Note],
        repeat_length: int,
        bpm: float,
        pitched: bool = False,
        amplitude: float = 1,
        *args,
        **kw
    ):
        """
        .notes is not guaranteed to
        be the same as initialized
        if accessed via property
        """

        super().__init__(*args, **kw)
        self.synth = synth
        self._notes = Voice.sort_notes(notes)
        self.repeat_length = repeat_length
        self.bpm = bpm
        self.pitched = pitched
        self.amplitude = amplitude
        self.enabled = True
        self.playing_note: Note | None = None
        self.releasing_note: Note | None = None  # remember which note to release

    @property
    def notes(self) -> list[Note]:
        return self._notes

    @notes.setter
    def notes(self, val: list[Note]):
        self._notes = Voice.sort_notes(val)
        # don't hold on to references to possibly now nonexistent notes
        self.playing_note = None
        self.releasing_note = None

    @staticmethod
    def sort_notes(notes: list[Note]) -> list[Note]:
        final = []
        for note in sorted(notes):
            # check for overlap
            for other in final:
                if note.overlaps(other):
                    raise Exception("Overlap was detected while verifying notes")
            final.append(note)
        return final

    def update_synth(self, beat_time: float):
        if (self.playing_note is not None) and (self.playing_note.contains(beat_time)):
            return  # still the same note, don't do anything
        # still slow for rests, but rests don't play anything

        # determine which note we are using
        self.playing_note = None
        for note in self._notes:
            if note.contains(beat_time):
                self.playing_note = note
                self.releasing_note = note
                break

        if self.playing_note is not None:
            self.synth.note_length = self.playing_note.length * 60 / self.bpm
            if self.pitched:
                self.synth.source.frequency = self.playing_note.frequency  # type: ignore

    def calculate_synth_index(self, beat_time: float) -> int:
        time_offset = self.releasing_note.time
        # handle wrap-around
        if self.releasing_note.time > beat_time:
            time_offset -= self.repeat_length
        return (beat_time - time_offset) * round(self.samplerate / (self.bpm / 60))

    def get_sample_at_index(self, index):
        if not self.enabled:
            return 0

        beat_time = (index * (self.bpm / 60) / self.samplerate) % self.repeat_length
        self.update_synth(beat_time)

        if self.releasing_note is None:
            return 0

        return self.amplitude * self.synth.get_sample_at_index(
            self.calculate_synth_index(beat_time)
        )


class SyncedVoices(Sampleable):
    def __init__(self, voices: list[Voice], bpm: float, *args, **kw):
        super().__init__(*args, **kw)
        self._bpm = bpm
        self._voices = voices
        self.enabled = True
        self.sync_bpm()

    @property
    def bpm(self) -> float:
        return self._bpm

    @bpm.setter
    def bpm(self, val: float):
        self._bpm = val
        self.sync_bpm()

    @property
    def voices(self) -> list[Voice]:
        return self._voices

    @voices.setter
    def voices(self, val: list[Voice]):
        self._voices = val
        self.sync_bpm()

    def sync_bpm(self):
        for voice in self._voices:
            voice.bpm = self._bpm

    def get_sample_at_index(self, index):
        if not self.enabled:
            return 0
        total = 0
        for voice in self._voices:
            total += voice.get_sample_at_index(index)
        return total
