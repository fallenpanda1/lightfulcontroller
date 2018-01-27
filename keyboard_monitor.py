import logging

from pymaybe import maybe

logger = logging.getLogger("global")


class KeyboardMonitor:
    """ Monitors keyboard events and supports registering callbacks
    for specific events """
    def __init__(self):
        self.callbacks_by_key = {}
        self.descriptions_by_key = {}

    def add_keydown_callback(self, key, description, callback):
        """ Add a callback when a key is pressed """
        if ord(key) in self.callbacks_by_key:
            logger.error("key " + str(key) + " already has a callback")
            return
        self.callbacks_by_key[ord(key)] = callback
        self.descriptions_by_key[ord(key)] = description

    def notify_key_press(self, character):
        callback = self.callbacks_by_key.get(character)
        maybe(callback)()
