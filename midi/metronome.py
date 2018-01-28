import logging
import sys

from scheduler.scheduler import Task

logger = logging.getLogger("global")


class MetronomeTask(Task):
    """ Metronome """
    def __init__(self, tempo, beats_per_measure):
        self.tempo = tempo
        self.beats_per_measure = beats_per_measure
        self.__last_tick_time = 0

    def start(self):
        self.__last_tick_time = 0

    def tick(self, time):
        next_tick_time = self.__last_tick_time + 1.0 * self.tempo / 1000000
        if time >= next_tick_time:
            self.__last_tick_time = next_tick_time
            self._ring()

    def _ring(self):
        sys.stdout.write('\a')
        sys.stdout.flush()

    def is_finished(self, time):
        return False  # never finished
