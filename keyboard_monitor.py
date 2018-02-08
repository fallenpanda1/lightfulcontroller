import logging

from abc import abstractmethod
from abc import ABC
from pymaybe import maybe

logger = logging.getLogger("global")
prefixless_logger = logging.getLogger("prefixless")


class NestedKeyboardMonitorWrapper:
    def __init__(self, parent_monitor, child_monitor):
        self.parent_monitor = parent_monitor
        self.child_monitor = child_monitor

    def go_into_nested_monitor(self):
        """Go into a nested keyboard handling mode"""
        self.parent_monitor.child_monitor = self.child_monitor
        self.child_monitor.parent_monitor = self.parent_monitor
        prefixless_logger.info("Gone into sub-menu!")
        prefixless_logger.info(self.child_monitor.description())


class KeyboardMonitor:
    """ Monitors keyboard events and supports registering callbacks
    for specific events """
    def __init__(self):
        self.callbacks_by_key = {}
        self.descriptions_by_key = {}

        self.parent_monitor = None
        self.child_monitor = None

    def register_nested_monitor(self, key, description):
        """Add a nested keyboard monitor for the given key. Basically
        a sub-menu that has its own key press options"""
        nested_monitor = KeyboardMonitor()
        # we hackily implement this just by adding as a callback and doing
        # type checking when looking at callbacks
        callback = NestedKeyboardMonitorWrapper(self, nested_monitor).\
            go_into_nested_monitor
        self.register_callback(key, description, callback)
        return nested_monitor

    def register_callback(self, key, description, callback):
        """ Add a callback when a key is pressed """
        if ord(key) in self.callbacks_by_key:
            logger.error("key " + str(key) + " already has a callback")
            return
        self.callbacks_by_key[ord(key)] = callback
        self.descriptions_by_key[ord(key)] = description

    def remove_nested_monitor(self):
        self.child_monitor.parent_monitor = None
        self.child_monitor = None
        prefixless_logger.info(self.description())

    def description(self):
        """Outputs all shortcuts registered"""
        descriptions = self.descriptions_by_key.values()
        return '\n'.join(descriptions)

    def notify_key_press(self, character):
        if self.child_monitor is not None:
            self.child_monitor.notify_key_press(character)
            return

        callback = self.callbacks_by_key.get(character)
        maybe(callback)()
