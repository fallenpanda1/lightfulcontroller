import logging
import time
from abc import ABC, abstractmethod

logger = logging.getLogger("global")

class Task(ABC):
    """A "lightful" task gets scheduled to tick once per main loop until cfinished"""

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
        self.__tasks = []
        self.__started = False

    def start(self):
        self.__started = True

    def stop(self):
        self.__started = False

    def add(self, task):
        """add a light effect"""
        self.__tasks.append(task)
        task.start()

    def clear(self):
        self.__tasks.clear()

    def tick(self):
        """do the animation!"""

        # filter out all finished effects
        self.__tasks[:] = [task for task in self.__tasks if not task.is_finished()]

        # TODO: sort the effects in render layer order
        for task in self.__tasks:
            task.tick()

class DebugTask(Task):
    def tick(self):
        logger.info("tick!")

    def is_finished(self):
        return False
