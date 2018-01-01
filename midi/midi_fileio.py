from mido import Message, MetaMessage, MidiFile, MidiTrack
import mido
from time import time
import logging
import rtmidi
import threading
import queue

logger = logging.getLogger("global")

class MidiPlayer:
    """ Plays a MIDI file """
    def __init__(self, file_name, virtual_midi_monitor): # TODO: rename--maybe virtual sender or something?
        self.file_name = file_name
        self.__midi_out = virtual_midi_monitor
        self.__midi_message_queue = queue.Queue()

    def play(self):
        logger.info("playing midi file: " + self.file_name)
        self.__midi_file = MidiFile(self.file_name)
        note_scheduler = threading.Thread(target=self.schedule_notes, args=())
        note_scheduler.daemon = True
        note_scheduler.start()

    def schedule_notes(self):
        """ schedules MIDI notes to be played on a background thread """
        for message in MidiFile(self.file_name).play():
            self.__midi_message_queue.put(message)

    def play_loop(self):
        """ loop that plays any scheduled MIDI notes (runs on main thread) """
        while not self.__midi_message_queue.empty():
            # get() normally blocks for next message, but since we check that queue isn't empty this should return immediately
            message = self.__midi_message_queue.get() 
            self.__midi_out.send_midi_message(self.get_rtmidi_message_from_mido_message(message))

    # TODO: Put this logic into some sort of adapter pattern
    def get_rtmidi_message_from_mido_message(self, mido_message):
        if mido_message.type == 'note_on':
            return rtmidi.MidiMessage().noteOn(mido_message.channel, mido_message.note, mido_message.velocity)
        elif mido_message.type == 'note_off':
            return rtmidi.MidiMessage().noteOff(mido_message.channel, mido_message.note)
        elif mido_message.type == 'control_change':
            return rtmidi.MidiMessage().controllerEvent(mido_message.channel, mido_message.control, mido_message.value)
        return "unknown mido message"

class MidiRecorder:
    """ Records incoming MIDI """
    def __init__(self, file_name, midi_monitor):
        self.file_name = file_name
        self.__midi_monitor = midi_monitor
        self.__recorded_notes = []
        self.__midi_file = MidiFile(ticks_per_beat=50)
        self.__tempo = 500000
        
        # add track
        self.__track = MidiTrack() # single track implementation for now
        self.__midi_file.tracks.append(self.__track)

        # set the tempo
        self.__track.append(MetaMessage('set_tempo', tempo=self.__tempo))
        self.__last_message_time = None

    def start(self):
        """ Begins recording of all MIDI events """
        logger.info("MidiRecorder: begin recording midi events")
        self.__midi_monitor.register(self)
        self.__last_message_time = time()

    def is_recording(self):
        return self.__last_message_time != None

    def stop(self):
        logger.info("MidiRecorder: finished recording midi events, saved recording to " + self.file_name)
        self.__midi_monitor.unregister(self)
        self.__midi_file.save(self.file_name)
        self.__recorded_notes = []
        self.__last_message_time = None

    def received_note(self, midi_note):
        logger.info(midi_note)
        
        if midi_note.velocity > 0:
            self.__track.append(Message('note_on', note=midi_note.pitch, velocity=midi_note.velocity, time=self.current_delta()))
        else:
            self.__track.append(Message('note_on', note=midi_note.pitch, velocity=0, time=self.current_delta()))

    def received_sustain_pedal_event(self, is_pedal_on):
        if is_pedal_on:
            logger.info("pedal on")
            self.__track.append(Message('control_change', control=64, value=127, time=self.current_delta()))
        else:
            logger.info("pedal off")
            self.__track.append(Message('control_change', control=64, value=0, time=self.current_delta()))

    def current_delta(self):
        if self.__last_message_time == None:
            self.__last_message_time = time()

        current_time = time()
        delta_seconds = current_time - self.__last_message_time
        delta_ticks = self.second2tick(delta_seconds, ticks_per_beat=self.__midi_file.ticks_per_beat, tempo=self.__tempo)
        self.__last_message_time = current_time
        return delta_ticks

    def second2tick(self, second, ticks_per_beat, tempo):
        """(COPY PASTED FROM MIDO since I can't find how to access it)
        Convert absolute time in seconds to ticks.
        Returns absolute time in ticks for a chosen MIDI file time
        resolution (ticks per beat, also called PPQN or pulses per quarter
        note) and tempo (microseconds per beat).
        """
        scale = tempo * 1e-6 / ticks_per_beat
        return int(second / scale)
        return delta_ticks
