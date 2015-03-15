import threading
import logging

from noip.lilypond import LilypondInstrument
from noip.piano import Note, OCTAVE
from bottle import Bottle, request, abort

logger = logging.getLogger(__name__)


class LilypondRunner(threading.Thread):

    def __init__(self, instrument, remove_callback):
        super().__init__()
        self.instrument = instrument
        self.remove_callback = remove_callback

    def stop(self):
        self.instrument.finish()

    def run(self):
        self.instrument.prepare()
        while self.instrument.playing():
            self.instrument.play()
        self.remove_callback(self)


class HTTPServer(object):

    def __init__(self, piano, host="0.0.0.0", port=40555):
        self.piano = piano
        self.host = host
        self.port = port
        self.app = Bottle()
        self.runners = []
        self.register_routes()

    def register_routes(self):
        self.app.get("/sms")(self.sms)
        self.app.post("/play")(self.play)
        self.app.post("/stop")(self.stop)

    def run(self):
        self.app.run(port=self.port, host=self.host)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop_runners()

    def stop_runners(self):
        logger.info("Stopping all HTTP lilypond runners")
        for runner in self.runners:
            runner.stop()

    def sms(self):
        score = request.query.get('score')
        if not score:
            abort(400, "missing score")

        instrument = LilypondInstrument(self.piano, score)
        runner = LilypondRunner(instrument, self.remove_runner)
        self.runners.append(runner)

        logger.info("Starting lilypond runner %s", runner)
        runner.start()

    def play(self):
        semitone, octave = self.extract_semitone()
        self.piano.play(Note.from_octave(semitone, octave))

    def extract_semitone(self):
        semitone = request.forms.get('semitone')
        octave = request.forms.get('octave', OCTAVE)
        if not semitone:
            abort(400, "missing semitone")
        return int(semitone), int(octave)

    def stop(self):
        semitone, octave = self.extract_semitone()
        self.piano.stop(Note.from_octave(semitone, octave))

    def remove_runner(self, runner):
        logger.info("Runner %s has stopped. Removing", runner)
        self.runners.remove(runner)
