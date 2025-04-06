import pyaudio
import numpy as np

import settings


class Player:
    """PyAudio wrapper for objects with next()"""

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

        def format_samples(samples):
            return (np.float32(np.array(samples)).tobytes, pyaudio.paContinue)

        def callback(self, in_data, frame_count, time_info, status_flags):
            return self.format_samples(next(self))

    def __init__(
        self, source, samplerate=settings.samplerate, chunksize=settings.chunksize
    ):
        self._pyaudio = pyaudio.PyAudio()
        self._source = source
        self._bufferer = Player.Bufferer(self._source, chunksize)
        self._stream = self._pyaudio.open(
            format=pyaudio.paFloat32,
            channels=1,
            rate=samplerate,
            output=True,
            frames_per_buffer=chunksize,
            stream_callback=self._bufferer.callback,
        )


class Generator:
    """Base class for things with audio generating capabilities"""

    def __init__(self, rate):
        pass
