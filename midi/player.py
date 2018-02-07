import logging

import mido

from midi.conversions import convert_to_rt
from midi.conversions import convert_to_ticks
from scheduler.scheduler import Task

logger = logging.getLogger("global")


class PlayMidiTask(Task):
    """ Plays a MIDI file """
    @classmethod
    def withfile(cls, file_name, midi_monitor, ticks_per_beat):
        """ Load MIDI from file """
        midi_file = mido.MidiFile(file_name)
        return cls.with_mido_events(list(midi_file), midi_monitor,
                                    ticks_per_beat)

    @classmethod
    def with_mido_events(cls, mido_events, midi_monitor, ticks_per_beat):
        tempo = cls.__get_tempo(mido_events)
        return PlayMidiTask(cls.__create_rtmidi_events_by_tick(mido_events,
                                                               tempo,
                                                               ticks_per_beat),
                            midi_monitor=midi_monitor,
                            tempo=tempo,
                            ticks_per_beat=ticks_per_beat)

    # TODO: abstract 'list of midi notes' into an object
    def __init__(self, rtmidi_events_by_tick, midi_monitor, tempo,
                 ticks_per_beat):
        """ mido_events - List of mido events to play """
        self.__midi_out = midi_monitor

        self.tempo = tempo
        self.ticks_per_beat = ticks_per_beat
        self.__rtmidi_events_by_tick = rtmidi_events_by_tick
        self.__last_tick = -1


    # TODO: put this in a general utility location
    @classmethod
    def __get_tempo(cls, mido_events):
        # assume tempo is the first message
        tempo_message = mido_events[0]
        if not isinstance(tempo_message, mido.MetaMessage):
            logger.error("unexpected: first message isn't a tempo message?!")
        return tempo_message.tempo

    @classmethod
    def __create_rtmidi_events_by_tick(cls, mido_events, tempo, ticks_per_beat):
        """Given a list of mido events, keys them by MIDI tick number (relative
        to first event)"""
        cumulative_time = 0
        events_by_tick_dict = {}
        for event in mido_events:
            rtmidi_event = convert_to_rt(event)
            if rtmidi_event is None:
                continue
            cumulative_time += event.time
            current_tick = convert_to_ticks(cumulative_time, tempo,
                                            ticks_per_beat)
            current_tick_events = events_by_tick_dict.get(current_tick, [])
            current_tick_events.append(rtmidi_event)
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

        if current_tick not in self.__rtmidi_events_by_tick:
            return
        messages_to_send = self.__rtmidi_events_by_tick[current_tick]

        for rtmidi_message in messages_to_send:
            if rtmidi_message is not None and not self.is_muted:
                self.__midi_out.send_midi_message(rtmidi_message)

    def is_finished(self, time):
        # TODO: need to get last event to figure out when to finish
        return False
