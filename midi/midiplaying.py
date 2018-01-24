import mido
import logging
from midi.conversions import convert_to_rt
from scheduler.scheduler import Task

logger = logging.getLogger("global")

DEFAULT_TEMPO = 500000
DEFAULT_TICKS_PER_BEAT = 9600


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
        self.__midi_out = midi_monitor

    def start(self, time):
        """ Play the midi """
        self.__last_stored_time = time
        self.is_muted = False
        logger.info("MidiPlayer -> play")

    def mute(self):
        self.is_muted = True

    def tick(self, time):
        """ loop that plays any scheduled MIDI notes (runs on main thread) """
        if self.is_finished(time):
            # uh, we technically shouldn't ever get here
            logger.error("trying to tick when task is over")
            return

        mido_message = self.__mido_events[0]
        delta_time = mido_message.time

        if time >= self.__last_stored_time + delta_time:
            if not isinstance(mido_message, mido.MetaMessage):
                rtmidi_message = convert_to_rt(mido_message)
                if rtmidi_message is not None and not self.is_muted:
                    self.__midi_out.send_midi_message(rtmidi_message)
            self.__mido_events.pop(0)
            time_drift = time - (self.__last_stored_time + delta_time)
            self.__last_stored_time = time - time_drift

    def is_finished(self, time):
        return len(self.__mido_events) == 0
