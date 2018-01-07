import serial
from array import array
import logging
import os, pty
import threading
import time
from pygdisplay.neopixel import NeopixelSimulationPygDrawable
from color import *

logger = logging.getLogger("global")

class ArduinoPixelAdapter:
    """simple interface for setting NeoPixel lights via Arduino"""
    def __init__(self, serial_port_id, baud_rate, num_pixels):

        self.num_pixels = num_pixels

        # array of pixels, each pixel being represented by an Int32 for R, G, and B (and 8 empty bits on top)
        self.__pixel_array = array("i", ([0] * num_pixels))

        self.__serial = serial.Serial(serial_port_id, baud_rate)

        # NOTE: the act of setting up serial reboots the remote Arduino, so we want to have the Arduino initiate
        # contact once it's been fully booted
        waiting = self.__serial.readline()

        # TODO: Document controller/arduino protocol here
        # TODO: Check that it's a specific message?
        logger.info("log 'setup' message: " + str(waiting))

        logger.info("stuff" + str(num_pixels))
        self.__serial.write(num_pixels.to_bytes(1, byteorder='little'))

        # wait for next line
        ready = self.__serial.readline()

        logger.info("Serial open, handshake complete!")

        self.ready_for_send = True

    def start(self):
        if not self.__serial.is_open:
            self.__serial.open()
            logger.info("Serial re-opened!")

    def stop(self):
    	if self.__serial.is_open:
            self.__serial.close()
            logger.info("Serial closed!")

    def get_color(self, position):
        return self.__pixel_array[position]

    def set_color(self, position, color):
        self.__pixel_array[position] = color.with_alpha(0) # don't need the alpha here, and the alpha confuses the signed-ness

    def int32(self, x):
        if x>0xFFFFFFFF:
            raise OverflowError
        elif x>0x7FFFFFFF:
            return int(0x100000000-x)
        else:
            return x

    def wait_for_ready_state(self):
        """ Block and wait for arduino to send back message """
        while not self.ready_for_send:
            self.check_for_ready_state()
            time.sleep(0.01)

    def check_for_ready_state(self):
        # if ready_for_send is false it means we're waiting for arduino response
        if not self.ready_for_send and self.__serial.in_waiting > 0:
            response_string = self.__serial.readline() # any response will do for now -- Arduino just sends a single newline back 
            self.ready_for_send = True

    def push_pixels(self):
        if not self.__serial.is_open:
            logger.error("Trying to send serial when serial isn't open!")

        self.check_for_ready_state()

        if self.ready_for_send:
            self.__serial.write(self.__pixel_array)
            self.ready_for_send = False

class VirtualArduinoClient:
    """ A fake arduino client that runs on a separate thread (TODO: and possibly actually handles rendering a lights screen??? thanks future Allen!)"""
    def __init__(self, num_pixels):

        # open a pseudoterminal, where master translates to our local serial and slave is the virtual arduino
        self.__master, self.__slave = pty.openpty()
        os.set_blocking(self.__master, False) # needed to make sure readline() doesn't block when no data comes in
        self.__serial_reader = os.fdopen(self.__master, "rb")
        self.__serial_writer = os.fdopen(self.__master, "wb")
        self.__num_pixels = num_pixels # todo: remove this and determine num_pixels from the protocol itself instead
        self.__neopixel_drawable = None
        self.__lights_show = None

        thread = threading.Thread(target=self.__loop, args=())
        thread.daemon = True
        thread.start()

    def begin_pygscreen_simulation(self, pygscreen, lights_show):
        self.__neopixel_drawable = NeopixelSimulationPygDrawable()
        pygscreen.display_with_drawable(self.__neopixel_drawable)
        self.__lights_show = lights_show

    def port_id(self):
        return os.ttyname(self.__slave)

    def __write_to_master(self, string):
        if string[-1] != '\n':
            logger.error("serial string is expected to end with a \\n character")
            return
        self.__serial_writer.write(string.encode())
        self.__serial_writer.flush()

    def __loop(self):
        time.sleep(0.1) # wait a little while for the adapter to be initialized before beginning setup protocol
        logger.info("sending message")
        self.__write_to_master("I'm ready! hit me with some setup calls!\n")

        setup_complete = False
        while True:
            line = self.__serial_reader.readline()
            if line:
                # we should simulate the delay of the Arduino actually setting the neopixels. According to docs:
                # 'One pixel requires 24 bits (8 bits each for red, green blue) — 30 microseconds.'
                # https://learn.adafruit.com/adafruit-neopixel-uberguide/advanced-coding
                time.sleep(0.000030 * self.__num_pixels)

                # TODO: wait for expected # of lines, then convert to a color array
                #self.__neopixel_drawable()
                if setup_complete == True:
                    color_array = []
                    for i in range(int(len(line) / 4)):
                        i = i * 4
                        # little-endian so reverse
                        color_array.append((line[i+2], line[i+1], line[i]))

                    self.__neopixel_drawable.update_with_colors(color_array)

                self.__write_to_master("\n") # got your message!
                setup_complete = True

            time.sleep(0.01)
