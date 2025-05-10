import settings
import math

# assuming 4th octave
NOTE_CONVERT = {
    "C": -9,
    "D": -7,
    "E": -5,
    "F": -4,
    "G": -2,
    "A": 0,
    "B": 2,
}

ACCIDENTAL_CONVERT = {"#": 1, "b": -1, "": 0}


def transpose(frequency: float, steps: int):
    return frequency * math.pow(2, steps / 12)


def _index_from_str(string):
    """
    Convert from a note name to a note index (internal function)
    format:
    octave is required.
    <note-letter> <accidental> <octave>
    <note-letter> ::= A | B | C | D | E | F | G | a | b | c | d | e | f | g
    <accidental> ::= # | b | <empty string>
    <octave> ::= 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8"""

    note_letter = string[0].upper()
    #            A#4                                A4 (accidental="")
    accidental = string[1] if len(string) == 3 else ""
    #            A#4                                A4 (accidental="")
    octave = int(string[2] if len(string) == 3 else string[1])

    octave_offset = 12 * (octave - 4)
    return NOTE_CONVERT[note_letter] + ACCIDENTAL_CONVERT[accidental] + octave_offset


def _freq_from_index(index):
    return settings.concert_a_freq * math.pow(2, index / 12)


def freq_from_str(string):
    """Convert from a note name to a frequency in Hz
    octave is required.
    <note-letter> <accidental> <octave>
    <note-letter> ::= A | B | C | D | E | F | G | a | b | c | d | e | f | g
    <accidental> ::= # | b | <empty string>
    <octave> ::= 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8"""
    return _freq_from_index(_index_from_str(string))
