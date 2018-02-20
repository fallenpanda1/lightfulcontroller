import copy
import logging

from color import make_color
from light_engine.light_effect import Functional
from light_engine.light_effect import Gradient
from light_engine.light_effect import LightEffectTaskFactory
from light_engine.light_effect import LightSection
from light_engine.light_effect import Meteor
from light_engine.light_effect import SolidColor
from midi.metronome import MetronomeSyncedTask

logger = logging.getLogger("global")

# background is a blue/green animating gradient
BLUE_BG = make_color(0, 0, 70)
GREEN_BG = make_color(0, 0, 70)
YELLOW = make_color(220, 200, 60)
ORANGE = make_color(220, 140, 60)
ORANGE_RED = make_color(220, 100, 60)  # reminder: alpha is set
RED = make_color(160, 40, 40)
PURPLE = make_color(150, 20, 140, 127)


class SomethingJustLikeThisShow:
    """Just for debugging"""

    def __init__(self, scheduler, pixel_adapter, midi_monitor):
        self.__scheduler = scheduler
        self.__pixel_adapter = pixel_adapter
        self.__midi_monitor = midi_monitor
        self.__midi_monitor.register(self)

        self.lightfactory = LightEffectTaskFactory(self.__pixel_adapter,
            self.__midi_monitor)

        self.row1 = LightSection(range(10, 30))
        self.row2 = LightSection(reversed(range(30, 50)))
        self.row3 = LightSection(range(60, 80))
        self.row4 = LightSection(reversed(range(80, 100)))

        self.all = LightSection.merge_all(
            [self.row1, self.row2, self.row3, self.row4])

        self.row1_16 = LightSection(self.row1.positions[2: -2])
        self.row2_16 = LightSection(self.row2.positions[2: -2])
        self.row3_16 = LightSection(self.row3.positions[2: -2])
        self.row4_16 = LightSection(self.row4.positions[2: -2])

        self.all_16 = LightSection.merge_all(
            [self.row1_16, self.row2_16, self.row3_16, self.row4_16]
        )

        # mapping between note and light animations
        self.note_map = {}

        # channel 1 high map (for main melody)
        channel = 1
        pitches_to_lights = space_notes_out_into_section(
            pitches=filter_out_non_C_notes(range(58, 92)),
            lightsection=self.row4
        )
        for pitch, light_position in pitches_to_lights.items():
            self.note_map[(pitch, channel)] = self.lightfactory.note_off_task(
                effect=SolidColor(color=YELLOW),
                section=LightSection(range(light_position, light_position+2)),
                duration=0.15,
                pitch=pitch
            )

        # channel 1 low map (for last few measures where channel 1
        # substitutes the base in channel 2)
        channel = 1
        pitches_to_lights = space_notes_out_into_section(
            pitches=filter_out_non_C_notes(range(36, 50)),
            lightsection=self.row4
        )
        for pitch, light_position in pitches_to_lights.items():
            self.note_map[(pitch, channel)] = self.lightfactory.note_off_task(
                effect=SolidColor(color=YELLOW),
                section=LightSection([light_position]),
                duration=0.15,
                pitch=pitch
            )

        # channel 2 map
        channel = 2
        pitches_to_lights = space_notes_out_into_section(
            pitches=filter_out_non_C_notes(range(24, 48)),
            lightsection=self.row1
        )
        for pitch, light_position in pitches_to_lights.items():
            self.note_map[(pitch, channel)] = self.lightfactory.task(
                effect=Meteor(color=PURPLE),
                section=self.row1.reversed(),
                duration=1.2,
            )

        # channel 3 map
        channel = 3
        pitches_to_lights = space_notes_out_into_section(
            pitches=filter_out_non_C_notes(range(36, 66)),
            lightsection=self.row2
        )
        for pitch, light_position in pitches_to_lights.items():
            self.note_map[(pitch, channel)] = self.lightfactory.task(
                effect=SolidColor(color=RED.with_alpha(0.3)),
                section=LightSection(range(
                    light_position-2,
                    light_position+1+1)
                ),
                duration=0.5,
            )

        # channel 4 map
        channel = 4
        pitches_to_lights = space_notes_out_into_section(
            pitches=filter_out_non_C_notes(range(48, 80)),
            lightsection=self.row3
        )
        for pitch, light_position in pitches_to_lights.items():
            self.note_map[(pitch, channel)] = self.lightfactory.task(
                effect=SolidColor(color=ORANGE_RED.with_alpha(0.35)),
                section=LightSection(range(
                    light_position-2,
                    light_position+2+1)
                ),
                duration=0.5
            )

        self.initialize_lights()

        self.looper = None

    @property
    def looper(self):
        return self._looper

    @looper.setter
    def looper(self, looper):
        self._looper = looper
        # for convenience sake, assume we have a started looper
        if looper is not None:
            if not looper.is_started:
                logger.error("looper not started!!")

            self.add_looper_metronome_animation()

    def add_looper_metronome_animation(self):
        # visual time keeping
        self.last_saved_progress = 0
        self.sub_measures = 2
        threshold = 0.05
        def get_color_by_time(progress, gradient):
            # each metronome 'measure' loop is actually two 4 beat measures,
            # so we want to loop twice per measure
            progress = progress * self.sub_measures % 1
            self.last_saved_progress = progress

            # ??? make progress sliiightly behind for aesthetics ??
            # progress = max(0, progress)
            delta = abs(progress - gradient)

            if delta < threshold:
                return YELLOW.with_alpha((1 - delta / threshold) * 0.6)
            else:
                return YELLOW.with_alpha(0)

        task = self.lightfactory.task(
            effect=Functional(func=get_color_by_time),
            section=self.all_16.reversed(),
            duration=self.looper.metronome.seconds_per_measure()
        )
        metronome_synced = MetronomeSyncedTask(
            task=task,
            metronome=self.looper.metronome
        )
        self.__scheduler.add(metronome_synced)

    def last_saved_light_column_position(self):
        num_pixels = self.num_metronome_pixels
        position = round(self.last_saved_progress * num_pixels)
        if position == num_pixels:
            position = 0
        return position

    def initialize_lights(self):
        # add base layer for scheduler
        base_layer_row1 = self.lightfactory.repeating_task(
            effect=Gradient(color1=BLUE_BG, color2=GREEN_BG),
            section=self.row1,
            duration=7,
            progress_offset=0
        )
        self.__scheduler.add(base_layer_row1)

        base_layer_row2 = self.lightfactory.repeating_task(
            effect=Gradient(color1=BLUE_BG, color2=GREEN_BG),
            section=self.row2,
            duration=7,
            progress_offset=0.1
        )
        self.__scheduler.add(base_layer_row2)

        base_layer_row3 = self.lightfactory.repeating_task(
            effect=Gradient(color1=BLUE_BG, color2=GREEN_BG),
            section=self.row3,
            duration=7,
            progress_offset=0.2
        )
        self.__scheduler.add(base_layer_row3)

        base_layer_row4 = self.lightfactory.repeating_task(
            effect=Gradient(color1=BLUE_BG, color2=GREEN_BG),
            section=self.row4,
            duration=7,
            progress_offset=0.3
        )
        self.__scheduler.add(base_layer_row4)

    def reset_lights(self):
        self.__scheduler.clear()
        self.initialize_lights()

    def clear_lights(self):
        # TODO: this should be shareable between light shows
        self.__scheduler.clear()
        self.__scheduler.add(self.lightfactory.task(
            effect=SolidColor(color=make_color(0, 0, 0)),
            section=self.all,
            duration=1)
        )
        self.__scheduler.tick()
        self.__pixel_adapter.wait_for_ready_state()
        self.__pixel_adapter.push_pixels()
        self.__pixel_adapter.wait_for_ready_state()

    def received_midi(self, rtmidi_message):
        if rtmidi_message.isNoteOn():
            channel = rtmidi_message.getChannel()
            original_channel = channel

            # if a channel is recording, pretend MIDI is coming
            # from that channel instead of the usual channel 1
            if channel == 1 and self.looper is not None:
                for recording_channel in range(2, 10):
                    if self.looper.is_recording(recording_channel):
                        channel = recording_channel
                        break

            # pitch = rtmidi_message.getNoteNumber()
            # if (pitch, channel) in self.note_map:
            #     task = copy.copy(self.note_map[(pitch, channel)])
            #     # only dedupe channel 1
            #     unique_tag = (pitch, channel) if channel == 1 else None
            #     self.__scheduler.add(task, unique_tag=unique_tag)

            # EXPERIMENTAL STUFF
            section = None
            self.num_metronome_pixels = 16
            if channel == 2:
                section = self.row1
            elif channel == 3:
                section = self.row4  # least important channel
            elif channel == 4:
                section = self.row3
            elif channel == 1:
                section = self.row2
            position = section.positions[self.num_metronome_pixels + 1 - self.last_saved_light_column_position()]
            color = RED.with_alpha(0.9) if original_channel == 1 else PURPLE.with_alpha(0.6)
            task = self.lightfactory.task(
                effect=SolidColor(color=color),
                section=LightSection([position]),
                duration=self.looper.metronome.seconds_per_measure() / self.sub_measures * 0.6
            )
            self.__scheduler.add(task)


def space_notes_out_into_section(pitches, lightsection):
    """ Given a pitch range and a light section, evenly spaces out
    the pitches in the range into positions in the lightsection.
    E.g. To space out 5 C maj notes C6 - G6 into 10 lights, call
    space_notes_out_into_section(
        pitches=[60, 62, 64, 65, 67],
        lightsection=LightSection(range(0, 10))
    This will return:
    [
        60: 0,
        62: 2,
        64: 4,
        65: 6,
        67: 8,
    ]

    """
    return evenly_spaced_mapping(pitches, lightsection.positions)

def evenly_spaced_mapping(key_list, value_list):
    """ Creates a map between elements of first array and second array. If
    first and second aren't the same length, the mapping will space out
    elements of the second array (TODO WORD THIS BETTER.)
    Example: [1, 2, 3] -> [a, b, c, d, e, f] returns {1:a, 2:c, 3:e} """
    mapping = {}
    for key_index, key in enumerate(key_list):
        value_index = round(1.0 * key_index * len(value_list) / len(key_list))
        value = value_list[value_index]
        mapping[key] = value
    return mapping


def is_valid_C_major_pitch(pitch):
    p = pitch % 12
    if p == 0 or p == 2 or p == 4 or p == 5 or p == 7 or p == 9 or p == 11:
        return True
    return False


def filter_out_non_C_notes(pitch_list):
    return list(filter(is_valid_C_major_pitch, pitch_list))
