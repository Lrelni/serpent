import time
import itertools
from abc import ABC, abstractmethod

import pyaudio
import numpy as np

import settings


def _index_from_str(string):
    # format:
    # octave is required.
    # <note-letter> <accidental> <octave>
    # <note-letter> ::= A | B | C | D | E | F | G | a | b | c | d | e | f | g
    # <accidental> ::= # | b | <empty string>
    # <octave> ::= 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8

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
    return settings.a_freq * np.pow(2, index / 12)


def freq_from_str(string):
    return _freq_from_index(_index_from_str(string))


class Oscillator(ABC):
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


class Bufferer:
    # wrap single sample generators into pyAudio compatible data
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
        return list(itertools.islice(self._source, self._frames_per_buffer))

    @staticmethod
    def format_samples(samples):
        return (np.float32(np.array(samples)).tobytes(), pyaudio.paContinue)

    def get_samples(self, in_data, frame_count, time_info, status_flags):
        # used as callback for non-blocking audio
        return self.format_samples(self.step())


class SineOscillator(Oscillator):
    def get_raw(self, i):
        return np.sin(np.pi * 2 * self._freq * i / self._rate)


class HarmonicsOscillator(Oscillator):
    def __init__(self, harmonics=[1], *args, **kw):
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
            final += self._harmonics[j] * np.sin(mult * (1+j))
        return final


class Metronome(Oscillator):
    def __init__(self, grouping=4, *args, **kw):
        super().__init__(*args, **kw)
        self.grouping = grouping

    # the freq variable is now in bpm.
    def get_raw(self, i):
        t = i / self.rate
        bps = self.freq / 60
        # see https://www.desmos.com/calculator/guduxdwwvv for a visual of the modulating function
        return np.pow(np.clip(1 - ((t * bps) % 1) - (0.3 if ((t * bps) % self.grouping) >= 1 else 0), 0, 1), 4) *\
            np.sin(np.pi * 2 * 1000 * i / self._rate)  # modulate a sine wave


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
    a = HarmonicsOscillator(harmonics=[1,1,1,1,1,1,1,1,1,1,1,1,1,1], freq=220)
    p = Player(a)
    while (not time.sleep(settings.sleep_delay)):
        pass


if __name__ == "__main__":
    print("serpent_audio.py")
    main()
