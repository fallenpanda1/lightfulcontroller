import logging
from light_engine.light_effect import (
    LightSection, LightEffectTask, LightEffectTaskFactory,
    MidiOffLightEffectTask, RepeatingTask)
from light_engine.light_effect import SolidColor, Meteor, Gradient
from color import make_color
import copy

logger = logging.getLogger("global")

# background is a blue/green animating gradient
BLUE_BG = make_color(0, 35, 50)
GREEN_BG = make_color(0, 60, 30)
YELLOW = make_color(220, 200, 60)


class HangingDoorLightsShow:
    """Just for debugging"""

    def __init__(self, scheduler, pixel_adapter, midi_monitor):
        self.__scheduler = scheduler
        self.__pixel_adapter = pixel_adapter
        self.__midi_monitor = midi_monitor
        self.__midi_monitor.register(self)
        self.lightfactory = LightEffectTaskFactory(self.__pixel_adapter)
        # TODO: this is exactly the kind of thing I don't want to have to do
        # for each song!!
        self.__is_in_end_mode = False

        self.row1 = LightSection(range(10, 30))
        self.row2 = LightSection(list(reversed(range(30, 50))))
        self.row3 = LightSection(range(60, 80))
        self.row4 = LightSection(list(reversed(range(80, 100))))

        self.row1and4 = self.row1.merged_with(self.row4)
        self.all = LightSection.merge_all(
            [self.row1, self.row2, self.row3, self.row4])

        # mapping between note and light animations
        self.note_map = {}

        # base map
        pitches_to_lights = evenly_spaced_mapping(
            first=range(36, 70),
            second=self.row2.positions)
        for pitch, light_position in pitches_to_lights.items():
            task = self.lightfactory.task(
                effect=SolidColor(color=YELLOW),
                section=LightSection([light_position]),
                duration=0.6
            )
            self.note_map[pitch] = MidiOffLightEffectTask(
                task, pitch, self.__midi_monitor)

        # melody map
        pitches_to_lights = evenly_spaced_mapping(
            first=filter_out_non_C_notes(range(70, 97)),
            second=self.row3.positions)
        for pitch, light_position in pitches_to_lights.items():
            task = self.lightfactory.task(
                effect=SolidColor(color=YELLOW),
                section=LightSection([light_position]),
                duration=0.6
            )
            self.note_map[pitch] = MidiOffLightEffectTask(
                task, pitch, self.__midi_monitor)

        # low notes
        for pitch in [29, 31, 33, 34, 36]:
            self.note_map[pitch] = self.lightfactory.task(
                effect=Meteor(color=YELLOW),
                section=self.row1and4.reversed(),
                duration=1.6
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
            duration=1))
        self.__scheduler.tick()
        self.__pixel_adapter.wait_for_ready_state()
        self.__pixel_adapter.push_pixels()
        self.__pixel_adapter.wait_for_ready_state()

    def received_midi(self, rtmidi_message):
        if rtmidi_message.isNoteOn():
            logger.info("received note_on:" + str(rtmidi_message))

            pitch = rtmidi_message.getNoteNumber()
            if pitch in self.note_map:
                task = copy.copy(self.note_map[pitch])
                # only allow 1 task to run at a time for one pitch
                task.uniquetag = pitch
                self.__scheduler.add(task)
        elif rtmidi_message.isNoteOff() and rtmidi_message.getNoteNumber() == 0:
            # hacky special message
            self.special_message_received()

    def special_message_received(self):
        if not self.__is_in_end_mode:
            logger.info("transitioned to end")

            # keys being played at the end
            key_range = [36, 43, 48, 64, 67, 71, 74]

            final_chord_mapping = evenly_spaced_mapping(
                key_range, range(0, 20))
            for pitch, position in final_chord_mapping.items():
                gradient_cross_section = self.all.positions_with_gradient(
                    (position + 1) * 1.0 / 20)
                task = self.lightfactory.task(
                    effect=SolidColor(color=make_color(YELLOW)),
                    section=LightSection(gradient_cross_section),
                    duration=0.3
                )
                self.note_map[pitch] = MidiOffLightEffectTask(
                    task, pitch, self.__midi_monitor)


def evenly_spaced_mapping(first, second):
    """ Creates a map between elements of first array and second array. If
    first and second aren't the same length, the mapping will space out
    elements of the second array (TODO WORD THIS BETTER.)
    Example: [1, 2, 3] -> [a, b, c, d, e, f] returns {1:a, 2:c, 3:e} """
    mapping = {}
    for key_index, key in enumerate(first):
        value_index = round(1.0 * key_index * len(second) / len(first))
        value = second[value_index]
        mapping[key] = value
    return mapping


def is_valid_C_major_pitch(pitch):
    p = pitch % 12
    if p == 0 or p == 2 or p == 4 or p == 5 or p == 7 or p == 9 or p == 11:
        return True
    return False


def filter_out_non_C_notes(pitch_list):
    return list(filter(is_valid_C_major_pitch, pitch_list))
