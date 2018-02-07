import logging

import rtmidi

logger = logging.getLogger("global")


class MidiMonitor:

    def __init__(self):
        self.__MAX_PITCH = 255
        self.__observers = []
        self.__midi_in = rtmidi.RtMidiIn()
        self.__is_sustain_pedal_active = False

    def start(self):
        ports = range(self.__midi_in.getPortCount())

        # TODO: the input/output port setup logic is hacky and should be fixed
        # lets us send midi messages to the piano
        self.__midi_out = rtmidi.RtMidiOut()
        if ports:
            try:
                self.__midi_out.openPort(0)
            except:
                logger.error("tried and failed to open midi out on port 0")
                return

        if ports:
            try:
                self.__midi_in.openPort(0)
                logger.info("MidiMonitor started... now listening for midi in "
                            "on port 0: " + self.__midi_in.getPortName(0))
            except:
                logger.error("tried and failed to open midi in on port 0")
                return
        else:
            logger.info(
                'no midi input ports found, did not open MIDI connection')

    def stop(self):
        self.__midi_in.closePort()

    def listen_loop(self):
        # process all waiting midi input
        while True:
            rtmidi_message = self.__midi_in.getMessage(0)  # some timeout in ms
            if rtmidi_message is None:
                return

            self.handle_midi_message(rtmidi_message)

    def send_midi_message(self, rtmidi_message):
        """ Send a MIDI message """
        self.__midi_out.sendMessage(rtmidi_message)
        self.handle_midi_message(rtmidi_message)

    def handle_midi_message(self, rtmidi_message):

        # don't bother handling sustain pedal value changes unless its
        # state changed between on and off
        is_redundant = False

        rtmidi_message = rtmidi_message # set var in function scope
        if rtmidi_message.isController() and \
                rtmidi_message.getControllerNumber() == 64:
            sustain_value = rtmidi_message.getControllerValue()
            SUSTAIN_ON_THRESHOLD = 64
            is_active = (sustain_value > SUSTAIN_ON_THRESHOLD)
            is_redundant = \
                (is_active == self.__is_sustain_pedal_active)
            self.__is_sustain_pedal_active = is_active
            rtmidi_message = rtmidi.MidiMessage.controllerEvent(0, 64, 127 if is_active else 0)

        for observer in self.__observers:
            observer.received_midi(rtmidi_message)

    def register(self, observer):
        """ Register an observer for handling incoming MIDI events (multiple
        can be registered) """
        if observer not in self.__observers:
            self.__observers.append(observer)

    def unregister(self, observer):
        """ Unregister an observer """
        if observer in self.__observers:
            self.__observers.remove(observer)
