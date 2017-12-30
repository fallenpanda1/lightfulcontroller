import logging
from light_engine.light_effect import *
from color import *

logger = logging.getLogger("global")

class HangingDoorLightsShow:
    """Just for debugging"""

    def __init__(self, scheduler, pixel_adapter):
        self.__scheduler = scheduler
        self.__pixel_adapter = pixel_adapter

    def received_note(self, midi_note):
        logger.info("received note:" + str(midi_note))
        offset = midi_note.pitch - 32
        if offset >= 30 and offset < 50:
            offset = 79 - offset
        elif offset >= 50:
            offset += 10
        simple_on_effect_task = MidiOffLightEffectTask(SolidColorLightEffect(color=make_color(220, 200, 60)), LightSection([offset]), 0.6, self.__pixel_adapter, midi_note)
        self.__scheduler.add(simple_on_effect_task)
