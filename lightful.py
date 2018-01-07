import curses
import argparse
from midi.midi_monitor import MidiMonitor # TODO: erm, can we simplify this? is that what the __init__ file is for?
from midi.midi_fileio import MidiRecorder, MidiPlayer, InMemoryMidiPlayer
import logging
from curses_log_handler import CursesLogHandler
from light_engine.adapter import ArduinoPixelAdapter, VirtualArduinoClient
from scheduler.scheduler import *
from light_engine.light_effect import *
from shows import *
import profiler
from pymaybe import maybe
import lightfulwindows

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

    # set up logging
    logger.setLevel(logging.DEBUG)
    handler = CursesLogHandler(curses_window)
    formatter = logging.Formatter('%(asctime)s-%(name)s-%(levelname)s-%(message)s') # todo, add function name here?
    handler.setFormatter(formatter)
    logger.handlers = [handler]

    # parse command line options
    parser = argparse.ArgumentParser(description="Lightful Piano Controller Script")
    parser.add_argument("--virtualpixels", action='store_true')
    args = parser.parse_args()

    # set up Midi listener
    monitor = MidiMonitor()
    monitor.start()

    # set up scheduler for animations, effects, etc.
    scheduler = Scheduler()
    scheduler.start()

    # set up and connect to NeoPixel adapter (or local virtual simulator)
    global pixel_adapter
    num_pixels = 100
    serial_port_id = '/dev/tty.usbmodem1411' # TODO: hardcoded for now, make configurable later
    virtual_client = None
    if args.virtualpixels:
        logger.info("using simulated arduino/neopixels")
        virtual_client = VirtualArduinoClient(num_pixels = num_pixels)
        serial_port_id = virtual_client.port_id()
    pixel_adapter = ArduinoPixelAdapter(serial_port_id = serial_port_id, baud_rate = 115200, num_pixels = num_pixels)
    pixel_adapter.start()

    # create show
    lights_show = hanging_door_lights_show.HangingDoorLightsShow(scheduler, pixel_adapter, monitor)

    # TODO: maybe have a protocol a light show can implement to describe its simulation layout
    # configure neopixel simulator with light show's data
    maybe(virtual_client).start(lights_show)

    curses_window.addstr("\nDone setting up\n\n")
    curses_window.addstr("Keyboard Shortcuts:\n")
    curses_window.addstr("(c)lose serial connection\n")
    curses_window.addstr("(o)pen serial connection\n")
    curses_window.addstr("(r)ecord MIDI input to a save file, or stop and save recording if recording in progress\n")
    curses_window.addstr("(p)lay saved MIDI recording\n")
    curses_window.addstr("(q)uit\n\n")
    curses_window.refresh()

    midi_recorder = None
    midi_player = None

    p = profiler.Profiler()
    p.enabled = False # True to enable time profile logs of main run loop

    while True:
        p.avg("loop start")

        # play any pending notes from the local midi player
        if midi_player is not None:
            midi_player.play_loop()

        p.avg("midi player play")
        # listen for any new midi input
        monitor.listen_loop()
        p.avg("midi listen")
        # tick scheduler
        scheduler.tick() # TODO: The ticks only need to happen once per arduino update
        p.avg("scheduler")
        # push pixels
        pixel_adapter.push_pixels() # NOTE: this now only pushes pixels when the arduino returns a response
        p.avg("pixel push")
        # check for any keyboard input (TODO: move into a keyboard monitor object)
        character = stdscr.getch()
        if character == ord('o'):
            pixel_adapter.start()
        elif character == ord('c'):
            pixel_adapter.stop()
        elif character == ord('t'):
            pixel_adapter.push_pixels()
        elif character == ord('q'):
            # lights_show.clear_lights() comment for now until lightfulwindow implemented
            pixel_adapter.stop()
            monitor.stop()
            maybe(virtual_client).stop()
            exit()
        elif character == ord('r'):
            if midi_recorder == None:
                midi_recorder = MidiRecorder("recording1.mid", monitor)
                midi_recorder.start()
                lights_show.reset_lights()
            else:
                midi_recorder.stop() # TODO: maybe fork into cancel vs save?
                midi_recorder = None
        elif character >= ord('1') and character <= ord('9'):
            monitor.send_virtual_note(offset = character - ord('1'))
        elif character == ord('p'):
            midi_player = MidiPlayer("recording1.mid", monitor)
            #midi_player = InMemoryMidiPlayer(midi_recorder.in_memory_recording, monitor)
            midi_player.play()
            lights_show.reset_lights()
        p.avg("character read")
        
        # update & render loop for lightful windows
        lightfulwindows.tick()

        p.avg("lightful window rendering")

        time.sleep(0.001) # have to sleep at least a short time to allow any other threads to do their stuff (e.g. midi player)

curses.wrapper(main_loop)
