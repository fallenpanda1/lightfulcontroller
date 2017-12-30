import time
from scheduler.scheduler import Task
import logging
from abc import ABC, abstractmethod

logger = logging.getLogger("global")

class LightSection:
    def __init__(self, positions):
        self.positions = positions

    def gradient(self, index):
        return 0

class LightEffect:
    @abstractmethod
    def get_color(self, progress, position):
        """Called for each light effect task tick"""
        pass

class SolidColorLightEffect(LightEffect):
    """Light effect that applies solid color to light section"""

    def __init__(self, color):
        self.color = color

    def get_color(self, progress, position):
        return self.color.with_alpha(1 - progress)

class LightEffectTask(Task):
    """An effect task contains a light effect and all the state around animating it.
    - the effect itself
    - section of light the effect is animating on
    - the time/lifecycle of the effect
     """

    def __init__(self, effect, section, duration, light_adapter):
        self.effect = effect
        self.section = section
        self.duration = duration
        self.light_adapter = light_adapter
        self._start_time = time.time() # protected

    def tick(self):
        for position in self.section.positions:
            new_color = self.effect.get_color(self.progress(), position)
            existing_color = self.light_adapter.get_color(position)
            self.light_adapter.set_color(position, new_color.blended_with(existing_color))

    def progress(self):
        return min((time.time() - self._start_time) / self.duration, 1)

    def is_finished(self):
        return self.progress() == 1


# TODO: definitely goes elsewhere
class MidiOffLightEffectTask(LightEffectTask):
    """A light effect task that sustains the first animation frame until the note is off"""
    def __init__(self, effect, section, duration, light_adapter, note):
        self.note = note
        super().__init__(effect, section, duration, light_adapter)

    def tick(self):
        if self.note.velocity > 0:
            self._start_time = time.time()
        super().tick()