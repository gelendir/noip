import mido
import logging

from threading import Lock

logger = logging.getLogger(__name__)

OCTAVE = 4


def setup_piano(name=None):
    ports = [p for p in mido.get_output_names()
             if p != 'Midi Through Port-0']

    if not ports:
        raise Exception("No MIDI device connected")
    elif len(ports) > 1:
        raise Exception("More than one MIDI device. Choose one")

    if not name:
        name = ports[0]

    return Piano(name)


class Note(object):

    def __init__(self, semitone):
        self.semitone = semitone

    @classmethod
    def from_octave(cls, tone, octave):
        semitone = (octave + 1) * 12 + tone
        return cls(semitone)

    def on(self):
        return mido.Message('note_on', note=self.semitone)

    def off(self):
        return mido.Message('note_off', note=self.semitone)


class Piano(object):

    @classmethod
    def device(cls, name):
        port = mido.open_output(name, autoreset=True)
        return cls(port)

    @classmethod
    def virtual(cls, name):
        rtmidi = mido.Backend('mido.backends.rtmidi')
        port = rtmidi.open_output(name, virtual=True)
        return cls(port)

    def __init__(self, port):
        self.port = port
        self.lock = Lock()

    def play(self, note):
        event = note.on()
        with self.lock:
            logger.debug(event)
            self.port.send(event)

    def stop(self, note):
        event = note.off()
        with self.lock:
            logger.debug(event)
            self.port.send(event)
