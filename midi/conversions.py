# Conversions between mido and rtmidi libraries
import mido
import rtmidi
import logging

logger = logging.getLogger("global")


def convert_to_rt(mido_message):
    """ Convert a mido message to an rtmidi message """
    if mido_message.type == 'note_on':
        return rtmidi.MidiMessage().noteOn(
            mido_message.channel, mido_message.note, mido_message.velocity)
    elif mido_message.type == 'note_off':
        return rtmidi.MidiMessage().noteOff(
            mido_message.channel, mido_message.note)
    elif mido_message.type == 'control_change':
        return rtmidi.MidiMessage().controllerEvent(
            mido_message.channel, mido_message.control, mido_message.value)
    return None


def convert_to_mido(rtmidi_message, time):
    """ Convert an rtmidi message plus corresponding delta time into a mido
    message """
    m = rtmidi_message
    if m.isNoteOn():
        return mido.Message('note_on', note=m.getNoteNumber(),
                            velocity=m.getVelocity(), time=time)
    elif m.isNoteOff():
        return mido.Message('note_off', note=m.getNoteNumber(),
                            velocity=0, time=time)
    elif m.isController():
        if m.getControllerNumber() == 64:  # sustain pedal
            return mido.Message('control_change', control=64,
                                value=m.getControllerValue(), time=time)

    logger.error("received unknown/unimplemented midi message: " + str(m))
