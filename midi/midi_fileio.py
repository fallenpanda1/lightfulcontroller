import mido
import time
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
        """ Play the file """
        logger.info("playing midi file: " + self.file_name)
        self.__midi_file = mido.MidiFile(self.file_name)
        note_scheduler = threading.Thread(target=self.schedule_notes, args=())
        note_scheduler.daemon = True
        note_scheduler.start()

    def schedule_notes(self):
        """ schedules MIDI notes to be played on a background thread """
        for message in mido.MidiFile(self.file_name).play():
            self.__midi_message_queue.put(message)

    def play_loop(self):
        """ loop that plays any scheduled MIDI notes (runs on main thread) """
        while not self.__midi_message_queue.empty():
            # get() normally blocks for next message, but since we check that queue isn't empty this should return immediately
            mido_message = self.__midi_message_queue.get() 
            self.__midi_out.send_midi_message(convert_to_rt(mido_message))

class InMemoryMidiPlayer:
    def __init__(self, in_memory_recording, virtual_midi_monitor):
        """ In-memory recording is a list of tuples: (mido_message, delta_time_from_record_start) """
        self.in_memory_recording = in_memory_recording.copy() # make a copy since we'll be mutating
        self.__midi_out = virtual_midi_monitor

    def play(self):
        self.__start_time = time.time()
        
        # parent_connection, child_connection = Pipe()
        #self.process = multiprocessing.Process(target=self.play_loop, args=(child_connection))

    def play_loop(self):
        if len(self.in_memory_recording) == 0:
            return

        mido_message, delta_time = self.in_memory_recording[0]
        current_time = time.time()

        if current_time >= self.__start_time + delta_time:
            self.__midi_out.send_midi_message(convert_to_rt(mido_message))
            self.in_memory_recording.pop(0)
            logger.info("playing delay: " + str(current_time - (self.__start_time + delta_time)))

class MidiRecorder:
    """ Records incoming MIDI """
    def __init__(self, file_name, midi_monitor):
        self.file_name = file_name
        self.__midi_monitor = midi_monitor
        self.__recorded_notes = []
        self.__midi_file = mido.MidiFile(ticks_per_beat=960)
        self.__tempo = 500000
        
        # add track
        self.__track = mido.MidiTrack() # single track implementation for now
        self.__midi_file.tracks.append(self.__track)

        # set the tempo
        self.__track.append(mido.MetaMessage('set_tempo', tempo=self.__tempo))
        self.__last_message_time = None

        self.in_memory_recording = []

    def start(self):
        """ Begins recording of all MIDI events """
        logger.info("MidiRecorder: begin recording midi events")
        self.__midi_monitor.register(self)
        self.__start_time = time.time()
        self.__last_message_time = self.__start_time
        self.__last_saved_is_pedal_on = False # have to track pedal state because we get a LOT of pedal messages but only really care if its on or off

    def is_recording(self):
        return self.__last_message_time != None

    def stop(self):
        logger.info("MidiRecorder: finished recording midi events, saved recording to " + self.file_name)
        self.__midi_monitor.unregister(self)
        self.__midi_file.save(self.file_name)
        self.__recorded_notes = []
        self.__last_message_time = None

    def received_midi(self, rtmidi_message):
        if not is_recognized_rtmidi_message(rtmidi_message):
            logger.error("received an unknown midi message")
            return

        if rtmidi_message.isController() and rtmidi_message.getControllerNumber() == 64:
            is_pedal_on = rtmidi_message.getControllerValue() >= 64 # taken from https://www.cs.cmu.edu/~music/cmsip/readings/Standard-MIDI-file-format-updated.pdf
            if self.__last_saved_is_pedal_on == is_pedal_on:
                # ignore pedal events that don't actually change its on state
                return
            self.__last_saved_is_pedal_on = is_pedal_on
        
        logger.info("Recorder received msg: " + str(rtmidi_message))

        current_time = time.time()
        tick_delta = self.convert_to_ticks(current_time - self.__last_message_time)
        logger.info("time delta: " + str(current_time - self.__last_message_time))
        logger.info("time->tick->time: " + str(self.convert_to_seconds(tick_delta)))
        self.__last_message_time = current_time

        mido_message = convert_to_mido(rtmidi_message, tick_delta)
        self.__track.append(mido_message)

        in_memory_message = (mido_message, current_time - self.__start_time)
        self.in_memory_recording.append(in_memory_message)

    def current_delta(self):
        current_time = time.time()
        delta_seconds = current_time - self.__last_message_time
        delta_ticks = self.second2tick(delta_seconds, ticks_per_beat=self.__midi_file.ticks_per_beat, tempo=self.__tempo)
        self.__last_message_time = current_time
        return delta_ticks

    def convert_to_ticks(self, time_in_seconds):
        scale = self.__tempo * 1e-6 / self.__midi_file.ticks_per_beat
        return int(time_in_seconds / scale)

    def convert_to_seconds(self, ticks):
        scale = self.__tempo * 1e-6 / self.__midi_file.ticks_per_beat
        return ticks * scale

# Convenience conversions between mido and rtmidi. TODO: it'd be nice to monkey-patch these directly onto the classes

def convert_to_rt(mido_message):
    """ Convert a mido message to an rtmidi message """
    if mido_message.type == 'note_on':
        return rtmidi.MidiMessage().noteOn(mido_message.channel, mido_message.note, mido_message.velocity)
    elif mido_message.type == 'note_off':
        return rtmidi.MidiMessage().noteOff(mido_message.channel, mido_message.note)
    elif mido_message.type == 'control_change':
        return rtmidi.MidiMessage().controllerEvent(mido_message.channel, mido_message.control, mido_message.value)
    return "unknown mido message"

def convert_to_mido(rtmidi_message, time):
    """ Convert an rtmidi message plus corresponding delta time into a mido message """
    m = rtmidi_message
    if m.isNoteOn():
        return mido.Message('note_on', note=m.getNoteNumber(), velocity=m.getVelocity(), time=time)
    elif m.isNoteOff():
        return mido.Message('note_off', note=m.getNoteNumber(), velocity=0, time=time)
    elif m.isController():
        if m.getControllerNumber() == 64: # sustain pedal
            return mido.Message('control_change', control=64, value=m.getControllerValue(), time=time)

    logger.error("received unknown/unimplemented midi message: " + str(m))

def is_recognized_rtmidi_message(rtmidi_message):
    """ Is the input type string a midi type we recognize """
    m = rtmidi_message
    if m.isNoteOn() or m.isNoteOff():
        return True
    elif m.isController():
        if m.getControllerNumber() == 64: # sustain pedal
            return True

    logger.error("received unknown/unimplemented midi message: " + str(m))
    return False
