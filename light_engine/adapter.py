import serial
from array import array
import logging
import os, pty
import threading
from time import sleep

logger = logging.getLogger("global")

class ArduinoPixelAdapter:
    """simple interface for setting NeoPixel lights via Arduino"""
    def __init__(self, serial_port_id, baud_rate, num_pixels):

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

    def push_pixels(self):
        if not self.__serial.is_open:
            logger.error("Trying to send serial when serial isn't open!")

        self.__serial.write(self.__pixel_array)

        # TODO: we can optimize by not waiting for the readline until right before sending the next write message
        response_string = self.__serial.readline()
        # logger.info("Arduino ACK: " + str(response_string))

class VirtualArduinoClient:
    """ A local thread that mocks out the behavior of the Arduino (TODO: and possibly actually handles rendering a lights screen??? thanks future Allen!)"""
    def __init__(self):

        # open a pseudoterminal, where master translates to our local serial and slave is the virtual arduino
        self.__master, self.__slave = pty.openpty()
        os.set_blocking(self.__master, False) # needed to make sure readline() doesn't block when no data comes in
        self.__serial_reader = os.fdopen(self.__master, "rb")
        self.__serial_writer = os.fdopen(self.__master, "wb")
        
        thread = threading.Thread(target=self.__loop, args=())
        thread.daemon = True
        thread.start()

    def port_id(self):
        return os.ttyname(self.__slave)

    def __write_to_master(self, string):
        if string[-1] != '\n':
            logger.error("serial string is expected to end with a \\n character")
            return
        self.__serial_writer.write(string.encode())
        self.__serial_writer.flush()

    def __loop(self):
        sleep(0.1) # wait a little while for the adapter to be initialized before beginning setup protocol
        logger.info("sending message")
        self.__write_to_master("I'm ready! hit me with some setup calls!\n")

        while True:
            line = self.__serial_reader.readline()
            if line:
                self.__write_to_master("ACK (cool I got your message, whatever it is!)\n")

            sleep(0.01)
