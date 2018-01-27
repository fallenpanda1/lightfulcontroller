import logging
import time
from abc import ABC, abstractmethod

logger = logging.getLogger("global")

class Task(ABC):
    """A 'lightful' time-based task.

    A task is scheduled to tick once per scheduler loop until done. For each
    tick, the task is given the current time. Tasks can be used for
    """

    # if a unique id is set, then only one task can be running at a time using
    # this id. any tasks being scheduled will cancel existing tasks with
    # matching id.
    uniquetag = None

    @abstractmethod
    def start(self):
        pass

    @abstractmethod
    def tick(self, time):
        """A task 'tick'.

        Args:
            time: time since task start, in seconds.
        """
        pass

    @abstractmethod
    def is_finished(self, time):
        pass


class Scheduler:
    """Scheduler for recurring tasks

    Attributes:
        task_tuples: (task, start_time, priority)
    """

    def __init__(self):
        self.task_tuples = []
        self.__started = False

    def start(self):
        self.__started = True

    def stop(self):
        self.__started = False

    def add(self, task, priority=0):
        """Add a task.

        Tasks can be assigned priorities. Within a scheduler object, tasks with
        higher priority are guaranteed to be executed before tasks with lower
        priority. For tasks assigned the same priority (or given no priority),
        the order of task execution is arbitrary. Callers using the priority
        system are encouraged to create their own enums or other abstractions
        to represent possible priorities.

        Args:
            task: Task to add.
            priority: Priority to give the task
        """

        start_time = time.time()

        # TODO: include uniquetag to the task tuple
        if task.uniquetag is not None:
            self.remove_by_tag(task.uniquetag)

        task_tuple = (task, start_time, priority)
        self.task_tuples.append(task_tuple)
        task.start()

    def remove_by_tag(self, tag):
        """ Remove task by its tag """
        for index, (task, _, _) in enumerate(self.task_tuples):
            if task.uniquetag == tag:
                del self.task_tuples[index]
                return

    def remove(self, task):
        for index, (existing_task, _, _) in enumerate(self.task_tuples):
            if task == existing_task:
                del self.task_tuples[index]

    def clear(self):
        self.task_tuples.clear()

    def tick(self):
        """do the animation!"""

        now = time.time()

        # remove all finished effects
        # TODO: clean up this ugly long line
        self.task_tuples[:] = [task_tuple for task_tuple in self.task_tuples if not task_tuple[0].is_finished(now - task_tuple[1])]

        # TODO: sort the effects in render layer order - note: I think because I'm not doing this correctly there's a bug with row1 turning all yellow
        for (task, start_time, _) in self.task_tuples:
            task.tick(now - start_time)

    def print_state(self):
        """ Prints scheduler state (e.g. active tasks) """
        logger.info("scheduler state:")
        for (task, _, _) in self.task_tuples:
            logger.info(" " + str(task))
