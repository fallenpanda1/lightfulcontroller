class LightfulKeyboardShortcuts:
    """ App-specific keyboard shortcuts """
    # NOTE: might want to refactor some/all of these 
    # to not just be keyboard toggled
    def __init__(self, 
                pixel_adapter, 
                virtual_client,
                lights_show,
                midi_monitor,
                midi_player,
                midi_recorder):
        self.pixel_adapter = None
        self.virtual_client = None
        self.lights_show = None
        self.midi_monitor = None
        self.midi_player = None
        self.midi_recorder = None