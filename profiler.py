import logging
import time
from collections import OrderedDict

logger = logging.getLogger("global")


class Profiler:

    def __init__(self, seconds_per_average=2):
        self.last_recorded_time = time.time()
        self.times_by_id = OrderedDict()
        self.seconds_per_average = seconds_per_average
        self.last_printed_average_time = None
        self.enabled = True

    def time(self, identifier):
        """ Print delta time since last time() call """
        # TODO: im sure I can think of a better name of this function...
        if not self.enabled:
            return

        logger.info(str(identifier) + ": " +
                    str(self.increment_time_and_get_delta()))

    def avg(self, identifier):
        """ Print average time deltas for identifier using frequency specified
        by seconds_per_average. For use with heavily looping areas """
        if not self.enabled:
            return

        delta_time = self.increment_time_and_get_delta()

        if identifier not in self.times_by_id:
            self.times_by_id[identifier] = (0, 0, 0)

        cumulative_time, counter, max_time = self.times_by_id[identifier]
        cumulative_time += delta_time
        max_time = max(delta_time, max_time)
        counter += 1
        self.times_by_id[identifier] = (cumulative_time, counter, max_time)

        now = time.time()

        if self.last_printed_average_time is None:
            self.last_printed_average_time = now

        if (now > self.last_printed_average_time +
                self.seconds_per_average):
            logger.info("Average Times: ")
            for identifier, triplet in self.times_by_id.items():
                cumulative_time, counter, max_time = triplet

                DISPLAY_LEN = 20
                fixed_length_id = str(identifier).ljust(DISPLAY_LEN)[:DISPLAY_LEN]
                logger.info(fixed_length_id + ": " +
                            "%.3f" % (cumulative_time / counter * 1000) + "ms" +
                            " max: %.3f" % (max_time * 1000) + "ms")

                # reset back to nothing (but still keep keys around to maintain
                # original order for OrderedDict)
                self.times_by_id[identifier] = (0, 0, 0)
            self.last_printed_average_time = now

    def increment_time_and_get_delta(self):
        now = time.time()
        delta_time = now - self.last_recorded_time
        self.last_recorded_time = now
        return delta_time
