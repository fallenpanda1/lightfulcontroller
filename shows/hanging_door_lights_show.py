import logging
logger = logging.getLogger("global")

from light_engine.light_effect import *
from color import *
from pygdisplay.screen import PygScreen
from pygdisplay.rain import RainPygDrawable
from pygdisplay.neopixel import NeopixelSimulationPygDrawable

class PitchToSubSectionMapper:
    """ 
    Given a range of (ordered) pitches and a light section with multiple lights, does an evenly spaced out mapping
    between pitches and lights.
    """
    def __init__(self, ordered_pitches, light_section):
        self.pitches = ordered_pitches
        self.light_section = light_section

    def section_for_pitch(self, pitch):
        pitch_index = None
        for index, element in enumerate(self.pitches):
            if pitch == element:
                pitch_index = index

        if pitch_index is None:
            return None

        ratio = pitch_index / len(self.pitches)
        section_position = round(ratio * len(self.light_section.positions))
        subsection_value = self.light_section.positions[section_position]
        return LightSection([subsection_value])

class HangingDoorLightsShow:
    """Just for debugging"""

    def __init__(self, scheduler, pixel_adapter, pygscreen):
        self.__scheduler = scheduler
        self.__pixel_adapter = pixel_adapter
        self.__rain_drawable = None# RainPygDrawable()
        # self.__neopixel_drawable = NeopixelSimulationPygDrawable()
        # pygscreen.display_with_drawable(self.__neopixel_drawable)

        self.row1 = LightSection(range(10, 30))
        self.row2 = LightSection(list(reversed(range(30, 50))))
        self.row3 = LightSection(range(60, 80))
        self.row4 = LightSection(list(reversed(range(80, 100))))
        self.row1and2 = LightSection(interleave_lists(self.row1.positions, self.row2.positions))
        self.row3and4 = LightSection(flatten_lists([self.row3.positions, self.row4.positions]))
        self.all = LightSection(flatten_lists([self.row1.positions, self.row2.positions, self.row3.positions, self.row4.positions]))

        base_mapper = PitchToSubSectionMapper(filter_out_non_C_notes(range(36, 65)), self.row1and2)
        melody1_mapper = PitchToSubSectionMapper(filter_out_non_C_notes(range(67, 87)), self.row3)

        self.mappers = [base_mapper, melody1_mapper]

        # add base layer for scheduler
        base_layer_effect = RepeatingTask(LightEffectTask(GradientLightEffect(color1=make_color(0, 35, 50), color2=make_color(0, 60, 30)), self.row1, 10, pixel_adapter), progress_offset = 0)
        scheduler.add(base_layer_effect)

        base_layer_effect = RepeatingTask(LightEffectTask(GradientLightEffect(color1=make_color(0, 35, 50), color2=make_color(0, 60, 30)), self.row2, 10, pixel_adapter), progress_offset = 0.2)
        scheduler.add(base_layer_effect)

        base_layer_effect = RepeatingTask(LightEffectTask(GradientLightEffect(color1=make_color(0, 35, 50), color2=make_color(0, 60, 30)), self.row3, 10, pixel_adapter), progress_offset = 0.4)
        scheduler.add(base_layer_effect)

        base_layer_effect = RepeatingTask(LightEffectTask(GradientLightEffect(color1=make_color(0, 35, 50), color2=make_color(0, 60, 30)), self.row4, 10, pixel_adapter), progress_offset = 0.6)
        scheduler.add(base_layer_effect)

    def received_note(self, midi_note, time):
        if midi_note.velocity == 0:
            return # don't need to handle not off events

        logger.info("received note:" + str(midi_note))

        # TODO: we should make the mappers more magical and take care of the light effects as well
        # e.g. a mapper takes a set of pitches and maps it to the scheduling of actual animations
        for index, mapper in enumerate(self.mappers):
            section = mapper.section_for_pitch(midi_note.pitch)
            if section is not None:
                color = make_color(220, 200, 60) if index == 1 else make_color(120, 0, 200)
                simple_on_effect_task = MidiOffLightEffectTask(SolidColorLightEffect(color=color), section, 0.4, self.__pixel_adapter, midi_note)
                self.__scheduler.add(simple_on_effect_task)
                break
        
        if self.__rain_drawable != None:
            self.__rain_drawable.add_raindrop_note(1.0 * (midi_note.pitch % 10) / 10)

def is_valid_C_major_pitch(pitch):
    p = pitch % 12
    if p == 0 or p == 2 or p == 4 or p == 5 or p == 7 or p == 9 or p == 11:
        return True
    return False

def filter_out_non_C_notes(pitch_list):
    return list(filter(is_valid_C_major_pitch, pitch_list))

def flatten_lists(lists):
    """ [[1, 2, 3], [4, 5, 6]] -> [1, 2, 3, 4, 5, 6] """
    return [item for sublist in lists for item in sublist]

def interleave_lists(list1, list2):
    """ [0, 0, 0], [1, 1, 1] -> [0, 1, 0, 1, 0, 1]
    Note: two lists must be the same length
    """
    return [val for pair in zip(list1, list2) for val in pair]
