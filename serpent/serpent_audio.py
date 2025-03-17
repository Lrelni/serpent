import time
import itertools
from abc import ABC, abstractmethod

import pyaudio
import numpy as np

import settings

class Oscillator(ABC):
    def __init__(self, freq=440, amp=1, rate=settings.rate):
        self._freq = freq
        self._amp = amp
        self._rate = rate
        self.i = 0
    
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

    def __iter__(self):
        return self
    
    def __next__(self):
        self.i += 1
        return self.get(self.i)
    
    @abstractmethod
    def get(self, i):
        pass

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
    
    def format_samples(self, samples):
        return (np.float32(np.array(samples)).tobytes(), pyaudio.paContinue)
    
    def get_samples(self, in_data, frame_count, time_info, status_flags):
        # used as callback for non-blocking audio
        return self.format_samples(self.step())

class SineOscillator(Oscillator):
    def get(self, i):
        return np.sin(np.pi * 2 * self._freq * i / self._rate) * self.amp
        
class Player():
    def __init__(self, source, rate, frames_per_buffer):
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
    a = Player(SineOscillator(freq=880), settings.rate, settings.frames_per_buffer)
    while (not time.sleep(settings.sleep_delay)):
        print("WhileTrue step")

if __name__ == "__main__":
    print("serpent_audio.py")
    main()