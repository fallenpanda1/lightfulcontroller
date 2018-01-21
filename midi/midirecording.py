import mido
import time
import logging
import rtmidi

logger = logging.getLogger("global")

DEFAULT_TEMPO = 500000
DEFAULT_TICKS_PER_BEAT = 9600


class MidiPlayer:
    """ Plays a MIDI file """
    @classmethod
    def withfile(cls, file_name, virtual_midi_monitor):
        """ Load MIDI from file """
        midi_file = mido.MidiFile(file_name)
        return MidiPlayer(list(midi_file), virtual_midi_monitor)


    # TODO: rename--maybe virtual sender or something?
    def __init__(self, mido_events, virtual_midi_monitor):
        """ mido_events - List of mido events to play """
        self.__mido_events = mido_events
        self.__midi_out = virtual_midi_monitor

    def play(self):
        """ Play the midi """
        self.__last_stored_time = time.time()
        logger.info("MidiPlayer -> play")

    def play_loop(self):
        """ loop that plays any scheduled MIDI notes (runs on main thread) """
        if len(self.__mido_events) == 0:
            return

        mido_message = self.__mido_events[0]
        delta_time = mido_message.time
        now = time.time()

        if now >= self.__last_stored_time + delta_time:
            if not isinstance(mido_message, mido.MetaMessage):
                rtmidi_message = convert_to_rt(mido_message)
                if rtmidi_message is not None:
                    self.__midi_out.send_midi_message(rtmidi_message)
            self.__mido_events.pop(0)
            time_drift = now - (self.__last_stored_time + delta_time)
            self.__last_stored_time = now - time_drift


class MidiLooper:
    """ a 'measure' is defined as ??? """
    def __init(self, tempo, ticks_per_beat, beats_per_measure, midi_monitor):
        self.tempo = tempo  # reminder: nanoseconds per beat
        self.ticks_per_beat = ticks_per_beat
        self.start_time = start_time
        self.__midi_monitor = midi_monitor

        self.isplaying = false

    def ticks_per_measure(self):
        """ returns the number of ticks in a measure """
        return self.ticks_per_beat * self.beats_per_measure

    def record(self, start_time):
        """ Start recording 
        start_time: global start time
        """
        self.__recorder = MidiRecorder(
            file_name='',
            midi_monitor=self.__midi_monitor,
            tempo=self.tempo,
            ticks_per_beat=self.ticks_per_beat
        )
        self.__recorder.start()

        delta_time = time.time() - start_time
        self.delta_ticks = convert_to_ticks(delta_time, self.tempo, self.ticks_per_beat)
        logger.info("recording " + str(delta_time) + " seconds after start")
        logger.info("recording " + str(self.delta_ticks) + " ticks after start")

    def cancel_record(self):
        """ Cancel active recording """
        self.__recorder.stop(save_to_file=False)
        pass

    def save_record(self):
        """ Save active recording """
        self.__recorder.stop(save_to_file=False)
        recording = self.__recorder.recorded_notes
        # get the last measure of notes only, then set the first note's 
        # delta to the delta from measure start

        logger.info("save record before: " + str(recording))

        # add extra delta ticks to first note
        if len(recording) > 0:
            recording[0].time += self.delta_ticks

        logger.info("save record after: " + str(recording))

    def snap_to_measures(self, mido_messages):
        """ Snap each message into measures, based on global start time
        and beats per measure and ticks per beat and tempo """

        pass

    def play(self):
        """ Play last saved recording """
        self.isplaying = true

    def stop(self):
        """ Stop playing last saved recording """
        self.__midi_monitor.unregister(self)

    def tick(self, time):
        """ Tick for when the loop is playing """
        if not self.isplaying:
            return

    def play_loop(self):
        """ loop that plays any scheduled MIDI notes (runs on main thread) """
        if len(self.__mido_events) == 0:
            return

        mido_message = self.__mido_events[0]
        delta_time = mido_message.time
        now = time.time()

        if now >= self.__last_stored_time + delta_time:
            if not isinstance(mido_message, mido.MetaMessage):
                rtmidi_message = convert_to_rt(mido_message)
                if rtmidi_message is not None:
                    self.__midi_out.send_midi_message(rtmidi_message)
            self.__mido_events.pop(0)
            time_drift = now - (self.__last_stored_time + delta_time)
            self.__last_stored_time = now - time_drift        

    def received_midi(self, rtmidi_message):
        now = time.time()
        if (rtmidi_message.isNoteOn()
                or rtmidi_message.isNoteOff()
                or (rtmidi_message.isController()
                    and rtmidi_message.getControllerNumber() == 64)):

            self.__message_by_time[rtmidi_message] = now - self.__record_start_time


class MidiRecorder:
    """ Records incoming MIDI """

    def __init__(self, file_name, midi_monitor, tempo=DEFAULT_TEMPO, 
            ticks_per_beat=DEFAULT_TICKS_PER_BEAT):
        self.file_name = file_name
        self.__midi_monitor = midi_monitor
        self.tempo = tempo
        self.ticks_per_beat = ticks_per_beat
        self.__midi_file = mido.MidiFile(ticks_per_beat=self.ticks_per_beat)

        # add track
        self.__track = mido.MidiTrack()  # single track implementation for now
        self.__midi_file.tracks.append(self.__track)

        # set the tempo
        self.__track.append(mido.MetaMessage('set_tempo', tempo=self.tempo))
        self.__last_message_time = None

        self.in_memory_recording = []

    def start(self):
        """ Begins recording of all MIDI events """
        logger.info("MidiRecorder: begin recording midi events")
        self.recorded_notes = []
        self.__midi_monitor.register(self)
        self.__start_time = time.time()
        self.__last_message_time = self.__start_time
        # have to track pedal state because we get a LOT of pedal messages but
        # only really care if it's on or off
        self.__last_saved_is_pedal_on = False

    def is_recording(self):
        return self.__last_message_time is not None

    def stop(self, save_to_file=True):
        logger.info("MidiRecorder: finished recording midi events, "
                    "saved recording to " + self.file_name)
        self.__midi_monitor.unregister(self)
        if save_to_file:
            self.__midi_file.save(self.file_name)
        self.__last_message_time = None

    def received_midi(self, rtmidi_message):
        if not is_recognized_rtmidi_message(rtmidi_message):
            logger.error("received an unknown midi message")
            return

        if (rtmidi_message.isController() and
                rtmidi_message.getControllerNumber() == 64):
            # taken from
            # https://www.cs.cmu.edu/~music/cmsip/readings/Standard-MIDI-file-format-updated.pdf
            is_pedal_on = rtmidi_message.getControllerValue() >= 64
            if self.__last_saved_is_pedal_on == is_pedal_on:
                # ignore pedal events that don't actually change its on state
                return
            self.__last_saved_is_pedal_on = is_pedal_on

        logger.info("Recorder received msg: " + str(rtmidi_message))

        now = time.time()
        tick_delta = convert_to_ticks(now - self.__last_message_time, 
            self.tempo, self.ticks_per_beat)
        self.__last_message_time = now

        mido_message = convert_to_mido(rtmidi_message, tick_delta)
        self.__track.append(mido_message)

        in_memory_message = (mido_message, now - self.__start_time)
        self.in_memory_recording.append(in_memory_message)


def convert_to_ticks(time_in_seconds, tempo, ticks_per_beat):
    ticks_per_second = tempo * 1e-6 / ticks_per_beat
    return int(time_in_seconds / scale)


def convert_to_seconds(ticks, tempo, ticks_per_beat):
    ticks_per_second = tempo * 1e-6 / ticks_per_beat
    return ticks * scale

# Convenience conversions between mido and rtmidi. TODO: it'd be nice to
# monkey-patch these directly onto the classes


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


def is_recognized_rtmidi_message(rtmidi_message):
    """ Is the input type string a midi type we recognize """
    m = rtmidi_message
    if m.isNoteOn() or m.isNoteOff():
        return True
    elif m.isController():
        if m.getControllerNumber() == 64:  # sustain pedal
            return True

    logger.error("received unknown/unimplemented midi message: " + str(m))
    return False


class InMemoryMidiPlayer:
    """ Only really used for testing purposes at this point, e.g.
    to sanity check if anything is broken in MidiPlayer """

    def __init__(self, in_memory_recording, virtual_midi_monitor):
        """ In-memory recording is a list of tuples:
        (mido_message, delta_time_from_record_start) """
        self.in_memory_recording = in_memory_recording.copy(
        )  # make a copy since we'll be mutating
        self.__midi_out = virtual_midi_monitor

    def play(self):
        self.__start_time = time.time()

    def play_loop(self):
        if len(self.in_memory_recording) == 0:
            return

        mido_message, delta_time = self.in_memory_recording[0]
        now = time.time()

        if now >= self.__start_time + delta_time:
            self.__midi_out.send_midi_message(convert_to_rt(mido_message))
            self.in_memory_recording.pop(0)
