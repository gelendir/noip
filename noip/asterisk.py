import socket
import logging

import threading
from queue import Queue, Empty

from noip.instrument import Instrument
from noip.piano import Note, OCTAVE

logger = logging.getLogger(__name__)


class AMIConnection(object):

    def __init__(self, host, username, password, port=5038):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.reader = None
        self.conn = None

    def is_open(self):
        return self.reader is not None

    def open(self):
        logger.info("Connecting to AMI %s:%s", self.host, self.port)
        self.conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.conn.connect((self.host, self.port))
        self.reader = self.conn.makefile()
        if not self.login():
            raise Exception("AMI Authentication failed")

    def login(self):
        message = [
            ('Action', 'login'),
            ('Username', self.username),
            ('Secret', self.password),
        ]

        self.send(message)
        response = dict(self.read())
        return response['Response'] == 'Success'

    def accumulate(self):
        lines = []

        line = self.reader.readline()
        while line.strip() != "":
            lines.append(line)
            line = self.reader.readline()

        return lines

    def parse(self, lines):
        message = []
        for line in lines:
            key, _, value = line.partition(":")
            message.append((key.strip(), value.strip()))
        return message

    def format(self, message):
        lines = ("{}: {}".format(key, value) for key, value in message)
        return "\n".join(lines) + "\n\n"

    def read(self):
        lines = self.accumulate()
        event = self.parse(lines)
        logger.debug("recv %s", event)
        return event

    def send(self, message):
        raw_message = self.format(message)
        logger.debug("send %s", message)
        self.conn.send(raw_message.encode('utf-8'))

    def close(self):
        if self.conn and self.reader:
            logger.info("Closing AMI connection")
            self.reader.close()
            self.conn.close()
            self.reader = None
            self.conn = None

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class AMIEventFilter(object):

    def __init__(self, connection, handler):
        self.connection = connection
        self.handler = handler
        self.filters = {'UserEvent': self.user_event,
                        'DTMF': self.dtmf,
                        'Hangup': self.hangup}

    def process_event(self):
        event = dict(self.connection.read())
        event_handler = self.filters.get(event['Event'])
        if event_handler:
            event_handler(event)

    def user_event(self, event):
        if event['UserEvent'] == 'Noip':
            self.handler.on_connect(event['Channel'])

    def dtmf(self, event):
        if event['Begin'] == 'Yes':
            self.handler.on_dtmf(event['Channel'], event['Digit'])

    def hangup(self, event):
        self.handler.on_disconnect(event['Channel'])


class PhoneManager(object):

    def __init__(self, piano):
        self.piano = piano
        self.octaves = [4, 5, 6, 7, 2, 1]
        self.channels = {}

    def on_connect(self, channel):
        if len(self.octaves) > 0:
            self.connect_phone(channel)
        else:
            logger.warn("No more octaves available for channel %s", channel)

    def connect_phone(self, channel):
        octave = self.octaves.pop(0)
        logger.info("Connecting channel %s octave %s", channel, octave)

        phone = PhoneChannel(self.piano, octave=octave)
        self.channels[channel] = phone
        phone.start()

    def on_disconnect(self, channel):
        if channel in self.channels:
            self.disconnect_channel(channel)

    def disconnect_channel(self, channel):
        logger.info("Disconnecting channel %s", channel)
        phone = self.channels.pop(channel)
        phone.stop()
        self.octaves.append(phone.octave)

    def on_dtmf(self, channel, digit):
        logger.debug("channel %s digit %s", channel, digit)
        phone = self.channels.get(channel)
        if phone:
            phone.play_digit(digit)

    def disconnect_all(self):
        channels = list(self.channels.keys())
        for channel in channels:
            self.disconnect_channel(channel)


class PhoneChannel(threading.Thread):

    TONES = {'1': 0,
             '2': 2,
             '3': 4,
             '4': 5,
             '5': 7,
             '6': 9,
             '7': 11,
             '8': 12}

    ACCIDENTALS = {'#': 1,
                   '*': -1}

    def __init__(self, piano, octave=OCTAVE, tempo=60):
        super().__init__()
        self.piano = piano
        self.octave = octave
        self.queue = Queue()
        self.accidental = 0
        self.time = 60.0 / tempo
        self.terminate = threading.Event()

    def stop(self):
        self.terminate.set()
        self.queue.put(None)

    def alive(self):
        return not self.terminate.is_set()

    def run(self):
        note = self.queue.get()

        while self.alive():

            self.piano.play(note)
            next_note = self.wait_next_note()
            self.piano.stop(note)

            if next_note:
                note = next_note
            elif self.alive():
                note = self.queue.get()

    def wait_next_note(self):
        try:
            return self.queue.get(True, self.time)
        except Empty:
            return None

    def play_digit(self, digit):
        if digit in self.TONES:
            tone = self.TONES[digit] + self.accidental
            note = Note.from_octave(tone, self.octave)
            self.queue.put(note)
            self.accidental = 0
        elif digit in self.ACCIDENTALS:
            self.accidental = self.ACCIDENTALS[digit]


class AsteriskInstrument(Instrument):

    def __init__(self, piano, connection):
        self.connection = connection
        self.manager = PhoneManager(piano)
        self.event_filter = AMIEventFilter(self.connection, self.manager)

    def prepare(self):
        if not self.connection.is_open():
            self.connection.open()

    def play(self):
        self.event_filter.process_event()

    def playing(self):
        return self.connection.is_open()

    def finish(self):
        self.manager.disconnect_all()
