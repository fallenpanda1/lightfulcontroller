import curses
import argparse
from midi.midi_monitor import MidiMonitor, VirtualMidiMonitor # TODO: erm, can we simplify this? is that what the __init__ file is for?
import logging
from curses_log_handler import CursesLogHandler
from light_engine.adapter import ArduinoPixelAdapter, MockAdapter
from array import array
from scheduler.scheduler import *
from light_engine.light_effect import *
from color import *
from shows import *
import rtmidi
from rain import PygRainScreen

logger = logging.getLogger("global")

# set up curses for async keyboard input
stdscr = curses.initscr()
curses.noecho()
stdscr.nodelay(1) # set getch() non-blocking

pixel_adapter = None

def main_loop(window):
    # set up curses window (similar to a regular terminal window except it allows for non-blocking keyboard input)
    curses_window = window
    curses_window.scrollok(1)

    curses_window.addstr("~^~^~Welcome to the Lightful Controller~^~^~\n")
    curses_window.addstr("Setting up program...\n")
    curses_window.refresh()

    rain_screen = PygRainScreen()

    # set up logging
    logger.setLevel(logging.DEBUG)
    handler = CursesLogHandler(curses_window)
    formatter = logging.Formatter('%(asctime)s-%(name)s-%(levelname)s-%(message)s') # todo, add function name here?
    handler.setFormatter(formatter)
    logger.handlers = [handler]

    # parse command line options
    parser = argparse.ArgumentParser(description="Lightful Piano Controller Script")
    parser.add_argument("--virtualmidi", action='store_true')
    args = parser.parse_args()

    # set up Midi listener
    monitor = MidiMonitor()
    if args.virtualmidi:
        monitor = VirtualMidiMonitor()
    monitor.start()

    # set up scheduler for animations, effects, etc.
    scheduler = Scheduler()
    scheduler.start()

    # scheduler.add(DebugTask()) # debug code

    global pixel_adapter
    num_notes = 100
    if False:
        pixel_adapter = ArduinoPixelAdapter(serial_port_id = '/dev/tty.usbmodem1411', baud_rate = 115200, num_notes = num_notes)
    else:
        pixel_adapter = MockAdapter(num_notes = num_notes)
    pixel_adapter.start()

    # great show
    monitor.register(hanging_door_lights_show.HangingDoorLightsShow(scheduler, pixel_adapter, rain_screen))

    # add base layer for scheduler
    base_layer_effect = LightEffectTask(SolidColorLightEffect(color=make_color(0, 35, 50)), LightSection(range(num_notes)), 100000000, pixel_adapter)
    scheduler.add(base_layer_effect)

    curses_window.addstr("\nDone setting up\n\n")
    curses_window.addstr("Keyboard Shortcuts:\n")
    curses_window.addstr("(c)lose serial connection\n")
    curses_window.addstr("(o)pen serial connection\n")
    curses_window.addstr("(q)uit\n\n")
    curses_window.refresh()

    while True:
        # listen for any new midi input
        monitor.listen_loop()

        # tick scheduler
        scheduler.tick()

        # push pixels
        pixel_adapter.push_pixels()

        # check for any keyboard input (TODO: move into a keyboard monitor object)
        character = stdscr.getch()
        if character == ord('o'):
            pixel_adapter.start()
        elif character == ord('c'):
            pixel_adapter.stop()
        elif character == ord('t'):
            pixel_adapter.push_pixels()
        elif character == ord('q'):
            pixel_adapter.stop()
            monitor.stop()
            exit()
        elif character >= ord('1') and character <= ord('9'):
            if isinstance(monitor, VirtualMidiMonitor):
                monitor.send_virtual_note(offset = character - ord('1'))

        # render loop for rain
        rain_screen.rain_loop()

curses.wrapper(main_loop)
