import math
import pyaudio
import numpy as np

import settings


def lerp(a, b, t):
    return t * (b - a) + a


class Player:
    """PyAudio wrapper for objects with next()"""

    class SourceCombiner:
        """Combine multiple audio sources."""

        def __init__(self, sources):
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

        def __init__(self, source, chunksize):
            self._source = source
            self._chunksize = chunksize

        def __next__(self):
            samples = []
            for _ in range(self._chunksize):
                samples.append(next(self._source))
            return samples

        @staticmethod
        def format_samples(samples):
            return (np.float32(np.array(samples)).tobytes(), pyaudio.paContinue)

        def callback(self, in_data, frame_count, time_info, status_flags):
            return self.format_samples(next(self))

    def __init__(
        self,
        sources,
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

    def __init__(self, rate=settings.samplerate):
        self.samplerate = rate
        self.sample_index = 0

    def get_sample_at_index(self, index):
        raise NotImplementedError

    def __next__(self):
        self.sample_index += 1
        return self.get_sample_at_index(self.sample_index)


# specific instruments below #


class Noise(Sampleable):

    def __init__(self, pitch=12000, amplitude=1, *args, **kw):
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

    def __init__(self, frequency=settings.concert_a_freq, amplitude=1, *args, **kw):
        super().__init__(*args, **kw)
        self.frequency = frequency
        self.amplitude = amplitude

    def get_sample_at_index(self, index):
        return (
            math.sin(math.tau * self.frequency * index / self.samplerate)
            * self.amplitude
        )


class Square(Sampleable):

    def __init__(self, frequency=settings.concert_a_freq, amplitude=1, *args, **kw):
        super().__init__(*args, **kw)
        self.frequency = frequency
        self.amplitude = amplitude

    def get_sample_at_index(self, index):
        return (
            1 if (self.frequency * index / self.samplerate) % 2 > 1 else 0
        ) * self.amplitude


class Saw(Sampleable):

    def __init__(self, frequency=settings.concert_a_freq, amplitude=1, *args, **kw):
        super().__init__(*args, **kw)
        self.frequency = frequency
        self.amplitude = amplitude

    def get_sample_at_index(self, index):
        return ((self.frequency * index / self.samplerate) % 1) * self.amplitude


class Harmonics(Sampleable):

    def __init__(
        self,
        harmonics=[1, 0.5, 0.25],
        frequency=settings.concert_a_freq,
        amplitude=1,
        *args,
        **kw
    ):
        super().__init__(*args, **kw)
        self._harmonics = harmonics
        self.frequency = frequency
        self.amplitude = amplitude
        self.lut = Harmonics.generate_lut(harmonics, settings.harmonics_lut_resolution)

    @property
    def harmonics(self):
        return self._harmonics

    @harmonics.setter
    def harmonics(self, val):
        self._harmonics = val
        self.lut = Harmonics.generate_lut(val, settings.harmonics_lut_resolution)

    @staticmethod
    def generate_lut(harmnonics, resolution):
        times = np.arange(0, 1, 1 / resolution)
        samples = []
        for time in times:
            total = 0
            harmonic = 1
            for harmonic_amp in harmnonics:
                total += math.sin(math.tau * time * harmonic) * harmonic_amp
                harmonic += 1
            samples.append(total)
        return samples

    def lut_sin_tau(self, time):
        lut_index = math.floor(len(self.lut) * (time % 1))
        return self.lut[lut_index]

    def get_sample_at_index(self, index):
        return self.amplitude * self.lut_sin_tau(
            self.frequency * index / self.samplerate
        )


class BassDrum(Sampleable):
    def __init__(self, amplitude=1, *args, **kw):
        super().__init__(*args, **kw)
        self.harmonics = Harmonics(
            harmonics=list(np.pow(np.divide(0.7, list(range(1, 20))), 4)),
            frequency=60,
        )
        self.amplitude = amplitude

    def get_sample_at_index(self, index):
        envelope = math.pow(((index / self.samplerate) * 0.6) + 1, -20)
        return envelope * self.amplitude * self.harmonics.get_sample_at_index(index)


class HiHatDrum(Sampleable):
    def __init__(self, amplitude=1, *args, **kw):
        super().__init__(*args, **kw)
        self.noise = Noise(pitch=100000)
        self.amplitude = amplitude

    def get_sample_at_index(self, index):
        envelope = 0.5 * math.pow((index / self.samplerate) + 1, -40)
        return envelope * self.amplitude * self.noise.get_sample_at_index(index)


class SnareDrum(Sampleable):
    def __init__(self, amplitude=1, *args, **kw):
        super().__init__(*args, **kw)
        self.noise = Noise(pitch=20000, amplitude=0.5)
        self.harmonics = Harmonics(
            harmonics=list(np.pow(np.divide(0.8, list(range(1, 20))), 3)), frequency=125
        )
        self.amplitude = amplitude

    def get_sample_at_index(self, index):
        envelope = np.clip(1.25 * math.pow((index / self.samplerate * 0.8) + 1, -40))
        return envelope * (
            self.harmonics.get_sample_at_index(index)
            + self.noise.get_sample_at_index(index)
        )


class Chord:
    def __init__(self, frequencies, amplitudes, length):
        self._frequencies = frequencies
        self._amplitudes = amplitudes
        self._length = length
        self.validate()

    @property
    def frequencies(self):
        return self._frequencies

    @property
    def amplitudes(self):
        return self._amplitudes

    def __len__(self):
        return self._length

    def __iter__(self):
        return zip(self._frequencies, self._amplitudes)

    def validate(self):
        if len(self._frequencies) != len(self._amplitudes):
            raise Exception("len(frequencies) was not the same as len(amplitudes.)")


class Chordable(Sampleable):
    def __init__(self, chord, synth, *args, **kw):
        super().__init__(*args, **kw)
        self.chord = chord
        self.synth = synth

    def get_sample_at_index(self, index):
        total = 0
        for frequency, amplitude in self.chord:
            self.synth.frequency = frequency
            self.synth.amplitude = amplitude
            total += self.synth.get_sample_at_index(index)
        return total
