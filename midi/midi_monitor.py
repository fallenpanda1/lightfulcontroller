import rtmidi
import logging

logger = logging.getLogger("global")

class MidiNote:
    def __init__(self, pitch, velocity):
        self.pitch = pitch
        self.velocity = velocity

    def __str__(self):
        """aka 'toString', for debugging convenience"""
        return "pitch: " + str(self.pitch) + ", vel: " + str(self.velocity)

class MidiMonitor:

    def __init__(self):
        self.__MAX_PITCH = 255
        self.__note_list = [0] * self.__MAX_PITCH 
        self.__observers = []
        self._midi_in = rtmidi.RtMidiIn()
        self.__is_sustain_pedal_active = False

    def start(self):
        ports = range(self._midi_in.getPortCount())
        
        # lets us send midi messages to the piano
        self.__midi_out = rtmidi.RtMidiOut()
        try:
            self.__midi_out.openPort(0)
        except:
            pass

        if not ports:
            logger.error('no midi input ports found, did not open MIDI connection')
            #return # TODO: throw an error that this can't be started?
        try:
            self._midi_in.openPort(0)
        except:
            pass
        logger.info("MidiMonitor started... now listening for midi in on port 0: " + self._midi_in.getPortName(0))

    def stop(self):
        self._midi_in.closePort()

    def listen_loop(self):
        # process all waiting midi input
        while True:
            message = self._midi_in.getMessage(0) # some timeout in ms
            if message is None:
                return
            self.handle_midi_message(message)

    def send_midi_message(self, rtmidi_message):
        """ Send a MIDI message """
        self.__midi_out.sendMessage(rtmidi_message)
        self.handle_midi_message(rtmidi_message)

    def handle_midi_message(self, message):
        if message.isNoteOn():
            existing_note = self.__note_list[message.getNoteNumber()]
            if existing_note is not None and existing_note is not 0:
                # edge case where recorded MIDI and live MIDI play the same key at the same time.
                # in this case edit the existing note so animations on the old note end correctly.
                existing_note.velocity = message.getVelocity()
                return

            note = MidiNote(message.getNoteNumber(), message.getVelocity())
            self.__note_list[message.getNoteNumber()] = note
            self.__notify_received_note(note)
        elif message.isNoteOff():
            note = self.__note_list[message.getNoteNumber()]
            if note == None:
                # throw an "error" once I figure out how to even do that :D
                logger.error("note off message received for a note that was never turned on")
                return
            note.velocity = 0
            self.__note_list[message.getNoteNumber()] = None
            self.__notify_received_note(note)
        elif message.isController():
            if message.getControllerNumber() == 64: # sustain pedal
                value = message.getControllerValue() # 0 - 127 depending on how hard pedal is pressed
                if value > 0 and not self.__is_sustain_pedal_active:
                    self.__notify_sustain_pedal_event(True, deltatime)
                    self.__is_sustain_pedal_active = True
                elif value == 0 and self.__is_sustain_pedal_active:
                    self.__notify_sustain_pedal_event(False, deltatime)
                    self.__is_sustain_pedal_active = False

    def __notify_received_note(self, midi_note, deltatime):
        for observer in self.__observers:
            observer.received_note(midi_note, deltatime)

    def __notify_sustain_pedal_event(self, is_pedal_on, deltatime):
        for observer in self.__observers:
            sustain_event_attr = getattr(observer, "received_sustain_pedal_event", None)
            if callable(sustain_event_attr):
                observer.received_sustain_pedal_event(is_pedal_on, deltatime)

    def register(self, observer):
        """ Register an observer for handling incoming MIDI events (multiple can be registered) """
        if not observer in self.__observers:
            self.__observers.append(observer)
 
    def unregister(self, observer):
        """ Unregister an observer """
        if observer in self.__observers:
            self.__observers.remove(observer)

    def send_virtual_note(self, offset):
        # TODO: refactor to use send_midi_message
        test_note_on_message = rtmidi.MidiMessage().noteOn(0, 30 + offset, 127)
        test_note_off_message = rtmidi.MidiMessage().noteOff(0, 30 + offset)
        self.handle_midi_message(test_note_on_message)
        self.handle_midi_message(test_note_off_message)
