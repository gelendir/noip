import pygame
import os
import logging

from contextlib import contextmanager

from noip.piano import Note, OCTAVE
from noip.instrument import Instrument

logger = logging.getLogger(__name__)


@contextmanager
def pygame_session():
    logger.info("Initializing pygame")
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    pygame.init()
    pygame.joystick.init()
    pygame.display.set_mode((1, 1))

    yield

    logger.info("Shutting down pygame")
    pygame.joystick.quit()
    pygame.quit()


def create_gamepad(number=0):
    count = pygame.joystick.get_count()
    if number >= count:
        raise Exception("Gamepad {} not detected".format(number))

    gamepad = pygame.joystick.Joystick(number)
    return gamepad


def gamepad_list():
    count = pygame.joystick.get_count()
    for number in range(count):
        joystick = pygame.joystick.Joystick(number)
        yield (joystick.get_id(), joystick.get_name())


class GamepadInstrument(Instrument):

    MAPPING = {6: 0,
               2: 2,
               7: 4,
               0: 5,
               3: 7,
               5: 9,
               1: 11,
               4: 12}

    def __init__(self, piano, gamepad, octave=OCTAVE, mapping=None):
        self.piano = piano
        self.gamepad = gamepad
        self.octave = octave
        self.mapping = mapping or self.MAPPING

    def prepare(self):
        logger.info("Initializing gamepad %s", self.gamepad.get_id())
        pygame.event.set_allowed([pygame.JOYBUTTONUP,
                                  pygame.JOYBUTTONDOWN])
        self.gamepad.init()

    def play(self):
        event = pygame.event.wait()
        if event.type == pygame.JOYBUTTONDOWN and event.joy == self.gamepad.get_id():
            logger.debug(event)
            self.start_note(event)
        elif event.type == pygame.JOYBUTTONUP and event.joy == self.gamepad.get_id():
            logger.debug(event)
            self.stop_note(event)

    def start_note(self, event):
        if event.button in self.mapping:
            note = self.event_to_note(event)
            self.piano.play(note)

    def stop_note(self, event):
        if event.button in self.mapping:
            note = self.event_to_note(event)
            self.piano.stop(note)

    def event_to_note(self, event):
        tone = self.mapping[event.button]
        return Note.from_octave(tone, self.octave)

    def finish(self):
        self.gamepad.quit()
        # pygame.event.post(pygame.event.Event(pygame.NOEVENT))

    def playing(self):
        return self.gamepad.get_init()
