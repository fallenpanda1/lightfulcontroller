import logging
import os
import pty
import threading
import time
from array import array

import serial

import lightful_windows

logger = logging.getLogger("global")

pixel_array = None


class ArduinoPixelAdapter:
    """simple interface for setting NeoPixel lights via Arduino"""

    def __init__(self, serial_port_id, baud_rate, num_pixels):

        self.num_pixels = num_pixels

        # array of pixels, each pixel being represented by an Int32 for R, G,
        # and B (and 8 empty bits on top)
        self.__pixel_array = array("i", ([0] * num_pixels))
        global pixel_array
        pixel_array = self.__pixel_array

        self.__serial = serial.Serial(serial_port_id, baud_rate)

        # NOTE: the act of setting up serial reboots the remote Arduino, so we
        # want to have the Arduino initiate contact once it's been fully booted
        waiting = self.__serial.readline()

        # TODO: Document controller/arduino protocol here
        # TODO: Check that it's a specific message?
        logger.info("log 'setup' message: " + str(waiting))

        logger.info("sending num_pixel value to Arduino: " + str(num_pixels))
        self.__serial.write(num_pixels.to_bytes(1, byteorder='little'))

        # wait for next line
        self.__serial.readline()

        logger.info("Serial open, handshake complete!")

        # ready for next push
        self.__ready_for_push = True

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
        # don't need the alpha here, and the alpha confuses the signed-ness
        self.__pixel_array[position] = color.with_alpha(0)

    def int32(self, x):
        if x > 0xFFFFFFFF:
            raise OverflowError
        elif x > 0x7FFFFFFF:
            return int(0x100000000 - x)
        else:
            return x

    def wait_for_ready_state(self):
        """ Block and wait for arduino to send back message """
        while not self.ready_for_push:
            self.check_for_ready_state()
            time.sleep(0.01)

    def ready_for_push(self):
        self.check_for_push_received_message()
        return self.__ready_for_push

    def check_for_push_received_message(self):
        # if ready_for_push is false it means we're waiting for arduino
        # response
        if not self.__ready_for_push and self.__serial.in_waiting > 0:
            # any response will do for now -- Arduino just sends a single
            # newline back
            self.__serial.readline()
            self.__ready_for_push = True

    def push_pixels(self):
        if not self.__serial.is_open:
            logger.error("Trying to send serial when serial isn't open!")

        if self.ready_for_push():
            self.__serial.write(self.__pixel_array)
            self.__ready_for_push = False  # now wait for next received message


class VirtualArduinoClient:
    """ A fake arduino client that runs on a separate thread"""

    def __init__(self, num_pixels):

        # open a pseudoterminal, where master translates to our local serial
        # and slave is the virtual arduino
        self.__master, self.__slave = pty.openpty()
        # needed to make sure readline() doesn't block when no data comes in
        os.set_blocking(self.__master, False)
        self.__serial_reader = os.fdopen(self.__master, "rb")
        self.__serial_writer = os.fdopen(self.__master, "wb")
        # todo: remove this and determine num_pixels from the protocol itself
        # instead
        self.__num_pixels = num_pixels
        self.__lights_show = None

        thread = threading.Thread(target=self.__loop, args=())
        thread.daemon = True
        thread.start()

    def start(self, lights_show):
        self.__lights_show = lights_show

        # open virtual window
        self.virtualpixelwindow = lightful_windows.VirtualNeopixelWindow(
            800, 600)
        self.virtualpixelwindow.start()

    def stop(self):
        self.virtualpixelwindow.close()

    def port_id(self):
        return os.ttyname(self.__slave)

    def __write_to_master(self, string):
        if string[-1] != '\n':
            logger.error(
                "serial string is expected to end with a \\n character")
            return
        self.__serial_writer.write(string.encode())
        self.__serial_writer.flush()

    def __loop(self):
        # wait a little while for the adapter to be initialized before
        # beginning setup protocol
        time.sleep(0.05)
        logger.info("sending message")
        # communication protocol is currently kind of.. handwavy
        self.__write_to_master("I'm ready! hit me with some setup calls!\n")
        time.sleep(0.05)  # wait for setup calls
        response_bytes = self.__serial_reader.readline()
        num_pixels = ord(response_bytes)
        if num_pixels != self.__num_pixels:
            logger.error(
                "mismatch between initialization num_pixels and actual"
                "num_pixels sent over serial setup")

        self.__write_to_master("\n")  # got your message!

        # TODO: set up above should happen on a background thread, but scary to
        # do this loop in the background
        while True:
            line = self.__serial_reader.read(self.__num_pixels * 4)
            if line:
                """we should simulate the delay of the Arduino actually setting
                the neopixels. According to docs: 'One pixel requires 24 bits
                (8 bits each for red, green blue) — 30 microseconds.'
                https://learn.adafruit.com/adafruit-neopixel-uberguide/advanced-coding"""  # noqa
                time.sleep(0.000030 * self.__num_pixels)

                color_array = []
                for i in range(int(len(line) / 4)):
                    i = i * 4
                    # little-endian so reverse
                    color_array.append((line[i + 2], line[i + 1], line[i]))

                # TODO: there's definitely a mismatch between input and output
                #   due to some rounding issues... resolve later
                # for index, pixel in enumerate(pixel_array):
                #     color = color_array[index]
                #     if pixel.r() != color[0] or pixel.g() != color[1] or pixel.b() != color[2]:
                #         pass

                self.virtualpixelwindow.update_with_colors(color_array)
                self.__write_to_master("\n")  # got your message!

            time.sleep(0.001)
