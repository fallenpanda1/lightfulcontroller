import logging
from time import time

from midi.conversions import convert_to_seconds
from midi.conversions import convert_to_ticks
from midi.metronome import MetronomeSyncedTask
from midi.metronome import MetronomeTask
from midi.player import PlayMidiTask

logger = logging.getLogger("global")


class MidiLoopRecorder:

    def __init__(self, metronome, midi_monitor, channel):
        self.__metronome = metronome
        self.__midi_monitor = midi_monitor
        self.channel = channel
        self.notes_by_tick = {}
        self.__is_recording = False

    def start(self):
        """Begin recording"""
        self.__midi_monitor.register(self)
        self.__is_recording = True

    def stop(self):
        """Stop recording"""
        self.__midi_monitor.unregister(self)
        self.__is_recording = False

    def is_recording(self):
        return self.__is_recording

    def received_midi(self, rtmidi_message):
        if rtmidi_message.getChannel() != 1:
            # assume only channel one has real time user input. TODO: enum this?
            return

        current_tick = self.__metronome.current_tick

        m = rtmidi_message
        if m.isNoteOn() or m.isNoteOff() or \
                (m.isController() and m.getControllerNumber() == 64):
            notes = self.notes_by_tick.get(current_tick, [])
            m.setChannel(self.channel)
            notes.append(m)
            self.notes_by_tick[current_tick] = notes


class MidiLooper:
    """Allows recording and looped playback of MIDI"""

    def __init__(self, tempo, ticks_per_beat, beats_per_measure, midi_monitor,
                 midi_scheduler):
        self.tempo = tempo  # reminder: nanoseconds per beat
        self.ticks_per_beat = ticks_per_beat
        self.beats_per_measure = beats_per_measure
        self.start_time = time()
        # TODO: metronome should be DI'ed since loopers and players
        # will share the same one
        self.metronome = MetronomeTask(
            tempo=self.tempo,
            ticks_per_beat=self.ticks_per_beat,
            beats_per_measure=self.beats_per_measure
        )
        self.__midi_monitor = midi_monitor
        self.__midi_scheduler = midi_scheduler
        self.__play_tasks = {}
        self.current_channel = -1

        self.is_started = False

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

    def start(self):
        if self.is_started is True:
            return
        self.is_started = True
        self.__midi_scheduler.add(self.metronome)

    def record(self, start_time, channel):
        """ Start recording
        start_time: global start time
        """
        self.current_channel = channel
        self.__recorder = MidiLoopRecorder(
            metronome=self.metronome,
            midi_monitor=self.__midi_monitor,
            channel=channel
        )
        self.__recorder.start()

        delta_time = time() - start_time
        self.delta_ticks = convert_to_ticks(delta_time, self.tempo,
                                            self.ticks_per_beat)

    def is_recording(self):
        return self.__recorder.is_recording()

    def cancel_record(self):
        """ Cancel active recording """
        self.__recorder.stop()
        pass

    def save_record(self):
        """ Save active recording """
        self.__recorder.stop()

    def play(self, channel):
        """ Play last saved recording """
        self.__play_tasks[channel] = MetronomeSyncedTask(
            self.metronome,
            PlayMidiTask(
                self.__recorder.notes_by_tick,
                self.__midi_monitor,
                self.tempo,
                self.ticks_per_beat
            )
        )
        self.__midi_scheduler.add(self.__play_tasks[channel])

    def pause(self, channel):
        self.__play_tasks[channel].pause()

    def stop(self):
        logger.info("stopping!")
        for task in self.__play_tasks:
            self.__midi_scheduler.remove(task) 
        self.__midi_scheduler.remove(self.metronome)
