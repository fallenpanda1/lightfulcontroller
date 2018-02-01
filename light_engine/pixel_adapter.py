import logging
import os
import time
from array import array

import serial

logger = logging.getLogger("global")


class ArduinoPixelAdapter:
    """simple interface for setting NeoPixel lights via Arduino"""

    def __init__(self, serial_port_id, baud_rate, num_pixels):
        self.num_pixels = num_pixels

        # array of pixels, each pixel being represented by an Int32 for R, G,
        # and B (and 8 empty bits on top)
        self.__pixel_array = array("i", ([0] * num_pixels))
        global pixel_array

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
