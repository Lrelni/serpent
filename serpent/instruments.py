import math
import random

import numpy as np
import librosa

import audio
import settings


def lerp(a: float, b: float, t: float) -> float:
    return t * (b - a) + a


class Noise(audio.Sampleable):

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


class Sine(audio.Sampleable):

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


class Square(audio.Sampleable):

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


class Saw(audio.Sampleable):

    def __init__(
        self, frequency=settings.concert_a_freq, amplitude: float = 1, *args, **kw
    ):
        super().__init__(*args, **kw)
        self.frequency = frequency
        self.amplitude = amplitude

    def get_sample_at_index(self, index):
        return ((self.frequency * index / self.samplerate) % 1) * self.amplitude


class Harmonics(audio.Sampleable):

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


class AudioFile(audio.Sampleable):
    def __init__(self, file, amplitude: float = 1, *args, **kw):
        super().__init__(*args, **kw)
        self.frames, _ = librosa.core.load(file, sr=self.samplerate)

    def get_sample_at_index(self, index):
        rounded = round(index)
        if rounded >= len(self.frames) or rounded < 0:
            return 0
        return self.frames[rounded]


class RoundRobin(audio.Sampleable):
    """Round-robin version of AudioFile that chooses a new file to play with each rewind()"""

    def __init__(self, files: list, amplitude: float = 1, *args, **kw):
        super().__init__(*args, **kw)
        self.sounds = []
        for file in files:
            self.sounds.append(librosa.core.load(file, sr=self.samplerate)[0])
        self.selected_sound = random.choice(self.sounds)

    def get_sample_at_index(self, index):
        rounded = round(index)
        if rounded >= len(self.selected_sound) or rounded < 0:
            return 0
        return self.selected_sound[rounded]

    def rewind(self):
        self.sample_index = 0
        self.selected_sound = random.choice(self.sounds)


class BassDrum(audio.Sampleable):
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


class HiHatDrum(audio.Sampleable):
    def __init__(self, amplitude: float = 1, *args, **kw):
        super().__init__(*args, **kw)
        self.noise = Noise(pitch=100000)
        self.amplitude = amplitude

    def get_sample_at_index(self, index):
        envelope = 0.5 * math.pow((index / self.samplerate) + 1, -40)
        return envelope * self.amplitude * self.noise.get_sample_at_index(index)


class SnareDrum(audio.Sampleable):
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
