import logging
logger = logging.getLogger("global")

from light_engine.light_effect import *
from color import *
from pygdisplay.screen import PygScreen
from pygdisplay.rain import RainPygDrawable
from pygdisplay.neopixel import NeopixelSimulationPygDrawable

class HangingDoorLightsShow:
    """Just for debugging"""

    def __init__(self, scheduler, pixel_adapter, pygscreen):
        self.__scheduler = scheduler
        self.__pixel_adapter = pixel_adapter
        self.__rain_drawable = None# RainPygDrawable()
        # self.__neopixel_drawable = NeopixelSimulationPygDrawable()
        # pygscreen.display_with_drawable(self.__neopixel_drawable)

    def received_note(self, midi_note):
        if midi_note.velocity == 0:
            return # don't need to handle not off events

        logger.info("received note:" + str(midi_note))
        offset = midi_note.pitch - 30
        if offset >= 30 and offset < 50:
            offset = 79 - offset
        elif offset >= 50:
            offset += 10
        simple_on_effect_task = MidiOffLightEffectTask(SolidColorLightEffect(color=make_color(220, 200, 60)), LightSection([offset]), 0.6, self.__pixel_adapter, midi_note)
        self.__scheduler.add(simple_on_effect_task)
        if self.__rain_drawable != None:
            self.__rain_drawable.add_raindrop_note(1.0 * (midi_note.pitch % 10) / 10)
