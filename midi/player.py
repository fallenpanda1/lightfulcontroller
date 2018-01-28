import logging

import mido

from midi.conversions import convert_to_rt
from scheduler.scheduler import Task

logger = logging.getLogger("global")


class PlayMidiTask(Task):
    """ Plays a MIDI file """
    @classmethod
    def withfile(cls, file_name, midi_monitor):
        """ Load MIDI from file """
        midi_file = mido.MidiFile(file_name)
        return PlayMidiTask(list(midi_file), midi_monitor)

    # TODO: rename--maybe virtual sender or something?
    def __init__(self, mido_events, midi_monitor):
        """ mido_events - List of mido events to play """
        self.__mido_events = mido_events.copy()
        self.__mido_events_and_times = \
            self.events_with_cumulative_times(mido_events)
        self.__midi_out = midi_monitor
        self.tempo = self.__get_tempo(self.__mido_events)
        if self.tempo is None:
            logger.error("could not find tempo in list of mido events")

    # TODO: put this in a general utility location
    def __get_tempo(self, mido_events):
        # assume tempo is the first message
        tempo_message = self.__mido_events[0]
        if not isinstance(tempo_message, mido.MetaMessage):
            logger.error("unexpected: first message isn't a tempo message?!")
        return tempo_message.tempo

    def events_with_cumulative_times(self, mido_events):
        """Given a list of mido events, returns an array of tuples:
        (mido_event, cumulative_time). This is to get around the fact
        that mido events are represented by time deltas from the previous
        event rather than delta from song start."""
        cumulative_time = 0
        event_time_tuples = []
        for event in mido_events:
            cumulative_time += event.time
            event_time_tuples.append((event, cumulative_time))
        return event_time_tuples

    def start(self):
        """ Play the midi """
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

        if self.__last_stored_time > time:
            # TODO: PlayMidiTask is a fundamentally flawed task since it
            # maintains state about previously stored time. Here we make a
            # guess that if the last stored time is greater than the current
            # time then the caller intended to re-start the task, but ideally
            # we shouldn't have to assume anything about the caller.
            self.__last_stored_time = 0

        messages_to_send = self.__messages_in_time_range(
            start=self.__last_stored_time,
            end=time
        )

        for mido_message in messages_to_send:
            if not isinstance(mido_message, mido.MetaMessage):
                rtmidi_message = convert_to_rt(mido_message)
                if rtmidi_message is not None and not self.is_muted:
                    self.__midi_out.send_midi_message(rtmidi_message)

        self.__last_stored_time = time

    def is_finished(self, time):
        last_message, last_message_time = self.__mido_events_and_times[-1]
        # need to check last stored time in addition to current time because
        # the final note will be played once time has already gone slightly
        # over the final note's scheduled play time
        return (self.__last_stored_time > last_message_time
                and time > last_message_time)

    def __messages_in_time_range(self, start, end):
        messages = []
        for message, time in self.__mido_events_and_times:
            if time >= start and time < end:
                messages.append(message)
        return messages
