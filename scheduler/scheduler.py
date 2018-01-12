import logging
import time
from abc import ABC, abstractmethod

logger = logging.getLogger("global")

class Task(ABC):
    """A "lightful" task gets scheduled to tick once per main loop until cfinished"""

    # if a unique id is set, then only one task can be running at a time using this id.
    # any tasks being scheduled will cancel existing tasks with matching id.
    uniquetag = None

    @abstractmethod
    def start(self):
        pass

    @abstractmethod
    def tick(self):
        pass

    @abstractmethod
    def is_finished(self):
        pass

class Scheduler:
    """Scheduler for recurring tasks"""

    def __init__(self):
        self.tasks = []
        self.__started = False

    def start(self):
        self.__started = True

    def stop(self):
        self.__started = False

    def add(self, task):
        """add a task"""

        if task.uniquetag is not None:
            self.remove_by_tag(task.uniquetag)

        self.tasks.append(task)
        task.start()

    def remove_by_tag(self, tag):
        """ remove task by its tag """
        for task in self.tasks:
            if task.uniquetag == tag:
                self.tasks.remove(task)
                return

    def remove(self, task):
        if task in self.tasks: # not efficient, but unlikely to ever matter
            self.tasks.remove(task)

    def clear(self):
        self.tasks.clear()

    def tick(self):
        """do the animation!"""

        # remove all finished effects
        self.tasks[:] = [task for task in self.tasks if not task.is_finished()]

        # TODO: sort the effects in render layer order
        for task in self.tasks:
            task.tick()


    def print_state(self):
        """ Prints scheduler state (e.g. active tasks) """
        logger.info("scheduler state:")
        for task in self.tasks:
            logger.info(" " + str(task))
