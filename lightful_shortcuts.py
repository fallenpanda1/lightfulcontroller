from pymaybe import maybe
import logging
import rtmidi
import sys
from midi.midieditor import MidiEditor
from midi.midieditor import RangeVelocityFilter
from midi.midirecording import MidiPlayer
from midi.midirecording import MidiRecorder

logger = logging.getLogger("global")


class LightfulKeyboardShortcuts:
    """ App-specific keyboard shortcuts """
    # NOTE: might want to refactor some/all of these
    # to not just be keyboard toggled
    def __init__(self, keyboard_monitor, pixel_adapter, virtual_client,
                 lights_show, midi_monitor, midi_player, scheduler):
        self.keyboard_monitor = keyboard_monitor
        self.pixel_adapter = pixel_adapter
        self.virtual_client = virtual_client
        self.lights_show = lights_show
        self.midi_monitor = midi_monitor
        self.midi_player = midi_player
        self.scheduler = scheduler

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
        k.add_keydown_callback('l', "(l)oop - begin midi looper",
                               self.play_recorded_midi_file)
        k.add_keydown_callback('b', "(b)eep (local speakers)", self.local_beep)
        k.add_keydown_callback('e', "(e)dit MIDI file", self.edit_midi_file)
        k.add_keydown_callback('q', "(q)uit", self.exit_app)

    def shortcuts_description(self):
        descriptions = self.keyboard_monitor.descriptions_by_key.values()
        return '\n'.join(descriptions)

    def exit_app(self):
        self.lights_show.clear_lights()
        self.pixel_adapter.stop()
        self.midi_monitor.stop()
        maybe(self.virtual_client).stop()
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
        self.midi_player = MidiPlayer.withfile("recording1.mid",
                                               self.midi_monitor)
        # reset lights show so that we always start any lights show
        # state, e.g. animations, at t=0 when recording starts
        self.lights_show.reset_lights()
        self.midi_player.play()

    def send_special_keyboard_event(self):
        self.midi_monitor.send_midi_message(rtmidi.MidiMessage().noteOff(0, 0))

    def local_beep(self):
        sys.stdout.write('\a')
        sys.stdout.flush()

    def edit_midi_file(self):
        editor = MidiEditor("recording1.mid", "recording1_baseline.mid")
        filter = RangeVelocityFilter(range(0, 70), 0)
        editor.apply_filter(filter)
        editor.save()

        editor = MidiEditor("recording1.mid", "recording1_melody.mid")
        filter = RangeVelocityFilter(range(70, 255), 0)
        editor.apply_filter(filter)
        editor.save()
        logger.info("write successful!")
