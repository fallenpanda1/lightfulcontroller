import serial
from array import array
import logging

logger = logging.getLogger("global")

class ArduinoPixelAdapter:
    """simple interface for setting NeoPixel lights via Arduino"""
    def __init__(self, serial_port_id, baud_rate, num_notes):

        # array of pixels, each pixel being represented by an Int32 for R, G, and B (and 8 empty bits on top)
        self.__pixel_array = array("i", ([0] * num_notes))

        self.__serial = serial.Serial(serial_port_id, baud_rate)
        # wait for waiting message
        waiting = self.__serial.readline()

        # TODO: Document controller/arduino protocol here
        # TODO: Check that it's a specific message?
        logger.info("log 'setup' message: " + str(waiting))

        logger.info("stuff" + str(num_notes))
        self.__serial.write(num_notes.to_bytes(1, byteorder='little'))

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

class MockAdapter(ArduinoPixelAdapter):
    def __init__(self, num_notes):
        # array of pixels, each pixel being represented by an Int32 for R, G, and B (and 8 empty bits on top)
        self.__pixel_array = array("i", ([0] * num_notes))

        logger.info("MockAdapter instance created")

    def start(self):
        logger.info("start called on MockAdapter")
        pass

    def stop(self):
        logger.info("stop called on MockAdapter")
        pass

    def get_color(self, position):
        return 0

    def set_color(self, position, color):
        pass

    def push_pixels(self):
        pass