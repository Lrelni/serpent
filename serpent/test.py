import time
import unittest

import main
import gui
import audio
import settings


class TestAudio(unittest.TestCase):

    def test_lerp(self):
        self.assertEqual(audio.lerp(0, 1, 0.2), 0.2)
        self.assertEqual(audio.lerp(-1, 1, 0.5), 0)

    def test_harmonics_lut(self):
        self.assertEqual(len(audio.Harmonics.generate_lut([1, 1, 0, 1], 2)), 2)


def interactive_test():
    osc = audio.Chordable(
        audio.Chord([440, 440 * 5 / 4, 440 * 3 / 2], [0.2, 0.2, 0.3], 9), audio.Sine()
    )
    player = audio.Player(osc)
    while True:
        time.sleep(2)


if __name__ == "__main__":
    print("test.py")
    interactive_test()
