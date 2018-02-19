import lightful_windows
import logging
import os
import pty
import time

logger = logging.getLogger("global")

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

    def start(self):
        # open virtual window
        self.virtualpixelwindow = lightful_windows.VirtualNeopixelWindow(
            1200, 800)
        self.virtualpixelwindow.start()

        ## MICROCONTROLLER STARTUP PROTOCOL

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

        ## THIS CONCLUDES MICROCONTROLLER STARTUP PROTOCOL

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

    def tick(self):
        """Virtual Arduino 'tick' polling for and updating for serial input."""

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

            self.virtualpixelwindow.update_with_colors(color_array)

            # TODO: performance is really bad if this is in the render loop
            # directly. figure out why!
            lightful_windows.tick()

            self.__write_to_master("\n")  # got your message!

        time.sleep(0.001)
