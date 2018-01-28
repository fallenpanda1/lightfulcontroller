import logging
from time import time

from lightful_tasks import RepeatingTask
from midi.conversions import convert_to_seconds
from midi.conversions import convert_to_ticks
from midi.player import PlayMidiTask
from midi.recorder import MidiRecorder

logger = logging.getLogger("global")


class MidiLooper:
    """Allows recording and looped playback of MIDI"""

    def __init__(self, tempo, ticks_per_beat, beats_per_measure, midi_monitor,
                 midi_scheduler):
        self.tempo = tempo  # reminder: nanoseconds per beat
        self.ticks_per_beat = ticks_per_beat
        self.beats_per_measure = beats_per_measure
        self.start_time = time()
        self.__midi_monitor = midi_monitor
        self.__midi_scheduler = midi_scheduler

        self.isplaying = False

    def ticks_per_measure(self):
        """returns number of ticks in a measure"""
        return self.ticks_per_beat * self.beats_per_measure

    def seconds_per_measure(self):
        """returns number of seconds in a measure"""
        return convert_to_seconds(
            ticks=self.ticks_per_measure(),
            tempo=self.tempo,
            ticks_per_beat=self.ticks_per_beat
        )

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
        self.__play_task = RepeatingTask(
            PlayMidiTask(
                self.__recorder.recorded_notes,
                self.__midi_monitor
            ),
            duration=self.seconds_per_measure()
        )
        self.__midi_scheduler.add(self.__play_task)

    def pause(self):
        self.__play_task.pause()

    def stop(self):
        self.__midi_scheduler.remove(self.__play_task)
