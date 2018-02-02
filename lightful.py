import argparse
import curses
import logging
import multiprocessing
import time
from multiprocessing import Process
from multiprocessing import Queue
import serial

from pymaybe import maybe

from curses_log_handler import CursesLogHandler
from keyboard_monitor import KeyboardMonitor
from light_engine.pixel_adapter import ArduinoPixelAdapter
from lightful_shortcuts import LightfulKeyboardShortcuts
from midi.monitor import MidiMonitor
from profiler import Profiler
from scheduler.scheduler import Scheduler
from shows import hanging_door_lights_show

logger = logging.getLogger("global")

# set up curses for async keyboard input
stdscr = curses.initscr()
curses.noecho()
stdscr.nodelay(1)  # set getch() non-blocking

pixel_adapter = None
lights_show = None

midi_monitor = None


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

    # set up scheduler for midi events
    midi_scheduler = Scheduler()
    midi_scheduler.start()

    # set up scheduler for animations, effects, etc.
    animation_scheduler = Scheduler()
    animation_scheduler.start()

    # set up and connect to NeoPixel adapter (or local virtual simulator)
    global pixel_adapter
    num_pixels = 100
    serial_port_id = '/dev/tty.usbmodem1411'  # TODO: make configurable
    if args.virtualpixels:
        multiprocessing.set_start_method('spawn')
        logger.info("using simulated arduino/neopixels handled on separate process")
        render_queue = Queue()
        render_process = Process(target=render_process_loop, args=(render_queue, num_pixels))
        render_process.start()
        # render loop expected to give us the port on which its listening for
        # arduino serial messages
        logger.info("GETTING")
        serial_port_id = render_queue.get()
        logger.info("YAH GOT VIRTUAL PORT!!: " + serial_port_id)

    pixel_adapter = ArduinoPixelAdapter(
        serial_port_id=serial_port_id, baud_rate=115200, num_pixels=num_pixels)
    pixel_adapter.start()

    # create show
    global lights_show
    lights_show = hanging_door_lights_show.HangingDoorLightsShow(
        animation_scheduler, pixel_adapter, midi_monitor)

    # create keyboard monitor
    keyboard_monitor = KeyboardMonitor()
    keyboard_shortcuts = LightfulKeyboardShortcuts(
        keyboard_monitor, pixel_adapter,
        lights_show, midi_monitor, animation_scheduler, midi_scheduler
    )
    keyboard_shortcuts.register_shortcuts()

    curses_window.addstr("\nDone setting up\n\n")
    curses_window.addstr("Keyboard Shortcuts:\n")
    curses_window.addstr(keyboard_shortcuts.shortcuts_description() + "\n")
    curses_window.refresh()

    profiler = Profiler()
    # set to True to enable time profile logs of main run loop
    profiler.enabled = False

    while True:
        """The main loop gives every system in this app a chance to
        perform any necessary actions"""
        profiler.avg("loop start")

        midi_scheduler.tick()

        profiler.avg("midi scheduler tick")

        # listen for any new midi input
        midi_monitor.listen_loop()
        profiler.avg("midi listen")

        # Pixel push protocol involves data transfer over serial. Instead
        # of blocking the main loop on serial I/O, we just skip animation
        # rendering and serial push if previous serial push hasn't completed
        if pixel_adapter.ready_for_push():
            # tick animation scheduler to update pixels
            animation_scheduler.tick()
            profiler.avg("animation scheduler")

            # push latest pixel state
            pixel_adapter.push_pixels()
            profiler.avg("pixel push")

        character = stdscr.getch()
        keyboard_monitor.notify_key_press(character)

        profiler.avg("character read")

        # sleep at least a short time to allow any other threads to do
        # their stuff (though we currently don't have any)
        time.sleep(0.001)


def render_process_loop(queue, num_pixels):
    """The render process loop gives all rendering logic time to perform
    any necessary actions and draws (and communication with the main
    process)"""
    from light_engine.virtual_pixels import VirtualArduinoClient
    import lightful_windows
    virtual_client = VirtualArduinoClient(num_pixels=num_pixels)

    # send the virtual serial port id we opened back to the main thread
    # so it can connect
    virtual_port_id = virtual_client.port_id()
    queue.put(virtual_port_id)

    virtual_client.start()

    # render process loop
    while True:
        # tick the virtual Arduino client to respond to any serial input
        # from the main process
        virtual_client.tick()

if __name__ == '__main__':
    curses.wrapper(main_loop)
