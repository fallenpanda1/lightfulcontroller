import logging
import sys

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
        self.__last_tick_time = 0

    def start(self):
        self.__last_tick_time = 0

    def tick(self, time):
        next_tick_time = self.__last_tick_time + 1.0 * self.tempo / 1000000
        if time >= next_tick_time:
            self.__last_tick_time = next_tick_time
            self._play_beat()

    def _play_beat(self):
        sys.stdout.write('\a')
        sys.stdout.flush()

    def is_finished(self, time):
        return False  # never finished for now

    def progress(self, time):
        # TODO: implement me
        return 0