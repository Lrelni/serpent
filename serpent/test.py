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


def interactive_test():
    osc = audio.Saw(frequency=110, amplitude=1)
    osc2 = audio.Saw(frequency=440 * 5 / 4, amplitude=0 / 3)
    osc3 = audio.Saw(frequency=440 * 3 / 2, amplitude=0 / 3)
    player = audio.Player([osc, osc2, osc3])

    while True:
        time.sleep(5)


if __name__ == "__main__":
    print("test.py")
    interactive_test()
