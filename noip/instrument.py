import abc

import logging

logger = logging.getLogger(__name__)


class Instrument(metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def prepare(self):
        pass

    @abc.abstractmethod
    def play(self):
        pass

    @abc.abstractmethod
    def finish(self):
        pass

    @abc.abstractmethod
    def playing(self):
        pass

    def __enter__(self):
        self.prepare()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.finish()
