from AppKit import NSSound
import logging

from midi.conversions import convert_to_seconds
from midi.conversions import convert_to_ticks
from scheduler.scheduler import Task

logger = logging.getLogger("global")


class MetronomeTask(Task):
    """Metronome that plays audio beats based on tempo and time
    signature. Also serves as a time-keeper for other systems that want
    to keep in sync with a common beat.
    """

    def __init__(self, tempo, ticks_per_beat, beats_per_measure):
        self.tempo = tempo
        self.ticks_per_beat = ticks_per_beat
        self.beats_per_measure = beats_per_measure
        self.first_tick = 0
        self.last_tick = 0

        # whoa, ObjC!
        self.sound = NSSound.alloc().initWithContentsOfFile_byReference_(
            "media/audio/metronome.wav", False
        )

    def start(self):
        self.first_tick = 0
        self.last_tick = 0

    def tick(self, time):
        if self.is_finished(time):
            # we're done already, so just return
            return

        current_tick = convert_to_ticks(time, self.tempo, self.ticks_per_beat)

        # mod current tick by beats in a measure
        current_tick = current_tick % self.__ticks_per_measure()

        if current_tick > self.last_tick + 1:
            logger.error("tick jump: " + str(current_tick - self.last_tick))

        if current_tick == self.last_tick:
            # don't handle same tick twice (this violates requirement that
            # tasks be deterministic, but it's not a huge deal in this case)
            return
        self.last_tick = current_tick

        if current_tick % self.ticks_per_beat == 0:
            logger.info("playing")
            self._play_beat()

    def __ticks_per_measure(self):
        return self.beats_per_measure * self.ticks_per_beat

    def _play_beat(self):
        self.sound.stop()
        self.sound.play()

    @property
    def last_time(self):
        return convert_to_seconds(self.last_tick, self.tempo,
                                  self.ticks_per_beat)

    def is_finished(self, time):
        return False  # never finished for now

    def progress(self, time):
        # TODO: implement me
        return 0


class MetronomeSyncedTask(Task):
    """Sync a task with a metronome"""

    def __init__(self, metronome, task):
        """
        Args:
            metronome: an already ticking metronome
            task: task to sync up with the metronome
        """
        self.metronome = metronome
        self.task = task

    def start(self):
        self.task.start()

    def tick(self, time):
        self.task.tick(self.metronome.last_time)

    def is_finished(self, time):
        return False
