import logging

import mido

from midi.conversions import convert_to_rt
from midi.conversions import convert_to_ticks
from scheduler.scheduler import Task

logger = logging.getLogger("global")


class PlayMidiTask(Task):
    """ Plays a MIDI file """
    @classmethod
    def withfile(cls, file_name, midi_monitor):
        """ Load MIDI from file """
        midi_file = mido.MidiFile(file_name)
        return PlayMidiTask(list(midi_file), midi_monitor)

    def __init__(self, mido_events, midi_monitor):
        """ mido_events - List of mido events to play """
        self.__mido_events = mido_events.copy()
        self.__midi_out = midi_monitor

        # TODO: inject in init instead of mido event list searching madness
        self.tempo = self.__get_tempo(self.__mido_events)
        if self.tempo is None:
            logger.error("could not find tempo in list of mido events")

        # TODO: pass this in instead of hardcoding
        self.ticks_per_beat = 50

        self.__mido_events_by_tick = self.events_by_tick(mido_events)
        self.__last_tick = -1


    # TODO: put this in a general utility location
    def __get_tempo(self, mido_events):
        # assume tempo is the first message
        tempo_message = self.__mido_events[0]
        if not isinstance(tempo_message, mido.MetaMessage):
            logger.error("unexpected: first message isn't a tempo message?!")
        return tempo_message.tempo

    def events_by_tick(self, mido_events):
        """Given a list of mido events, keys them by MIDI tick number (relative
        to first event)"""
        cumulative_time = 0
        events_by_tick_dict = {}
        for event in mido_events:
            cumulative_time += event.time
            current_tick = convert_to_ticks(cumulative_time, self.tempo,
                                            self.ticks_per_beat)
            current_tick_events = events_by_tick_dict.get(current_tick, [])
            current_tick_events.append(event)
            events_by_tick_dict[current_tick] = current_tick_events
        return events_by_tick_dict

    def start(self):
        """ Play the MIDI """
        self.__last_stored_time = 0
        self.is_muted = False
        logger.info("MidiPlayer -> play")

    def mute(self):
        self.is_muted = True

    def tick(self, time):
        """ loop that plays any scheduled MIDI notes (runs on main thread) """
        if self.is_finished(time):
            # we're done already, so just return
            return

        current_tick = convert_to_ticks(time, self.tempo, self.ticks_per_beat)
        if current_tick > self.__last_tick + 1:
            logger.error("tick jump: " + str(current_tick - self.__last_tick))

        if current_tick == self.__last_tick:
            # don't handle same tick twice (this violates requirement that
            # tasks be deterministic, but it's not a huge deal in this case)
            return
        self.__last_tick = current_tick

        if current_tick not in self.__mido_events_by_tick:
            return
        messages_to_send = self.__mido_events_by_tick[current_tick]

        for mido_message in messages_to_send:
            if not isinstance(mido_message, mido.MetaMessage):
                rtmidi_message = convert_to_rt(mido_message)
                if rtmidi_message is not None and not self.is_muted:
                    self.__midi_out.send_midi_message(rtmidi_message)

    def is_finished(self, time):
        # TODO: need to get last event to figure out when to finish
        return False
