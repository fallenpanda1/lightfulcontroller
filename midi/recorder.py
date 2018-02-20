import logging
import sys
from time import time

import mido

from midi.conversions import convert_to_mido
from midi.conversions import convert_to_ticks

logger = logging.getLogger("global")

DEFAULT_TEMPO = 500000
DEFAULT_TICKS_PER_BEAT = 9600


class MidiRecorder:
    """ Records incoming MIDI """

    def __init__(self, file_name, midi_monitor, tempo=DEFAULT_TEMPO,
                 ticks_per_beat=DEFAULT_TICKS_PER_BEAT, channel=None):
        self.file_name = file_name
        self.__midi_monitor = midi_monitor
        self.tempo = tempo
        self.ticks_per_beat = ticks_per_beat
        self.channel = channel
        self.__midi_file = mido.MidiFile(ticks_per_beat=self.ticks_per_beat)

        # add track
        self.__track = mido.MidiTrack()  # single track implementation for now
        self.__midi_file.tracks.append(self.__track)

        # set the tempo
        self.__track.append(mido.MetaMessage('set_tempo', tempo=self.tempo))
        self.__last_message_time = None

    def start(self):
        """ Begins recording of all MIDI events """
        logger.info("MidiRecorder: begin recording midi events")
        self.recorded_notes = []
        self.__midi_monitor.register(self)
        self.__start_time = time()
        self.__last_message_time = self.__start_time
        # have to track pedal state because we get a LOT of pedal messages but
        # only really care if it's on or off
        self.__last_saved_is_pedal_on = False

    def is_recording(self):
        return self.__last_message_time is not None

    def stop(self, save_to_file=True):
        logger.info("MidiRecorder: finished recording midi events, "
                    "saved recording to " + self.file_name)
        self.__midi_monitor.unregister(self)
        if save_to_file:
            self.__midi_file.save(self.file_name)
        self.recorded_notes = list(self.__midi_file)
        self.__last_message_time = None

    def received_midi(self, rtmidi_message):
        if self.channel is not None and \
           self.channel != rtmidi_message.getChannel():
            return

        if not is_recognized_rtmidi_message(rtmidi_message):
            logger.error("received an unknown midi message")
            return

        if (rtmidi_message.isController() and
                rtmidi_message.getControllerNumber() == 64):
            # values taken from
            # https://www.cs.cmu.edu/~music/cmsip/readings/Standard-MIDI-file-format-updated.pdf
            is_pedal_on = rtmidi_message.getControllerValue() >= 64
            if self.__last_saved_is_pedal_on == is_pedal_on:
                # ignore pedal events that don't actually change its on state
                return
            self.__last_saved_is_pedal_on = is_pedal_on

        # logger.info("Recorder received msg: " + str(rtmidi_message))

        now = time()
        tick_delta = convert_to_ticks(now - self.__last_message_time,
                                      self.tempo, self.ticks_per_beat)
        self.__last_message_time = now

        mido_message = convert_to_mido(rtmidi_message, tick_delta)
        self.__track.append(mido_message)


def is_recognized_rtmidi_message(rtmidi_message):
    """ Is the input type string a midi type we recognize """
    m = rtmidi_message
    if m.isNoteOn() or m.isNoteOff():
        return True
    elif m.isController():
        if m.getControllerNumber() == 64:  # sustain pedal
            return True

    logger.error("received unknown/unimplemented midi message: " + str(m))
    return False
