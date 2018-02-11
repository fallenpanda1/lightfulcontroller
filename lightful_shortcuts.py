import logging
import time
from threading import Timer

import rtmidi
from pymaybe import maybe

from midi.editor import MidiEditor
from midi.editor import RangeVelocityFilter
from midi.looper import MidiLooper
from midi.metronome import MetronomeTask
from midi.player import PlayMidiTask
from midi.recorder import MidiRecorder

logger = logging.getLogger("global")


class LightfulKeyboardShortcuts:
    """ App-specific keyboard shortcuts """
    # NOTE: might want to refactor some/all of these
    # to not just be keyboard toggled
    def __init__(self, keyboard_monitor, pixel_adapter,
                 lights_show, midi_monitor, animation_scheduler,
                 midi_scheduler):
        self.keyboard_monitor = keyboard_monitor
        self.pixel_adapter = pixel_adapter
        self.lights_show = lights_show
        self.midi_monitor = midi_monitor
        self.animation_scheduler = animation_scheduler
        self.midi_scheduler = midi_scheduler

        self.midi_recorder = None
        self.midi_looper = None

    def register_shortcuts(self):
        k = self.keyboard_monitor
        k.register_callback('o', "(o)pen serial connection",
                               self.pixel_adapter.start)
        k.register_callback('c', "(c)lose serial connection",
                               self.pixel_adapter.stop)
        k.register_callback('r', "(r)ecord MIDI input to a save file, or "
                               "if a file is recording, then save recording",
                               self.toggle_record_midi_file)
        k.register_callback('p', "(p)lay saved MIDI recording",
                               self.play_recorded_midi_file)
        
        loop_keyboard_monitor = k.register_nested_monitor(
            'l', "(l)oop mode - loop mode!"
        )
        l = loop_keyboard_monitor
        l.register_callback('s', "(s)tart loop mode", self.begin_loop_mode)
        l.register_callback('b', "(b) note on/off event 1",
                               self.send_note_on_off_event1)
        l.register_callback('n', "(n)ote on/off event 2",
                               self.send_note_on_off_event2)
        l.register_callback('m', "(m) note on/off event 3",
                               self.send_note_on_off_event3)
        l.register_callback('2', "(2) record/play/pause channel 2", self.toggle_channel_2)
        l.register_callback('3', "(3) record/play/pause channel 3", self.toggle_channel_3)
        l.register_callback('4', "(4) record/play/pause channel 4", self.toggle_channel_4)
        l.register_callback('5', "(5) record/play/pause channel 5", self.toggle_channel_5)
        l.register_callback('6', "(6) record/play/pause channel 6",
                            self.toggle_channel_6)
        l.register_callback('7', "(7) record/play/pause channel 7",
                            self.toggle_channel_7)
        l.register_callback('q', "(q)uit (back to previous menu)", self.quit_loop_mode)
        
        k.register_callback('b', "(b)eep (local speakers)",
                               self.add_metronome)
        k.register_callback('e', "(e)dit MIDI file", self.edit_midi_file)
        k.register_callback('q', "(q)uit", self.exit_app)
 
    def begin_loop_mode(self):
        if self.midi_looper is not None:
            return
        self.midi_looper = MidiLooper(
            tempo=410000,
            ticks_per_beat=50,
            beats_per_measure=16,
            midi_monitor=self.midi_monitor,
            midi_scheduler=self.midi_scheduler
        )
        self.midi_looper.start()

    def quit_loop_mode(self):
        self.end_loop_mode()
        self.keyboard_monitor.remove_nested_monitor()

    def end_loop_mode(self):
        self.midi_looper.stop()
        self.midi_looper = None

    def toggle_channel_2(self):
        self.toggle_loop(2)

    def toggle_channel_3(self):
        self.toggle_loop(3)

    def toggle_channel_4(self):
        self.toggle_loop(4)

    def toggle_channel_5(self):
        self.toggle_loop(5)

    def toggle_channel_6(self):
        self.toggle_loop(6)

    def toggle_channel_7(self):
        self.toggle_loop(7)

    def toggle_loop(self, channel):
        looper = self.midi_looper
        if not looper.has_been_recorded(channel):
            logger.info("A")
            looper.record(time.time(), channel)
            looper.play(channel)
        elif looper.is_recording(channel):
            logger.info("B")
            looper.save_record(channel)
        elif looper.is_playing(channel):
            logger.info("C")
            looper.pause(channel)  # TODO: this is more of a mute than a pause
        elif not looper.is_playing(channel):
            logger.info("D")
            looper.play(channel)

    def shortcuts_description(self):
        descriptions = self.keyboard_monitor.descriptions_by_key.values()
        return '\n'.join(descriptions)

    def exit_app(self):
        self.lights_show.clear_lights()
        self.pixel_adapter.stop()
        self.midi_monitor.stop()
        exit()

    # TODO: recording/playing seem like they deserve being in a dedicated
    # file somewhere else
    def toggle_record_midi_file(self):
        """ record input midi, or stop and save active recording """
        if self.midi_recorder is None:
            self.midi_recorder = MidiRecorder("recording1.mid",
                                              self.midi_monitor)
            self.midi_recorder.start()
            self.lights_show.reset_lights()
        else:
            self.midi_recorder.stop()  # TODO: maybe fork into cancel vs save?
            self.midi_recorder = None

    def play_recorded_midi_file(self):
        """ play recorded midi file """
        self.play_midi_task = PlayMidiTask.withfile("recording1.mid",
                                                    midi_monitor=self.midi_monitor,
                                                    ticks_per_beat=50)
        # reset lights show so that we always start any lights show
        # state, e.g. animations, at t=0 when recording starts
        self.lights_show.reset_lights()
        self.midi_scheduler.add(self.play_midi_task)

    def send_special_keyboard_event(self):
        self.midi_monitor.send_midi_message(rtmidi.MidiMessage().noteOff(0, 0))

    def add_metronome(self):
        self.metronome_task = MetronomeTask(500000, 50, 8)
        self.midi_scheduler.add(self.metronome_task)

    def edit_midi_file(self):
        editor = MidiEditor("recording1.mid", "recording1_baseline.mid")
        velocity_filter = RangeVelocityFilter(range(0, 70), 0)
        editor.apply_filter(velocity_filter)
        editor.save()

        editor = MidiEditor("recording1.mid", "recording1_melody.mid")
        velocity_filter = RangeVelocityFilter(range(70, 255), 0)
        editor.apply_filter(velocity_filter)
        editor.save()
        logger.info("write successful!")

    def send_note_on_off_event1(self):
        self.send_note_on_off_event(58)

    def send_note_on_off_event2(self):
        self.send_note_on_off_event(60)

    def send_note_on_off_event3(self):
        self.send_note_on_off_event(62)


    def send_note_on_off_event(self, pitch):
        """Note on event, then after a delay, note off event"""
        self.send_note_on_event(pitch)

        Timer(0.2, self.send_note_off_event, [pitch]).start()

    def send_note_on_event(self, pitch):
        note_on = rtmidi.MidiMessage().noteOn(0, pitch, 100)
        self.midi_monitor.send_midi_message(note_on)

    def send_note_off_event(self, pitch):
        note_off = rtmidi.MidiMessage().noteOff(0, pitch)
        self.midi_monitor.send_midi_message(note_off)