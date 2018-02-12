import copy
import logging

from color import make_color
from light_engine.light_effect import Gradient
from light_engine.light_effect import LightEffectTaskFactory
from light_engine.light_effect import LightSection
from light_engine.light_effect import Meteor
from light_engine.light_effect import SolidColor

logger = logging.getLogger("global")

# background is a blue/green animating gradient
BLUE_BG = make_color(0, 35, 50)
GREEN_BG = make_color(0, 60, 30)
YELLOW = make_color(220, 200, 60)


class SomethingJustLikeThisShow:
    """Just for debugging"""

    def __init__(self, scheduler, pixel_adapter, midi_monitor):
        self.__scheduler = scheduler
        self.__pixel_adapter = pixel_adapter
        self.__midi_monitor = midi_monitor
        self.__midi_monitor.register(self)
        self.lightfactory = LightEffectTaskFactory(self.__pixel_adapter,
            self.__midi_monitor)
        # TODO: this is exactly the kind of thing I don't want to have to do
        # for each song!!
        self.__is_in_end_mode = False

        self.row1 = LightSection(range(10, 30))
        self.row2 = LightSection(reversed(range(30, 50)))
        self.row3 = LightSection(range(60, 80))
        self.row4 = LightSection(reversed(range(80, 100)))

        # mapping between note and light animations
        self.note_map = {}

        # channel 1 map
        channel = 1
        pitches_to_lights = space_notes_out_into_section(
            pitches=range(36, 70),
            lightsection=self.row1
        )
        for pitch, light_position in pitches_to_lights.items():
            self.note_map[(pitch, channel)] = self.lightfactory.note_off_task(
                effect=SolidColor(color=YELLOW),
                section=LightSection([light_position]),
                duration=0.6,
                pitch=pitch
            )

        # channel 2 map
        channel = 2
        pitches_to_lights = space_notes_out_into_section(
            pitches=range(36, 70),
            lightsection=self.row2
        )
        for pitch, light_position in pitches_to_lights.items():
            self.note_map[(pitch, channel)] = self.lightfactory.note_off_task(
                effect=SolidColor(color=YELLOW),
                section=LightSection([light_position]),
                duration=0.6,
                pitch=pitch
            )

        # channel 3 map
        channel = 3
        pitches_to_lights = space_notes_out_into_section(
            pitches=range(36, 70),
            lightsection=self.row3
        )
        for pitch, light_position in pitches_to_lights.items():
            self.note_map[(pitch, channel)] = self.lightfactory.note_off_task(
                effect=SolidColor(color=YELLOW),
                section=LightSection([light_position]),
                duration=0.6,
                pitch=pitch
            )

        # channel 4 map
        channel = 4
        pitches_to_lights = space_notes_out_into_section(
            pitches=range(36, 70),
            lightsection=self.row4
        )
        for pitch, light_position in pitches_to_lights.items():
            self.note_map[(pitch, channel)] = self.lightfactory.note_off_task(
                effect=SolidColor(color=YELLOW),
                section=LightSection([light_position]),
                duration=0.6,
                pitch=pitch
            )

        self.initialize_lights()

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
            pitch = rtmidi_message.getNoteNumber()
            if (pitch, channel) in self.note_map:
                task = copy.copy(self.note_map[(pitch, channel)])
                self.__scheduler.add(task, unique_tag=(pitch, channel))


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