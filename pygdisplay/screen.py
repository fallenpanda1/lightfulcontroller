import pygame
from pygame.locals import *

class PygScreen:
    def __init__(self):
        self.__drawable = None

    def display_with_drawable(self, pygdrawable):
        pygame.init()
        self.__drawable = pygdrawable
        self.__drawable.start()

    def draw_loop(self):
        if self.__drawable is not None:
            self.__drawable.draw_loop()
