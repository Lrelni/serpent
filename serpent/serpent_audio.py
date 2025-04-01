import time
import math
from abc import ABC, abstractmethod
from copy import deepcopy

import pyaudio
import numpy as np

import settings


def _index_from_str(string):
    """
    Convert from a note name to a note index (internal function)
    format:
    octave is required.
    <note-letter> <accidental> <octave>
    <note-letter> ::= A | B | C | D | E | F | G | a | b | c | d | e | f | g
    <accidental> ::= # | b | <empty string>
    <octave> ::= 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8"""

    # assuming 4th octave here.
    convert = {
        "C": -9,
        "D": -7,
        "E": -5,
        "F": -4,
        "G": -2,
        "A": 0,
        "B": 2,
    }

    acc_offset = {
        "#": 1,
        "b": -1,
        "": 0
    }

    note_letter = string[0]
    #            A#4                                A4 (accidental="")
    accidental = string[1] if len(string) == 3 else ""
    #            A#4                                A4 (accidental="")
    octave = int(string[2] if len(string) == 3 else string[1])

    octave_offset = 12 * (octave - 4)
    return convert[note_letter] + acc_offset[accidental] + octave_offset


def _freq_from_index(index):
    """Convert from an index to a frequency with equal temperament tuning."""
    return settings.a_freq * math.pow(2, index / 12)


def freq_from_str(string):
    """Convert from a note name to a frequency in Hz"""
    return _freq_from_index(_index_from_str(string))


def freqs_from_strs(strings):
    """Wrap freq_from_str in map() to allow array inputs"""
    return list(map(freq_from_str, strings))


def lerp(a, b, t):
    """Linear interpolation between a and b with t as the parameter"""
    return t*(b-a)+a


class Chord:
    """Storage class for chords. 
    freqs: list of frequencies in the chord.
    length: length of the chord in beats.
    (length of beats in time is determined
    by other classes)"""

    def __init__(self, freqs, length):
        self._freqs = freqs
        self._length = length

    @property
    def freqs(self):
        return self._freqs

    @property
    def length(self):
        return self._length

    def __len__(self):
        return self._length


class Oscillator(ABC):
    """Base class for audio sources. Comes with freq and amp variables"""

    def __init__(self, freq=440, amp=1, rate=settings.rate):
        self._freq = freq
        self._amp = amp
        self._rate = rate
        self.i = 0
        self.is_started = True

    @property
    def freq(self):
        return self._freq

    @freq.setter
    def freq(self, val):
        self._freq = np.clip(val, 0, np.inf)

    @property
    def rate(self):
        return self._rate

    @rate.setter
    def rate(self, val):
        self._rate = np.clip(val, 0, np.inf)

    @property
    def amp(self):
        return self._amp

    @amp.setter
    def amp(self, val):
        self._amp = np.clip(val, 0, 1)

    def start(self):
        if not self.is_started:
            self.is_started = True
            self.i = 0

    def stop(self):
        if self.is_started:
            self.is_started = False

    def toggle(self):
        self.stop() if self.is_started else self.start()

    def trigger(self):
        self.i = 0

    def __iter__(self):
        return self

    def __next__(self):
        if self.is_started:
            self.i += 1
        return self.get_sample(self.i)

    @abstractmethod
    def get_raw(self, i):
        pass

    def get_sample(self, i):
        return self.get_raw(i) * self.amp if self.is_started else 0


class OscAdder(Oscillator):
    """Add multiple Oscillators together inside of one source"""

    def __init__(self, sources, *args, **kw):
        super().__init__(*args, **kw)
        self._sources = sources
        self._n = len(sources)

    @property
    def sources(self):
        return self._sources

    @sources.setter
    def sources(self, val):
        self._sources = val
        self._n = len(val)

    @property
    def n(self):
        return self._n

    def start(self):
        super().start()
        [x.start() for x in self._sources]

    def stop(self):
        super().stop()
        [x.stop() for x in self._sources]

    def __next__(self):
        if self.is_started:
            return self.amp * np.sum(list(map(lambda x: next(x), self._sources)))
        else:
            return 0

    def get_raw(self, i):
        return np.sum(list(map(lambda x: x.get_sample(i), self._sources)))


class PolyOscillator(Oscillator):
    """Wrapper for monophonic instruments that allows them to play polyphonically.
    nvoices: number of voices.
    osc: a subclass of Oscillator
    freq: a list instead of a scalar."""

    def __init__(self, nvoices=8, osc=None, *args, **kw):
        super().__init__(*args, **kw)

        self._nvoices = nvoices
        # osc: Oscillator object (to be used as a template)
        # oscs: list of Oscillator 
        self._osc = osc
        self._oscs = None
        self.update_oscs()
        self.update_freqs()

    def update_oscs(self):
        self._oscs = []
        for i in range(self._nvoices):
            self._oscs.append(deepcopy(self._osc))

    def update_freqs(self):
        i = 0
        for osc in self._oscs:
            osc.freq = 0 if i >= len(self._freq) else self._freq[i]
            i += 1

    @property
    def nvoices(self):
        return self._nvoices

    @nvoices.setter
    def nvoices(self, val):
        self._nvoices = val
        self.update_oscs()
        self.update_freqs()

    @property
    def osc(self):
        return self._osc
    
    @osc.setter
    def osc(self, val):
        self._osc = val
        self.update_oscs()
        self.update_freqs()

    @property
    def freq(self):
        return self._freq

    # setter freq
    @freq.setter
    def freq(self, val):
        self._freq = val
        self.update_freqs()

    # get_raw
    def get_raw(self, i):
        total = 0
        for osc in self._oscs:
            total += osc.get_raw(i)
        return total


class Bufferer:
    """Wrap single sample generators into pyAudio compatible data"""

    def __init__(self, source, frames_per_buffer):
        self._source = source
        self._frames_per_buffer = frames_per_buffer
        self._frange = range(frames_per_buffer)

    @property
    def source(self):
        return self._source

    @source.setter
    def source(self, val):
        self._source = val

    @property
    def frames_per_buffer(self):
        return self._frames_per_buffer

    @frames_per_buffer.setter
    def frames_per_buffer(self, val):
        self._frames_per_buffer = val
        self._frange = range(val)

    def step(self):
        samples = []
        for _ in range(self._frames_per_buffer):
            samples.append(next(self._source))
        return samples

    @staticmethod
    def format_samples(samples):
        return (np.float32(np.array(samples)).tobytes(), pyaudio.paContinue)

    def get_samples(self, in_data, frame_count, time_info, status_flags):
        # used as callback for non-blocking audio
        return self.format_samples(self.step())


class SineOscillator(Oscillator):
    """Simple sine wave oscillator."""

    def get_raw(self, i):
        return math.sin(np.pi * 2 * self._freq * i / self._rate)


class HarmonicsOscillator(Oscillator):
    """Add a bunch of sine wave harmonics together to get a more complex sound."""

    def __init__(self, harmonics=[1, 0.5, 0.33, 0.25, 0.2], *args, **kw):
        super().__init__(*args, **kw)
        self._harmonics = harmonics

    @property
    def harmonics(self):
        return self._harmonics

    @harmonics.setter
    def harmonics(self, val):
        self._harmonics = val

    def get_raw(self, i):
        mult = np.pi * 2 * self._freq * i / self._rate
        final = 0
        for j in range(len(self._harmonics)):
            final += self._harmonics[j] * math.sin(mult * (1+j))
        return final


class Metronome(Oscillator):
    """Simple metronome with grouping support."""

    def __init__(self, grouping=4, *args, **kw):
        super().__init__(*args, **kw)
        self.grouping = grouping

    # the freq variable is now in bpm.
    def get_raw(self, i):
        t = i / self.rate
        bps = self.freq / 60
        # see https://www.desmos.com/calculator/guduxdwwvv for a visual of the modulating function
        return math.pow(np.clip(1 - ((t * bps) % 1) - (0.3 if ((t * bps) % self.grouping) >= 1 else 0), 0, 1), 4) *\
            math.sin(np.pi * 2 * 1000 * t)  # modulate a sine wave


class MetronomeBeep(Oscillator):
    """Just like Metronome, but only goes once. 
    MetronomeBeep.trigger() must be called to reset."""

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)

    # the freq variable is now in bpm.
    def get_raw(self, i):
        t = i / self.rate
        bps = self.freq / 60
        # see https://www.desmos.com/calculator/guduxdwwvv for a visual of the modulating function
        return math.pow(np.clip(1 - (t * bps), 0, 1), 4) *\
            math.sin(np.pi * 2 * 1000 * t)  # modulate a sine wave


class Noise(Oscillator):
    """A noise function that can be played with lower pitch if needed.
    Mainly used as building blocks for other Oscillators."""

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.quantize = 2

    def rand_round(self, i):
        return (i + 20) ** 3.5 % 25 / 25

    def rand_unsmooth(self, i):
        return self.rand_round(1 + self.rand_round(1 + self.rand_round(i)))

    def noise(self, i):
        return lerp(self.rand_unsmooth(math.floor(i)), self.rand_unsmooth(math.ceil(i)), i % 1)

    def get_raw(self, i):
        return self.noise(i * self.freq)


class BassDrum(Oscillator):
    """Bass drum sound"""

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)

        self.harmonics_osc = HarmonicsOscillator(harmonics=list(
            np.pow(np.divide(1, list(range(1, 20))), 3)), freq=60)
        self.harmonics_osc.harmonics[0] = 1.5

    def get_raw(self, i):
        t = i / self.rate
        return math.pow((t * 0.6) + 1, -20) * self.harmonics_osc.get_raw(i)


class HiHatDrum(Oscillator):
    """Hihat cymbal sound from Noise oscillator"""

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.noise = Noise()

    def get_raw(self, i):
        t = i / self.rate
        return 0.5 * math.pow((t) + 1, -40) * self.noise.get_raw(i)


class SnareDrum(Oscillator):
    """Snare drum sound"""

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.harmonics_osc = HarmonicsOscillator(harmonics=list(
            np.pow(np.divide(1, list(range(1, 20))), 3)), freq=125)
        self.harmonics_osc.harmonics[0] = 2
        self.harmonics_osc.harmonics[2] *= 2
        self.noise = Noise()

    def get_raw(self, i):
        t = i / self.rate
        return 1.3 * math.pow((t * 0.8) + 1, -40) * \
            (self.harmonics_osc.get_raw(i) + 0.07 * self.noise.get_raw(i))


class BackingTrack(Oscillator):
    """Combine drums, a beat, and chords into a single
    Oscillator that plays a backing track.
    drums: list of Oscillators to use as drums
    beat: list< drumbeat > where drumbeat := list< 1 | 0 >
    freq: BPM of the backing track.
    amp: volume of the backing track
    chords: list< chord >
    where chord := (list<frequency>, length in beats)"""

    def __init__(self, drums, beat, chords, *args, **kw):

        super().__init__(*args, **kw)
        self._drums = drums
        self._beat = beat
        self._accum = self.accumulate_beats(beat)
        self._chords = chords
        self._poly = PolyOscillator(SineOscillator)

        self.validate()

    @property
    def drums(self):
        return self._drums

    @drums.setter
    def drums(self, val):
        self._drums = val
        self.validate()

    @property
    def beat(self):
        return self._beat

    @beat.setter
    def beat(self, val):
        self._beat = val
        self._accum = self.accumulate_beats(val)
        self.validate()

    @property
    def chords(self):
        return self._chords

    @chords.setter
    def chords(self, val):
        self._chords = val

    def accumulate_beats(self, b):
        """Helper function to make longer drums sound good
        example:
        [[1,0,0,1,1,0,1,1]]
        => [[0,1,2,0,0,1,0,0]]
        (each index is mapped to its distance from the last beat.)
        the purpose of this is to let drums "ring" without being reset
        during empty beats."""
        final = []
        for line in b:
            accum = []
            counter = 0
            for x in line:
                counter = (0 if x > 0 else counter + 1)
                accum.append(counter)
            final.append(accum)
        return final

    def validate(self):
        # avoid some common problems
        if len(self._drums) != len(self._beat):
            print("Warning: BackingTrack has a different number of drums and beats.")

        len1 = len(self._beat[1])
        for line in self._beat:
            if len(line) != len1:
                print(
                    "Warning: inconsistent number of beats given for different instruments.")

    def get_raw(self, i):
        t = i / self.rate
        bps = self.freq / 60
        ipb = 60 / self.freq * self.rate

        total = 0

        # sum up drums
        for j in range(len(self._drums)):
            total += self._drums[j].get_raw(
                i % ipb +  # per-beat time
                ipb * self._accum[j]  # accumulated beats to let "ring"
                [math.floor(t * bps) % len(self._accum[j])]
            )

        return total


class Player():
    def __init__(self, source, rate=settings.rate, frames_per_buffer=settings.frames_per_buffer):
        self.pyaudio = pyaudio.PyAudio()

        self.source = source
        self.bufferer = Bufferer(self.source, frames_per_buffer)

        self.stream = self.pyaudio.open(
            format=pyaudio.paFloat32,
            channels=1,
            rate=rate,
            output=True,
            frames_per_buffer=frames_per_buffer,
            stream_callback=self.bufferer.get_samples
        )


def main():
    # test module
    # a = BackingTrack([BassDrum(), HiHatDrum()], [
    #                 [0, 0, 0, 0], [0, 0, 0, 0]], None, freq=130)
    a = PolyOscillator(4, HarmonicsOscillator(harmonics=[1,0.5,0.25]), freq=[440 * 0.25, 0.5 * 261.6, 440*1.5*0.25, 0], amp=0.07)
    p = Player(a)
    while (not time.sleep(0.5 * settings.sleep_delay)):
        pass


if __name__ == "__main__":
    print("serpent_audio.py")
    main()
