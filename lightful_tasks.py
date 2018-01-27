from scheduler.scheduler import Task

"""General tasks useful for the lightful app"""

class RepeatingTask(Task):
    """ A task that auto-repeats a task. The task being repeated is reset every
    'duration' seconds. The task will be forcibly restarted if it isn't done
    by that point in time. The task is expected to execute in a deterministic
    way as a function of time.
     """
    def __init__(self, task, duration, progress_offset=0.0):
        self.__repeating = True
        self.duration = duration
        self.progress_offset = progress_offset
        self.task = task
        self.__finished = False

    def start(self):
        """ Task implementation """
        self.task.start()

    def tick(self, time):
        """ Task implementation """
        modded_time = time % self.duration
        self.task.tick(modded_time)

    def is_finished(self, time):
        """ Task implementation """
        return self.__finished

    def end(self):
        """ Call to stop repeating the task """
        self.__finished = True

