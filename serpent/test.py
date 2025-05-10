import time
import unittest

import main
import gui
import audio
import notes
import settings


def interactive_test():
    voice1 = audio.Voice(
        audio.ADSR(
            audio.Harmonics(),
            attack_len=0.01,
            release_len=0.07,
            sustain_amp=0.8,
            decay_len=0.07,
        ),
        [
            # giant steps
            audio.Note(0, 2, notes.transpose(notes.freq_from_str("D#5"), 3)),
            audio.Note(2, 2, notes.transpose(notes.freq_from_str("B4"), 3)),
            audio.Note(4, 2, notes.transpose(notes.freq_from_str("G#4"), 3)),
            audio.Note(6, 1.66, notes.transpose(notes.freq_from_str("E4"), 3)),
            audio.Note(7.66, 4.33, notes.transpose(notes.freq_from_str("G4"), 3)),
            audio.Note(12, 1.66, notes.transpose(notes.freq_from_str("G#4"), 3)),
            audio.Note(13.66, 2.33, notes.transpose(notes.freq_from_str("F#4"), 3)),
            audio.Note(16, 2, notes.transpose(notes.freq_from_str("B4"), 3)),
            audio.Note(18, 2, notes.transpose(notes.freq_from_str("G4"), 3)),
            audio.Note(20, 2, notes.transpose(notes.freq_from_str("E4"), 3)),
            audio.Note(22, 1.66, notes.transpose(notes.freq_from_str("C4"), 3)),
            audio.Note(23.66, 4.33, notes.transpose(notes.freq_from_str("D#4"), 3)),
            audio.Note(28, 2, notes.transpose(notes.freq_from_str("E4"), 3)),
            audio.Note(30, 1.66, notes.transpose(notes.freq_from_str("D4"), 3)),
            audio.Note(31.66, 4.33, notes.transpose(notes.freq_from_str("G4"), 3)),
            audio.Note(36, 2, notes.transpose(notes.freq_from_str("G#4"), 3)),
            audio.Note(38, 1.66, notes.transpose(notes.freq_from_str("F#4"), 3)),
            audio.Note(39.66, 4.33, notes.transpose(notes.freq_from_str("B4"), 3)),
            audio.Note(44, 2, notes.transpose(notes.freq_from_str("C5"), 3)),
            audio.Note(46, 1.66, notes.transpose(notes.freq_from_str("C5"), 3)),
            audio.Note(47.66, 4.33, notes.transpose(notes.freq_from_str("D#5"), 3)),
            audio.Note(52, 2, notes.transpose(notes.freq_from_str("E5"), 3)),
            audio.Note(54, 1.66, notes.transpose(notes.freq_from_str("E5"), 3)),
            audio.Note(55.66, 4.33, notes.transpose(notes.freq_from_str("G5"), 3)),
            audio.Note(60, 1.66, notes.transpose(notes.freq_from_str("D#5"), 3)),
            audio.Note(61.66, 0.33, notes.transpose(notes.freq_from_str("D#5"), 3)),
        ],
        64,
        288,
        True,
    )

    voice2 = audio.Voice(
        audio.ADSR(audio.HiHatDrum(amplitude=1)),
        [
            audio.Note(1, 1),
            audio.Note(3, 1),
        ],
        4,
        200,
        False,
    )

    full = audio.SyncedVoices([voice1, voice2], 348)
    player = audio.Player(full)
    while True:
        time.sleep(2)


if __name__ == "__main__":
    print("test.py")
    interactive_test()
