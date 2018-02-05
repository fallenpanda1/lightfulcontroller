import logging
from abc import ABC, abstractmethod
from midi.conversions import convert_to_ticks
from scheduler.scheduler import Task

logger = logging.getLogger("global")


class TimeKeeper(ABC):

    @property
    @abstractmethod
    def current_time(self):
        """Return the current time since this object's time keeping began"""
        pass

    @property
    @abstractmethod
    def current_tick(self):
        """Return current tick since this object's time keeping began"""
        pass

    @property
    @abstractmethod
    def tempo(self):
        """Return tempo (in MIDI standard nanoseconds, e.g. 120 bpm = 500000)"""
        pass


class TimeKeepingTask(Task, TimeKeeper):
    """"""
    current_tick = 0  # TimeKeeper abstract property
    tempo = 0  # TimeKeeper abstract property

    def __init__(self, tempo, ticks_per_beat):
        self.tempo = tempo
        self.ticks_per_beat = ticks_per_beat


    def start(self):
        pass

    def tick(self, time):
        self.current_tick = convert_to_ticks(time, self.tempo,
                                             self.ticks_per_beat)

    def is_finished(self):
        return False
