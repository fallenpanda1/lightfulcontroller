from abc import abstractmethod
import logging
import operator
import math
import time

from scheduler.scheduler import Task

logger = logging.getLogger("global")


class LightSection:
    def __init__(self, positions, gradients=None):
        # make positions a list if it's a range masquerading as a list
        self.positions = list(positions)
        length = len(self.positions)

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
    def get_color(self, progress, gradient):
        """Called for each light effect task tick"""
        pass


class SolidColor(LightEffect):
    """Light effect that applies solid color to light section"""

    def __init__(self, color):
        self.color = color

    def get_color(self, progress, gradient):
        return self.color.with_alpha(max(0, 1 - progress))


class Gradient(LightEffect):
    """Light effect that applies gradient over time to light section"""

    def __init__(self, color1, color2):
        self.color1 = color1
        self.color2 = color2

    def get_color(self, progress, gradient):
        # value of 2 would show whole sin wave on screen,
        # value of 4 would show half sine wave
        period = 3
        alpha = math.sin((progress - 1.0 * gradient / period)
                         * math.pi * 2) / 2 + 0.5
        return self.color1.with_alpha(alpha).blended_with(self.color2)


class Meteor(LightEffect):

    def __init__(self, color, tail_length=1):
        self.color = color
        # 1 provides a 'standard' length, 0.5 will halve, 2 will double
        self.tail_length = tail_length

    def get_color(self, progress, gradient):
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


class LightEffectTaskFactory:
    """ Makes light effect task creation more readable and concise """

    def __init__(self, pixel_adapter, midi_monitor):
        self.__pixel_adapter = pixel_adapter
        self.__midi_monitor = midi_monitor

    def task(self, effect, section, duration):
        return LightEffectTask(effect, section, duration, self.__pixel_adapter)

    def repeating_task(self, effect, section, duration, progress_offset):
        """ Creates an auto-repeating LightEffectTask """
        task = self.task(effect, section, duration)
        return RepeatingTask(task, duration, progress_offset)

    def note_off_task(self, effect, section, duration, pitch):
        """ Creates a LightEffectTask that pauses on the first time frame
        until the midi off event for the input pitch """
        task = self.task(effect, section, duration)
        return MidiOffTask(task, pitch, self.__midi_monitor)


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

    ### Task Protocol Implementation
    def start(self, time):
        self.__start_time = time

    def tick(self, time):
        for index, position in enumerate(self.section.positions):
            gradient = self.section.gradients[index]
            new_color = self.effect.get_color(
                self.__progress(time), gradient)
            existing_color = self.light_adapter.get_color(position)
            self.light_adapter.set_color(
                position, new_color.blended_with(existing_color))

    def is_finished(self, time):
        return self.__progress(time) == 1
    ### End Task Protocol Implementation

    def __progress(self, time):
        return min((time - self.__start_time) / self.duration, 1)



class RepeatingTask(Task):
    """ A task that auto-repeats a task. The task being repeated is reset every
    'duration' seconds. The task will be forcibly restarted if it isn't done
    by that point in time. The task is expected to execute in a deterministic 
    way as a function of time.
     """
    def __init__(self, task, duration, progress_offset=0.0):
        self.__repeating = True
        self.duration = duration
        self.progress_offset = progress_offset
        self.task = task
        self.__finished = False

    def start(self, time):
        self.task.start(time)
        self.__start_time = time

    def end(self):
        """ Call to stop the task """
        self.__finished = True

    def tick(self, time):
        delta_time = (time - self.__start_time) % self.duration
        self.task.tick(self.__start_time + delta_time)

    def is_finished(self, time):
        return self.__finished


class MidiOffTask(Task):
    """A special light effect task that reacts to the state of a particular
    MIDI note. The task sustains the first animation frame until the input note
    is off"""

    def __init__(self, task, pitch, midi_monitor):
        self.task = task
        self.pitch = pitch
        self.__midi_monitor = midi_monitor
        self.__note_duration = None  # TBD once note off is received

    def start(self, time):
        self.task.start(time)
        self.__midi_monitor.register(self)
        self.__start_time = time

    def received_midi(self, rtmidi_message):
        if (rtmidi_message.isNoteOff() and
                rtmidi_message.getNoteNumber() == self.pitch):
            self.__note_duration = time.time() - self.__start_time
            self.__midi_monitor.unregister(self)

    def tick(self, time):
        if not self.__note_duration:
            # if note hasn't been lifted yet, freeze at the first frame
            self.task.tick(self.__start_time)
        else:
            # once note has been lifted, allow the tick to start
            self.task.tick(time - self.__note_duration)

    def is_finished(self, time):
        if not self.__note_duration:
            return False
        else:
            return self.task.is_finished(time - self.__note_duration)
