import logging
import time
from abc import ABC, abstractmethod

logger = logging.getLogger("global")


class Task(ABC):
    """A 'lightful' time-based task.

    A task is scheduled to tick once per scheduler loop until done. For
    each tick, the task is given the current time. Tasks can be used for
    """

    @abstractmethod
    def start(self):
        pass

    @abstractmethod
    def tick(self, time):
        """A task 'tick'. 'time' is seconds since task start"""
        pass

    @abstractmethod
    def is_finished(self, time):
        """Tasks should return true when finished. Will be scheduled
        for removal once true"""
        pass


class _TaskWrapper:
    """Small task wrapper that contains extra state info about
    a task once it's been scheduled to run.

    Attributes:
        task: Task being wrapped.
        start_time: System time (using time.time()) when the task was started.
        priority: Numerical priority of the task relative to other tasks.
        unique_tag: Unique tag for the task. Only one task can be running
            at a time for a task.
    """

    def __init__(self, task, start_time, priority, unique_tag):
        self.task = task
        self.start_time = start_time
        self.priority = priority
        self.unique_tag = unique_tag


class Scheduler:
    """Scheduler for running tasks. The system is tick-based--the scheduler
    repeatedly ticks each task with the current time to allow the task to
    update given the time.

    Attributes:
        task_wrappers: List of task wrappers representing all tasks that
        have been scheduled.
    """

    def __init__(self):
        self.task_wrappers = []
        self.__started = False

    def start(self):
        self.__started = True

    def stop(self):
        self.__started = False

    def add(self, task, priority=0, unique_tag=None):
        """Add a task.

        Order of task execution:
        Tasks can be assigned priorities. Within a scheduler object, tasks with
        higher priority are guaranteed to be executed before tasks with lower
        priority. For tasks assigned the same priority (or given no priority),
        the earliest added tasks will be executed first. Callers using the
        priority system are encouraged to create their own enums or other
        abstractions to represent possible priorities.

        Args:
            task: Task to add.
            priority: Numerical priority to give the task
            unique_tag: A unique tag to give the task. If a prior task was
              added using the same tag, it will be removed before adding
              this one.
        """

        start_time = time.time()

        if unique_tag is not None:
            self.remove_by_unique_tag(unique_tag)

        task_wrapper = _TaskWrapper(task, start_time, priority, unique_tag)
        self.task_wrappers.append(task_wrapper)
        task.start()

    def remove_by_unique_tag(self, unique_tag):
        """Remove task from the scheduler by its unique tag"""
        if unique_tag is None:
            return

        for index, task_wrapper in enumerate(self.task_wrappers):
            if unique_tag == task_wrapper.unique_tag:
                # only safe to remove in loop because we're returning after
                del self.task_wrappers[index]
                return

    def remove(self, task):
        """Remove a task from the scheduler"""
        for index, task_wrapper in enumerate(self.task_wrappers):
            if task == task_wrapper.task:
                # only safe to remove in loop because we're returning after
                del self.task_wrapper[index]
                return

    def clear(self):
        """Remove all tasks from the scheduler"""
        self.task_wrappers.clear()

    def tick(self):
        """Scheduler 'tick' to only be called by the run loop. Goes through
        scheduled tasks and forwards ticks to them and also removes finished
        tasks"""

        now = time.time()

        # remove all finished effects
        still_active = []
        for index, task_wrapper in enumerate(self.task_wrappers):
            task = task_wrapper.task
            start_time = task_wrapper.start_time
            if not task.is_finished(now - start_time):
                still_active.append(task_wrapper)
        self.task_wrappers = still_active

        # sort the effects in order of start time
        # TODO: need to implement sort by priority as well
        self.task_wrappers.sort(key=lambda task_wrapper: task_wrapper.start_time)

        for task_wrapper in self.task_wrappers:
            task_wrapper.task.tick(now - task_wrapper.start_time)

    def print_state(self):
        """ Prints scheduler state (e.g. active tasks) """
        logger.info("scheduler state:")
        for (task, _, _, _) in self.task_wrappers:
            logger.info(" " + str(task))
