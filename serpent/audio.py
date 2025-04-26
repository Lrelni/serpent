import math
import pyaudio
import numpy as np

import settings


def lerp(a, b, t):
    return t * (b - a) + a


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
        self._harmonics = Harmonics.normal(harmonics) if normalize else harmonics
        self.frequency = frequency
        self.amplitude = amplitude
        self.normalize = normalize
        self.lut = Harmonics.generate_lut(harmonics, settings.harmonics_lut_resolution)

    @property
    def harmonics(self):
        return self._harmonics

    @harmonics.setter
    def harmonics(self, val):
        self._harmonics = Harmonics.normal(val) if self.normalize else val
        self.lut = Harmonics.generate_lut(val, settings.harmonics_lut_resolution)

    @staticmethod
    def normal(harmonics):
        total = sum(harmonics)
        final = []
        for harmonic in harmonics:
            final.append(harmonic / total)
        return final

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
        """'Sine' function that looks up the table"""
        lut_index = math.floor(len(self.lut) * (time % 1))
        return self.lut[lut_index]

    def get_sample_at_index(self, index):
        return self.amplitude * self.lut_sin_tau(
            self.frequency * index / self.samplerate
        )


class BassDrum(Sampleable):
    def __init__(self, amplitude: float = 1, *args, **kw):
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
    """Length is in beats. The time amount for each beat
    is not determined here."""

    def __init__(self, frequencies: list, amplitudes: list, length: int):
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
            raise Exception("len(frequencies) was not the same as len(amplitudes).")


class ChordProgression:

    def __init__(self, chords: list[Chord]):
        self.chords = chords
        self.accumulated_chord_indexes = ChordProgression.accumulate_chord_indexes(
            chords
        )
        self.length = len(self)

    def __len__(self):
        total_len = 0
        for chord in self.chords:
            total_len += len(chord)
        return total_len

    @staticmethod
    def accumulate_chord_indexes(chords) -> list[int]:
        """Helper function for mapping from a
        list of Chords to a list of indexes
        for the above list of chords.

        Example:
        [Chord(len=2), Chord(len=1), Chord(len=3)]
        =>[0, 0,        1,            2, 2]"""
        final = []
        index_of_current_chord = 0
        for chord in chords:
            for _ in range(len(chord)):
                final.append(index_of_current_chord)
            index_of_current_chord += 1
        return final

    def chord_index_at_beat(self, beat) -> int:
        return self.accumulated_chord_indexes[beat % self.length]

    def chord_at_beat(self, beat) -> Chord:
        return self.chords[self.accumulated_chord_indexes[beat % self.length]]


class Polyphonic(Sampleable):
    """Wrapper for making Sampleables play chords"""

    def __init__(self, chord: Chord, synth: Sampleable, *args, **kw):
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


class Drumbeat:
    """Lines format:
    list<line>
    where line := list<bool>.
    true: beat, false: rest"""

    def __init__(self, lines: list[list[bool]]):
        self.lines = lines
        self.accumulated_lines = Drumbeat.accumulate_beats(lines)
        self.validate()

    def get_accumulated_beat_amp(self, drum_index: int, beat: int) -> bool:
        return 1 if self.accumulated_lines[drum_index][beat] else 0

    def validate(self):
        len_first = len(self.lines[0])
        for line in self.lines:
            if len(line) != len_first:
                raise Exception(
                    "Drumbeat was not initialized with correct line lengths"
                )

    @staticmethod
    def accumulate_beats(lines: list[list[bool]]) -> list[list[bool]]:
        """Helper function to make longer drums sound good
        example:
        [[1,0,0,1,1,0,1,1]]
        => [[0,1,2,0,0,1,0,0]]
        (each beat is mapped to its distance from the last attack.)
        the purpose of this is to let drums "ring" without being reset
        during empty beats."""

        final = []
        for line in lines:
            accumulated_line = []
            beats_since_last_attack = 0
            for beat in line:
                beats_since_last_attack = 0 if beat else beats_since_last_attack + 1
                accumulated_line.append(beats_since_last_attack)
            final.append(accumulated_line)
        return final

    @staticmethod
    def convert_int_lines_to_bool(lines_int: list[list[int]]) -> list[list[bool]]:
        final = []
        for line_int in lines_int:
            converted_line = []
            for beat_int in line_int:
                converted_line.append(True if beat_int > 0 else False)
            final.append(converted_line)
        return final


class Drummer(Sampleable):
    def __init__(
        self, drumset: list[Sampleable], drumbeat: Drumbeat, bpm: float, *args, **kw
    ):
        super().__init__(*args, **kw)
        self._drumset = drumset
        self._drumbeat = drumbeat
        self.bpm = bpm

    @property
    def drumset(self) -> list[Sampleable]:
        return self._drumset

    @drumset.setter
    def drumset(self, val: list[Sampleable]):
        self._drumset = val
        self.validate()

    @property
    def drumbeat(self) -> Drumbeat:
        return self._drumbeat

    @drumbeat.setter
    def drumbeat(self, val: Drumbeat):
        self._drumbeat = val
        self.validate()

    def validate(self):
        if len(self._drumset) != len(self._drumbeat.lines):
            raise Exception("Drummer has nonmatching number of drums and lines")

    def get_sample_at_index(self, index):
        time = index / self.samplerate
        beats_per_second = self.bpm / 60
        samples_per_beat = 60 / self.bpm * self.samplerate

        total = 0
        for i in range(len(self._drumset)):
            accumulated_line = self._drumbeat.accumulated_lines[i]
            drum_sample_index = (
                index % samples_per_beat
                + samples_per_beat
                * self._drumbeat.get_accumulated_beat_amp(
                    i, math.floor(time * beats_per_second) % len(accumulated_line)
                )
            )
            drum = self._drumset[i]
            total += drum.get_sample_at_index(drum_sample_index)

        return total


class PolyphonicProgression(Sampleable):
    def __init__(
        self,
        chord_progression: ChordProgression,
        polyphonic: Polyphonic,
        bpm: float,
        *args,
        **kw
    ):
        super().__init__(*args, **kw)
        self.chord_progression = chord_progression
        self.polyphonic = polyphonic
        self.bpm = bpm

        self.last_chord_index = -1
        # initialize as -1 to ensure updating

    def update_synth_chord(self, current_beat: int):
        self.polyphonic.chord = self.chord_progression.chord_at_beat(current_beat)

    def lazy_update(self, index: int):
        time = index / self.samplerate
        beats_per_second = self.bpm / 60
        current_beat = math.floor(time * beats_per_second)
        if (
            self.chord_progression.chord_index_at_beat(current_beat)
            != self.last_chord_index
        ):
            self.update_synth_chord(current_beat)
        self.last_chord_index = self.chord_progression.chord_index_at_beat(current_beat)

    def get_sample_at_index(self, index: int):
        self.lazy_update(index)
        return self.polyphonic.get_sample_at_index(index)


class ControlledSynth(Sampleable):
    def __init__(
        self,
        synth: Sampleable,
        attacks: list[float],
        nbeats: int,
        bpm: float,
        *args,
        **kw
    ):
        """
        attacks: list of beat locations.
        For example, attacks=[0, 4.5, 4, 2]
        would look like
        attacks on beat 0, 2, 4, and 4.5.
        Beats are zero indexed.
        (Traditional beat 1 is data beat 0)
        When getting .attacks via property
        there is no guarantee that the
        original order is preserved.

        nbeats: number of beats before repeating.
        If nbeats < max(attacks) then some of the
        attacks will be deleted. If nbeats > max(attacks)
        then silence will be played until the beat begins
        again.

        """
        super().__init__(*args, **kw)
        self.synth = synth
        self.bpm = bpm
        self._attacks = ControlledSynth.format_attacks(attacks, nbeats)
        self._nbeats = nbeats
        self.cur_attack_i = 0  # index of current attack
        print(self._attacks)

    @property
    def attacks(self) -> list[float]:
        return self._attacks[1:-1]  # remove padding at ends

    @attacks.setter
    def attacks(self, val: list[float]):
        ControlledSynth.validate(val)
        self._attacks = ControlledSynth.format_attacks(
            attacks=val, nbeats=self._attacks[-1]
        )

    @property
    def nbeats(self) -> int:
        return self._nbeats

    @nbeats.setter
    def nbeats(self, val: int):
        self._attacks = ControlledSynth.format_attacks(attacks=self.attacks, nbeats=val)
        self._nbeats = val

    @staticmethod
    def validate(attacks: list[float]):
        for attack_beat in attacks:
            if attack_beat < 0:
                raise ValueError(
                    "ControlledSynth.attacks must consist of beats >= zero."
                )

    @staticmethod
    def format_attacks(attacks: list[float], nbeats: int):
        sorted_attacks_trimmed = []
        for attack_beat in sorted(attacks):
            if attack_beat < nbeats:
                sorted_attacks_trimmed.append(attack_beat)
        return [0, *sorted_attacks_trimmed, float(nbeats)]

    def update_current_attack(self, beat: float):
        """beat should be %"""
        self.cur_attack_i = 0
        for index in range(len(self._attacks) - 1, 0, -1):
            # step backwards through [len-1,len-2...1]
            if beat >= self._attacks[index]:
                self.cur_attack_i = index % len(self._attacks)
                # wrap around to zeroth attack if last is reached
                break  # don't check any more attacks

    def get_sample_at_index(self, index):
        time = index / self.samplerate
        beat = (time * self.bpm / 60) % self._attacks[-1]
        # beat is wrapped around (nbeats=self._attacks[-1])

        if (
            beat >= self._attacks[self.cur_attack_i + 1]
            or beat <= self._attacks[self.cur_attack_i]
        ):
            self.update_current_attack(beat)

        return (
            self.synth.get_sample_at_index(
                # relative to current attack's beat
                index=(beat - self._attacks[self.cur_attack_i])
                * self.samplerate
                / (self.bpm / 60)  # beats per second
            )
            if self.cur_attack_i != 0  # first "attack" is always at beat 0
            else 0
        )


class BackingTrack(Sampleable):
    def __init__(
        self,
        drumset: list[Sampleable],
        drumbeat: Drumbeat,
        chord_progression: ChordProgression,
        bpm: float,
        chord_synth: Sampleable,
        *args,
        **kw
    ):
        super().__init__(*args, **kw)
        self._drumset = drumset
        self._drumbeat = drumbeat
        self.chord_progression = chord_progression

        self.chord_player = PolyphonicProgression(
            chord_progression=chord_progression,
            polyphonic=Polyphonic(None, chord_synth),
            bpm=bpm,
        )

        self.drummer = Drummer(drumset=drumset, drumbeat=drumbeat, bpm=bpm)

    @property
    def drumset(self) -> list[Sampleable]:
        return self.drummer._drumset

    @drumset.setter
    def drumset(self, val: list[Sampleable]):
        self.drummer._drumset = val

    @property
    def drumbeat(self) -> Drumbeat:
        return self.drummer._drumbeat

    @drumbeat.setter
    def drumbeat(self, val: Drumbeat):
        self.drummer._drumbeat = val

    def get_sample_at_index(self, index):

        # average used to stop clipping issues
        return 0.5 * (
            self.drummer.get_sample_at_index(index)
            + self.chord_player.get_sample_at_index(index)
        )
