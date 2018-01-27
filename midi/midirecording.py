import logging
import sys
from time import time

import mido

# TODO: this should definitely be moved
from light_engine.light_effect import RepeatingTask
from midi.conversions import convert_to_mido
from midi.midiplaying import PlayMidiTask
from scheduler.scheduler import Task

logger = logging.getLogger("global")

DEFAULT_TEMPO = 500000
DEFAULT_TICKS_PER_BEAT = 9600


class MetronomeTask(Task):
    """ Metronome """
    def __init__(self, tempo, beats_per_measure):
        self.tempo = tempo
        self.beats_per_measure = beats_per_measure

    def start(self):
        self.last_tick_time = 0

    def tick(self, time):
        next_tick_time = self.last_tick_time + 1.0 * self.tempo / 1000000
        if time >= next_tick_time:
            self.last_tick_time = next_tick_time
            self._ring()

    def _ring(self):
        sys.stdout.write('\a')
        sys.stdout.flush()

    def is_finished(self, time):
        return False  # never finished


class MidiLooper:
    """  """
    def __init__(self, tempo, ticks_per_beat, beats_per_measure, midi_monitor,
                 midi_scheduler):
        self.tempo = tempo  # reminder: nanoseconds per beat
        self.ticks_per_beat = ticks_per_beat
        self.start_time = time()
        self.__midi_monitor = midi_monitor
        self.__midi_scheduler = midi_scheduler

        self.isplaying = False

    def ticks_per_measure(self):
        """ returns the number of ticks in a measure """
        return self.ticks_per_beat * self.beats_per_measure

    def record(self, start_time):
        """ Start recording
        start_time: global start time
        """
        self.__recorder = MidiRecorder(
            file_name='',
            midi_monitor=self.__midi_monitor,
            tempo=self.tempo,
            ticks_per_beat=self.ticks_per_beat
        )
        self.__recorder.start()

        delta_time = time() - start_time
        self.delta_ticks = convert_to_ticks(delta_time, self.tempo,
                                            self.ticks_per_beat)
        logger.info("recording " + str(delta_time) + " seconds after start")
        logger.info("recording " + str(self.delta_ticks) + " ticks after start")

    def is_recording(self):
        return self.__recorder.is_recording()

    def cancel_record(self):
        """ Cancel active recording """
        self.__recorder.stop(save_to_file=False)
        pass

    def save_record(self):
        """ Save active recording """
        self.__recorder.stop(save_to_file=False)
        recording = self.__recorder.recorded_notes
        # get the last measure of notes only, then set the first note's
        # delta to the delta from measure start

        logger.info("save record before: " + str(recording))

        # add extra delta ticks to first note
        if len(recording) > 0:
            recording[0].time += self.delta_ticks

        logger.info("save record after: " + str(recording))

    def snap_to_measures(self, mido_messages):
        """ Snap each message into measures, based on global start time
        and beats per measure and ticks per beat and tempo """

        pass

    def play(self):
        """ Play last saved recording """
        self.__play_task = RepeatingTask(PlayMidiTask(self.__recorder.recorded_notes,
                                        self.__midi_monitor))
        self.__midi_scheduler.add(self.__play_task)

    def pause(self):
        self.__play_task.pause()

    def stop(self):
        self.__midi_scheduler.remove(self.__play_task)


class MidiRecorder:
    """ Records incoming MIDI """

    def __init__(self, file_name, midi_monitor, tempo=DEFAULT_TEMPO,
                 ticks_per_beat=DEFAULT_TICKS_PER_BEAT):
        self.file_name = file_name
        self.__midi_monitor = midi_monitor
        self.tempo = tempo
        self.ticks_per_beat = ticks_per_beat
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
        self.__last_message_time = None

    def received_midi(self, rtmidi_message):
        if not is_recognized_rtmidi_message(rtmidi_message):
            logger.error("received an unknown midi message")
            return

        if (rtmidi_message.isController() and
                rtmidi_message.getControllerNumber() == 64):
            # taken from
            # https://www.cs.cmu.edu/~music/cmsip/readings/Standard-MIDI-file-format-updated.pdf
            is_pedal_on = rtmidi_message.getControllerValue() >= 64
            if self.__last_saved_is_pedal_on == is_pedal_on:
                # ignore pedal events that don't actually change its on state
                return
            self.__last_saved_is_pedal_on = is_pedal_on

        logger.info("Recorder received msg: " + str(rtmidi_message))

        now = time()
        tick_delta = convert_to_ticks(now - self.__last_message_time,
                                      self.tempo, self.ticks_per_beat)
        self.__last_message_time = now

        mido_message = convert_to_mido(rtmidi_message, tick_delta)
        self.__track.append(mido_message)


def convert_to_ticks(time_in_seconds, tempo, ticks_per_beat):
    ticks_per_second = tempo * 1e-6 / ticks_per_beat
    return round(time_in_seconds / ticks_per_second)


def convert_to_seconds(ticks, tempo, ticks_per_beat):
    ticks_per_second = tempo * 1e-6 / ticks_per_beat
    return ticks * ticks_per_second


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
