from mido import MidiFile, MidiTrack, MetaMessage
import logging

logger = logging.getLogger("global")

DEFAULT_TEMPO = 500000
DEFAULT_TICKS_PER_BEAT = 9600


class MidiFilter:
    """ Base abstract class for filtering Midi notes in a file """

    def filter_note_on(self, mido_message):
        """ Takes in a 'note on' and returns a new 'note on'
        Subclasses can optionally override """
        return mido_message

    def filter_note_off(self, mido_message):
        """ See 'filter_note_on' """
        return mido_message

    def will_save(self):
        """ Editor is about to save.
        Subclasses can optionally override """
        pass


class RangeVelocityFilter(MidiFilter):
    """ Increase/decrease velocity of notes in range. All notes
    in this range will be affected using the same multiplier """

    def __init__(self, note_range, multiplier):
        self.note_range = note_range
        self.multiplier = multiplier

    def filter_note_on(self, mido_message):
        new_message = mido_message.copy()
        if mido_message.note in self.note_range:
            new_message.velocity = round(mido_message.velocity * self.multiplier)
        return new_message


class FileSplitFilter(MidiFilter):
    """ Saves notes in the specified range into a different file """

    def __init__(self, other_file_name, note_range):
        self.note_range = note_range
        self.__output_file_name = other_file_name
        self.__output_file = MidiFile(ticks_per_beat=DEFAULT_TICKS_PER_BEAT)
        self.__track = MidiTrack()  # single track implementation for now
        self.__output_file.tracks.append(self.__track)
        # set the tempo (TODO: get this from the original midi)
        self.__track.append(MetaMessage('set_tempo', tempo=DEFAULT_TEMPO))

    def filter_note_on(self, mido_message):
        if not mido_message.note in self.note_range:
            self.__track.append(mido_message)
            return None  # don't return any note back
        return mido_message

    def filter_note_off(self, mido_message):
        if mido_message.note in self.note_range:
            self.__track.append(mido_message)
            return None  # don't return any note back
        return mido_message

    def will_save(self):
        self.__output_file.save(self.__output_file_name)


class MidiEditor:
    """ Applies effects/filters to contents of a MIDI file
    e.g. mute every note """
    def __init__(self, input_file_name, output_file_name):
        self.__input_file = MidiFile(input_file_name)
        self.__messages = []
        for track in self.__input_file.tracks:
            for msg in track:
                self.__messages.append(msg)
        self.output_file_name = output_file_name
        self.__output_file = MidiFile(ticks_per_beat=DEFAULT_TICKS_PER_BEAT)

        # assume single track for now
        self.__track = MidiTrack()
        self.__output_file.tracks.append(self.__track)
        self.__applied_filters = []

    def apply_filter(self, midifilter):
        """ loop through MIDI messages and applies filters """
        self.__applied_filters.append(midifilter)

        filtered_messages = []
        for mido_message in self.__messages:
            logger.info("message: " + str(mido_message))
            if mido_message.type == 'note_on':
                mido_message = midifilter.filter_note_on(mido_message)
            elif mido_message.type == 'note_off':
                mido_message = midifilter.filter_note_off(mido_message)

            if mido_message is not None:
                filtered_messages.append(mido_message)

        self.__messages = filtered_messages

    def save(self):
        for midifilter in self.__applied_filters:
            midifilter.will_save()

        self.__track.extend(self.__messages)
        self.__output_file.save(self.output_file_name)
