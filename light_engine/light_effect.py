import time
from scheduler.scheduler import Task
import logging
from abc import ABC, abstractmethod
import operator
import math

logger = logging.getLogger("global")

class LightSection:
    def __init__(self, positions):
        self.positions = positions
        length = len(positions)

        # create a list ranging from 0 to 1
        # todo: make this customizable later
        self.gradients = list(map(operator.truediv, list(range(length)), [length] * length))

    def __str__(self):
        return str(self.positions)

class LightEffect:
    @abstractmethod
    def get_color(self, progress, gradient):
        """Called for each light effect task tick"""
        pass

class SolidColorLightEffect(LightEffect):
    """Light effect that applies solid color to light section"""

    def __init__(self, color):
        self.color = color

    def get_color(self, progress, gradient):
        return self.color.with_alpha(max(0, 1 - progress))

class GradientLightEffect(LightEffect):
    """Light effect that applies gradient over time to light section"""

    def __init__(self, color1, color2):
        self.color1 = color1
        self.color2 = color2

    def get_color(self, progress, gradient):
        alpha = math.sin((progress - gradient / 2) * math.pi * 2) / 2 + 0.5
        return self.color1.with_alpha(alpha).blended_with(self.color2)

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
        for index, position in enumerate(self.section.positions):
            gradient = self.section.gradients[index]
            new_color = self.effect.get_color(self.progress(), gradient)
            existing_color = self.light_adapter.get_color(position)
            self.light_adapter.set_color(position, new_color.blended_with(existing_color))

    def progress(self):
        return min((time.time() - self._start_time) / self.duration, 1)

    def is_finished(self):
        return self.progress() == 1

class RepeatingTask(Task):
    def __init__(self, task, progress_offset=0.0):
        self.__repeating = True
        self.task = task
        self.task._start_time -= self.task.duration * progress_offset

    def stop_repeating(self):
        self.__repeating = False

    def tick(self):
        self.task.tick()

    def progress(self):
        return self.task.progress()

    def is_finished(self):
        if self.__repeating and self.task.is_finished():
            self.task._start_time = time.time()
            return False

        return self.task.is_finished()

class MidiOffLightEffectTask(LightEffectTask):
    """A special light effect task that reacts to the state of a particular MIDI note. 
    The task sustains the first animation frame until the input note is off"""
    def __init__(self, task, pitch, midi_monitor):
        self.task = task
        self.pitch = pitch
        self.__midi_monitor = midi_monitor
        midi_monitor.register(self)
        self.__note_off_received = False

    def received_midi(self, rtmidi_message):
        if rtmidi_message.isNoteOff() and rtmidi_message.getNoteNumber() == self.pitch:
            self.__note_off_received = True
            self.__midi_monitor.unregister(self)

    def tick(self):
        if not self.__note_off_received:
            self.task._start_time = time.time() # TODO: sanity check that this isn't a big performance hit

        self.task.tick()

    def progress(self):
        return self.task.progress()

    def is_finished(self):
        return self.task.is_finished()
