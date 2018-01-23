import curses
import argparse
from midi.midimonitor import MidiMonitor
import logging
from curses_log_handler import CursesLogHandler
from light_engine.pixeladapter import ArduinoPixelAdapter, VirtualArduinoClient
from scheduler.scheduler import Scheduler
from shows import hanging_door_lights_show
import profiler
from pymaybe import maybe
import lightfulwindows
import time
from keyboard_monitor import KeyboardMonitor
from lightful_shortcuts import LightfulKeyboardShortcuts

logger = logging.getLogger("global")

# set up curses for async keyboard input
stdscr = curses.initscr()
curses.noecho()
stdscr.nodelay(1)  # set getch() non-blocking

pixel_adapter = None
virtual_client = None
lights_show = None

midi_monitor = None
midi_player = None


def main_loop(window):
    # set up curses window (similar to a regular terminal window except it
    # allows for non-blocking keyboard input)
    curses_window = window
    curses_window.scrollok(1)

    curses_window.addstr("~^~^~Welcome to the Lightful Controller~^~^~\n")
    curses_window.addstr("Setting up program...\n")
    curses_window.refresh()

    # set up logging
    logger.setLevel(logging.DEBUG)
    handler = CursesLogHandler(curses_window)
    # todo, add function name here?
    formatter = logging.Formatter('%(asctime)s-%(name)s-'
                                  '%(levelname)s-%(message)s')
    handler.setFormatter(formatter)
    logger.handlers = [handler]

    # parse command line options
    parser = argparse.ArgumentParser(
        description="Lightful Piano Controller Script")
    parser.add_argument("--virtualpixels", action='store_true')
    args = parser.parse_args()

    # set up Midi listener
    global midi_monitor
    midi_monitor = MidiMonitor()
    midi_monitor.start()

    global midi_player

    # set up scheduler for animations, effects, etc.
    scheduler = Scheduler()
    scheduler.start()

    # set up and connect to NeoPixel adapter (or local virtual simulator)
    global pixel_adapter
    num_pixels = 100
    serial_port_id = '/dev/tty.usbmodem1411'  # TODO: make configurable
    global virtual_client
    if args.virtualpixels:
        logger.info("using simulated arduino/neopixels")
        virtual_client = VirtualArduinoClient(num_pixels=num_pixels)
        serial_port_id = virtual_client.port_id()
    pixel_adapter = ArduinoPixelAdapter(
        serial_port_id=serial_port_id, baud_rate=115200, num_pixels=num_pixels)
    pixel_adapter.start()

    # create show
    global lights_show
    lights_show = hanging_door_lights_show.HangingDoorLightsShow(
        scheduler, pixel_adapter, midi_monitor)

    # TODO: add protocol for light shows to describe layout for simulation
    # configure neopixel simulator with light show's data
    maybe(virtual_client).start(lights_show)

    # create keyboard monitor
    keyboard_monitor = KeyboardMonitor()
    keyboard_shortcuts = LightfulKeyboardShortcuts(
        keyboard_monitor, pixel_adapter, virtual_client,
        lights_show, midi_monitor, midi_player,
        scheduler
    )
    keyboard_shortcuts.register_shortcuts()

    curses_window.addstr("\nDone setting up\n\n")
    curses_window.addstr("Keyboard Shortcuts:\n")
    curses_window.addstr(keyboard_shortcuts.shortcuts_description() + "\n")
    curses_window.refresh()

    p = profiler.Profiler()
    p.enabled = False  # True to enable time profile logs of main run loop

    while True:
        p.avg("loop start")

        # play any pending notes from the local midi player
        if midi_player is not None:
            midi_player.play_loop()

        p.avg("midi player play")
        # listen for any new midi input
        midi_monitor.listen_loop()
        p.avg("midi listen")
        # tick scheduler
        if pixel_adapter.ready_for_push():
            scheduler.tick()
            p.avg("scheduler")

            pixel_adapter.push_pixels()
            p.avg("pixel push")

        character = stdscr.getch()
        keyboard_monitor.notify_key_press(character)

        p.avg("character read")

        # update & render loop for lightful windows
        maybe(lightfulwindows).tick()

        p.avg("lightful window rendering")

        # have to sleep at least a short time to allow any other threads to do
        # their stuff (e.g. midi player)
        time.sleep(0.001)


curses.wrapper(main_loop)
