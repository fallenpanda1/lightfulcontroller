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

    def start(self):
        ports = range(self._midi_in.getPortCount())
        
        if not ports:
            logger.error('no midi input ports found')
            return # TODO: throw an error that this can't be started?
        self._midi_in.openPort(0)
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

    def handle_midi_message(self, message):
        if message.isNoteOn():
            note = MidiNote(message.getNoteNumber(), message.getVelocity())
            self.__note_list[message.getNoteNumber()] = note
            self.notify_received_note(note)
        elif message.isNoteOff():
            note = self.__note_list[message.getNoteNumber()]
            if note == None:
                # throw an "error" once I figure out how to even do that :D
                logger.error("note off message received for a note that was never turned on")
            note.velocity = 0
            self.__note_list[message.getNoteNumber()] = None
        elif message.isController():
            pass
            # midi.getControllerNumber() and midi.getControllerValue()
            # reminder: number = 127? for sustain pedal, value > 0 sustains

    def notify_received_note(self, midi_note):
        for observer in self.__observers:
            observer.received_note(midi_note)

    def register(self, observer):
        if not observer in self.__observers:
            self.__observers.append(observer)
 
    def unregister(self, observer):
        if observer in self.__observers:
            self.__observers.remove(observer)

class VirtualMidiMonitor(MidiMonitor):
    """ Listens to Midi on the virtual port and (TODO) allows for simulating midi events via keyboard events on the curses window """
    def __init__(self):
        super(VirtualMidiMonitor, self).__init__()
        self.__virtual_midi_out = rtmidi.RtMidiOut()

    def start(self):
        self.__virtual_midi_out.openVirtualPort()
        super(VirtualMidiMonitor, self).start()
        logger.info("VirtualMidiMonitor started... midi in virtual port and midi out virtual port set up")

    def send_virtual_note(self):
        test_note_on_message = rtmidi.MidiMessage().noteOn(2, 60, 127)
        self.__virtual_midi_out.sendMessage(test_note_on_message)
