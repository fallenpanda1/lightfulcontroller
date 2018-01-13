from scheduler.scheduler import Task
import logging
from abc import abstractmethod
import operator
import math

logger = logging.getLogger("global")


class LightSection:

    def __init__(self, positions, gradients=None):
        if isinstance(positions, range):
            positions = list(positions)

        self.positions = positions
        length = len(positions)

        if gradients is not None:
            self.gradients = gradients
        else:
            # create a list ranging from 0 to 1
            self.gradients = list(
                map(operator.truediv, list(range(length)), [length] * length))

    def __str__(self):
        return str(self.positions)

    def reversed(self):
        return LightSection(self.positions, list(reversed(self.gradients)))

    def merged_with(self, othersection):
        """ Merges two sections without modifying their gradients """
        combined_positions = self.positions + othersection.positions
        unaltered_gradients = self.gradients + othersection.gradients
        return LightSection(combined_positions, gradients=unaltered_gradients)

    def appended_with(self, othersection):
        """ 'Appends' a section to an existing one with gradients serially
        combined (TODO: whatever that means?) """
        combined_positions = self.positions + othersection.positions
        # passing in gradient = None uses the default gradient implementation,
        # which puts othersection in the gradient section after self
        return LightSection(combined_positions)

    def positions_with_gradient(self, value):
        return self.positions_in_gradient_range(value, value)

    def positions_in_gradient_range(self, min, max):
        filtered_positions = []
        for index, position in enumerate(self.positions):
            gradient = self.gradients[index]
            if min <= gradient <= max:
                filtered_positions.append(position)
        return filtered_positions

    @staticmethod
    def merge_all(sections):
        # not implemented efficiently at all, but doubtful it'll ever matter
        merged_positions = []
        merged_gradients = []
        for section in sections:
            merged_positions += section.positions
            merged_gradients += section.gradients
        return LightSection(merged_positions, merged_gradients)


class LightEffect:

    @abstractmethod
    def get_color(self, progress, gradient, velocity):
        """Called for each light effect task tick"""
        pass


class SolidColorLightEffect(LightEffect):
    """Light effect that applies solid color to light section"""

    def __init__(self, color):
        self.color = color

    def get_color(self, progress, gradient, velocity):
        return self.color.with_alpha(max(0, 1 - progress))


class GradientLightEffect(LightEffect):
    """Light effect that applies gradient over time to light section"""

    def __init__(self, color1, color2):
        self.color1 = color1
        self.color2 = color2

    def get_color(self, progress, gradient, velocity):
        # value of 2 would show whole sin wave on screen,
        # value of 4 would show half sine wave
        period = 3
        alpha = math.sin((progress - 1.0 * gradient / period)
                         * math.pi * 2) / 2 + 0.5
        return self.color1.with_alpha(alpha).blended_with(self.color2)


class MeteorLightEffect(LightEffect):

    def __init__(self, color, tail_length=1):
        self.color = color
        # 1 provides a 'standard' length, 0.5 will halve, 2 will double
        self.tail_length = tail_length

    def get_color(self, progress, gradient, velocity):
        meteor_head_length = 0.05
        meteor_tail_length = self.tail_length * 0.2

        # allow fireball to fully exit the bottom of the screen
        progress *= meteor_tail_length + 1

        if 0.0 < gradient - progress < meteor_head_length:  # meteor head
            alpha = 1 - (gradient - progress) / meteor_head_length
            return self.color.with_alpha(alpha)
        elif -meteor_tail_length < gradient - progress <= 0.0:  # meteor tail
            alpha = 1 - abs(gradient - progress) / meteor_tail_length
            return self.color.with_alpha(alpha)
        else:
            return self.color.with_alpha(0)
            # since we have to animate starting from off the screen and then go
            # off the screen, progress should range from -1 to 2
            # progress *= 3
            # progress -= 1

            # return self.color.with_alpha(alpha)


class LightEffectTask(Task):
    """An effect task contains a light effect and all the state around
    animating it.
    - the effect itself
    - section of light the effect is animating on
    - the time/lifecycle of the effect
     """

    def __init__(self, effect, section, duration, light_adapter):
        self.effect = effect
        self.section = section
        self.duration = duration
        self.light_adapter = light_adapter

    def start(self, time):
        self._start_time = time

    def tick(self, time):
        velocity = 1.0 * len(self.section.positions) / self.duration
        for index, position in enumerate(self.section.positions):
            gradient = self.section.gradients[index]
            new_color = self.effect.get_color(
                self.progress(time), gradient, velocity)
            existing_color = self.light_adapter.get_color(position)
            self.light_adapter.set_color(
                position, new_color.blended_with(existing_color))

    def progress(self, time):
        return min((time - self._start_time) / self.duration, 1)

    def is_finished(self, time):
        return self.progress(time) == 1


class RepeatingTask(Task):

    def __init__(self, task, progress_offset=0.0):
        self.__repeating = True
        self.progress_offset = progress_offset
        self.task = task

    def start(self, time):
        self.task.start(time)
        self.task._start_time -= self.task.duration * self.progress_offset

    def stop_repeating(self):
        self.__repeating = False

    def tick(self, time):
        self.task.tick(time)

    def progress(self, time):
        return self.task.progress(time)

    def is_finished(self, time):
        if self.__repeating and self.task.is_finished(time):
            self.task._start_time = time
            return False

        return self.task.is_finished(time)


class MidiOffLightEffectTask(LightEffectTask):
    """A special light effect task that reacts to the state of a particular
    MIDI note. The task sustains the first animation frame until the input note
    is off"""

    def __init__(self, task, pitch, midi_monitor):
        self.task = task
        self.pitch = pitch
        self.__midi_monitor = midi_monitor

    def start(self, time):
        self.task.start(time)
        self.__midi_monitor.register(self)
        self.__note_off_received = False

    def received_midi(self, rtmidi_message):
        if (rtmidi_message.isNoteOff() and
                rtmidi_message.getNoteNumber() == self.pitch):
            self.__note_off_received = True
            self.__midi_monitor.unregister(self)

    def tick(self, time):
        if not self.__note_off_received:
            self.task._start_time = time

        self.task.tick(time)

    def progress(self, time):
        return self.task.progress(time)

    def is_finished(self, time):
        return self.task.is_finished(time)
