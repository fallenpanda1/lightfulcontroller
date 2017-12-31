import logging
logger = logging.getLogger("global")

from light_engine.light_effect import *
from color import *
from rain import PygRainScreen

class HangingDoorLightsShow:
    """Just for debugging"""

    def __init__(self, scheduler, pixel_adapter, rain_screen):
        self.__scheduler = scheduler
        self.__pixel_adapter = pixel_adapter
        self.__rain_screen = rain_screen

    def received_note(self, midi_note):
        logger.info("received note:" + str(midi_note))
        offset = midi_note.pitch - 30
        if offset >= 30 and offset < 50:
            offset = 79 - offset
        elif offset >= 50:
            offset += 10
        simple_on_effect_task = MidiOffLightEffectTask(SolidColorLightEffect(color=make_color(220, 200, 60)), LightSection([offset]), 0.6, self.__pixel_adapter, midi_note)
        self.__scheduler.add(simple_on_effect_task)
        self.__rain_screen.add_raindrop_note(1.0 * (midi_note.pitch % 10) / 10)
