import logging
import sys

from midi.conversions import convert_to_ticks
from scheduler.scheduler import Task

logger = logging.getLogger("global")


class MetronomeTask(Task):
    """Metronome that plays audio beats based on tempo and time
    signature. Also serves as a time-keeper for other systems that want
    to keep in sync with a common beat.
    """

    def __init__(self, tempo, beats_per_measure):
        self.tempo = tempo
        self.beats_per_measure = beats_per_measure
        self.ticks_per_beat = 50
        self.__last_tick = 0

    def start(self):
        self.__last_tick = 0

    def tick(self, time):
        if self.is_finished(time):
            # we're done already, so just return
            return

        current_tick = convert_to_ticks(time, self.tempo, self.ticks_per_beat)
        if current_tick > self.__last_tick + 1:
            logger.error("tick jump: " + str(current_tick - self.__last_tick))

        if current_tick == self.__last_tick:
            # don't handle same tick twice (this violates requirement that
            # tasks be deterministic, but it's not a huge deal in this case)
            return

        if current_tick + self.ticks_per_beat >= self.__last_tick:
            self.__last_tick = current_tick
            self._play_beat()

    def _play_beat(self):
        sys.stdout.write('\a')
        sys.stdout.flush()

    def is_finished(self, time):
        return False  # never finished for now

    def progress(self, time):
        # TODO: implement me
        return 0