# wrappers and connectors for gui and audio code.

import gui
import audio


class BackingTrackBridge:
    def __init__(self):
        DEFAULT_BACKING_TRACK_DRUMSET = [
            audio.BassDrum,
            audio.SnareDrum,
            audio.HiHatDrum,
        ]

        DEFAULT_BACKING_TRACK_DRUMBEAT = audio.Drumbeat(
            [
                [False, False, False, False],
                [True, True, True, True],
                [False, False, False, False],
            ]
        )

        DEFAULT_CHORD_PROGRESSION = audio.ChordProgression(
            [audio.Chord([466.164], [0.7], 4)]  # Bb chord
        )

        DEFAULT_BPM = 140

        DEFAULT_CHORD_SYNTH = audio.Harmonics()

        self.backing_track = audio.BackingTrack(
            drumset=DEFAULT_BACKING_TRACK_DRUMSET,
            drumbeat=DEFAULT_BACKING_TRACK_DRUMBEAT,
            chord_progression=DEFAULT_CHORD_PROGRESSION,
            bpm=DEFAULT_BPM,
            chord_synth=DEFAULT_CHORD_SYNTH,
        )

    def update_bpm(self, bpm: float):
        self.backing_track.bpm = bpm

    def update_drumbeat(self, lines: list[list[bool]]):
        self.backing_track.drumbeat = audio.Drumbeat(lines)
