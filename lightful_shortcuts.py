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
        k.add_keydown_callback('o', "(o)pen serial connection",
                               self.pixel_adapter.start)
        k.add_keydown_callback('c', "(c)lose serial connection",
                               self.pixel_adapter.stop)
        k.add_keydown_callback('r', "(r)ecord MIDI input to a save file, or "
                               "if a file is recording, then save recording",
                               self.toggle_record_midi_file)
        k.add_keydown_callback('p', "(p)lay saved MIDI recording",
                               self.play_recorded_midi_file)
        k.add_keydown_callback('l', "(l)oop - begin midi looper, or "
                               "if already recording, then loop the recording",
                               self.toggle_loop)
        k.add_keydown_callback('b', "(b)eep (local speakers)",
                               self.add_metronome)
        k.add_keydown_callback('e', "(e)dit MIDI file", self.edit_midi_file)
        k.add_keydown_callback('q', "(q)uit", self.exit_app)
        k.add_keydown_callback('n', "(n)ote on/off event",
                               self.send_note_on_off_event)

    def shortcuts_description(self):
        descriptions = self.keyboard_monitor.descriptions_by_key.values()
        return '\n'.join(descriptions)

    def exit_app(self):
        self.lights_show.clear_lights()
        self.pixel_adapter.stop()
        self.midi_monitor.stop()
        # TODO: stop the render process!
        #maybe(self.virtual_client).stop()
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
                                                    self.midi_monitor)
        # reset lights show so that we always start any lights show
        # state, e.g. animations, at t=0 when recording starts
        self.lights_show.reset_lights()
        self.midi_scheduler.add(self.play_midi_task)

    def toggle_loop(self):
        if not self.midi_looper:
            self.midi_looper = MidiLooper(
                tempo=500000,
                ticks_per_beat=120,
                beats_per_measure=4,
                midi_monitor=self.midi_monitor,
                midi_scheduler=self.midi_scheduler
            )
            self.midi_looper.record(time.time())
        else:
            self.midi_looper.save_record()
            self.midi_looper.play()


    def send_special_keyboard_event(self):
        self.midi_monitor.send_midi_message(rtmidi.MidiMessage().noteOff(0, 0))

    def add_metronome(self):
        self.metronome_task = MetronomeTask(500000, 8)
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

    def send_note_on_off_event(self):
        """Note on event, then after a delay, note off event"""
        self.send_note_on_event()

        Timer(0.2, self.send_note_off_event, ()).start()

    def send_note_on_event(self):
        note_on = rtmidi.MidiMessage().noteOn(0, 60, 100)
        self.midi_monitor.send_midi_message(note_on)

    def send_note_off_event(self):
        note_off = rtmidi.MidiMessage().noteOff(0, 60)
        self.midi_monitor.send_midi_message(note_off)