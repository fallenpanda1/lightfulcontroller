import time
import logging
logger = logging.getLogger("global")

class Profiler:
	def __init__(self, seconds_per_average=2):
		self.last_recorded_time = time.time()
		self.times_for_identifier = {}
		self.seconds_per_average = seconds_per_average
		self.last_printed_average_time = time.time()
		self.enabled = True

	def time(self, identifier):
		""" Print delta time since last time() call """
		# TODO: im sure I can think of a better name of this function...
		if not self.enabled:
			return
		
		logger.info(str(identifier) + ": " + str(self.increment_time_and_get_delta()))

	def avg(self, identifier):
		""" Print average time deltas for identifier using frequency specified by seconds_per_average. For use with heavily looping areas """
		if not self.enabled:
			return

		delta_time = self.increment_time_and_get_delta()
		
		if identifier not in self.times_for_identifier:
			self.times_for_identifier[identifier] = (0, 0)

		cumulative_time, counter = self.times_for_identifier[identifier]
		cumulative_time += delta_time
		counter += 1
		self.times_for_identifier[identifier] = (cumulative_time, counter)

		if self.last_printed_average_time is None:
			self.last_printed_average_time = time.time()

		current_time = time.time()
		if current_time > self.last_printed_average_time + self.seconds_per_average:
			logger.info("Average Times: ")
			for identifier, pair in self.times_for_identifier.items():
				cumulative_time, counter = pair
				logger.info(str(identifier) + ": " + str(cumulative_time / counter))
			self.last_printed_average_time = current_time


	def increment_time_and_get_delta(self):
		current_time = time.time()
		delta_time = current_time - self.last_recorded_time
		self.last_recorded_time = current_time
		return delta_time