from pymaybe import maybe

class KeyboardMonitor:
    """ TODO: work in progress """
    def __init__(self):
        self.callbacks_by_key = {}
        self.descriptions_by_key = {}

    def add_callback(self, key, description, callback):
        if key in self.callbacks_by_key:
            logger.error("key " + str(key) + " already has a callback")
            return
        self.callbacks_by_key[key] = callback

    def notify_key_press(self, character):
        callback = self.callbacks_by_key.get(character)
        maybe(callback)()
