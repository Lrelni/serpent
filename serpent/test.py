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

    osc = audio.BackingTrack(
        [
            audio.BassDrum(),
            audio.SnareDrum(),
            audio.HiHatDrum(),
        ],
        audio.Drumbeat(
            [
                [
                    1,
                    0,
                    1,
                    0,
                ],
                [
                    0,
                    1,
                    0,
                    1,
                ],
                [0, 1, 1, 0],
            ],
        ),
        audio.ChordProgression(
            [audio.Chord([440], [1], 1), audio.Chord([220], [1], 2)]
        ),
        130 * 4,
        audio.Harmonics(harmonics=[1]),
    )
    """osc = audio.Drummer(
        [
            audio.BassDrum(),
            audio.SnareDrum(),
            audio.HiHatDrum(),
        ],
        audio.Drumbeat(
            [
                [
                    1,
                    0,
                    1,
                    0,
                ],
                [
                    0,
                    1,
                    0,
                    1,
                ],
                [0, 1, 1, 0],
            ],
        ),
        130,
    )

    osc2 = audio.PolyphonicProgression(
        audio.ChordProgression(
            [
                audio.Chord([440, 440 * 3 / 2], [0.25, 0.25], 2),
                audio.Chord([440 * 4 / 3, 440 * 4 / 3 * 3 / 2], [0.25, 0.25], 2),
            ]
        ),
        audio.Polyphonic(None, audio.Harmonics(harmonics=[1, 0.5, 0.25, 0.125])),
        130,
    )"""

    player = audio.Player(osc)
    while True:
        time.sleep(2)


if __name__ == "__main__":
    print("test.py")
    interactive_test()
