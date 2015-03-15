import time
import logging

from notehole.parse import parse_lilypond
from notehole.music import Note, Chord
from noip.piano import Note as PianoNote
from noip.instrument import Instrument

logger = logging.getLogger(__name__)


class LilypondInstrument(Instrument):

    def __init__(self, piano, score, tempo=120):
        self.piano = piano
        self.score = score
        self.tempo = tempo

    def prepare(self):
        self.items = list(parse_lilypond(self.score))
        logger.debug("parsed score %s", self.items)

    def play(self):
        if len(self.items) > 0:
            self.play_item(self.items.pop(0))

    def play_item(self, item):
        notes = self.convert_item(item)
        self.play_notes(notes)
        self.wait(item.duration)
        self.stop_notes(notes)

    def convert_item(self, item):
        if isinstance(item, Note):
            return [PianoNote.from_octave(item.tone.semitone, item.tone.octave)]
        elif isinstance(item, Chord):
            return [PianoNote.from_octave(i.semitone, i.octave)
                    for i in item.tones]
        return []

    def play_notes(self, notes):
        for note in notes:
            self.piano.play(note)

    def stop_notes(self, notes):
        for note in notes:
            self.piano.stop(note)

    def wait(self, duration):
        unit = 4 / duration.value
        for _ in range(duration.dots):
            unit += unit / 2
        secs = 60 / self.tempo * unit
        logger.debug("wait %s", secs)
        time.sleep(secs)

    def playing(self):
        return len(self.items) > 0

    def finish(self):
        self.items = []
