import pygame
from pygame.locals import *
from pygdisplay.screen import PygScreen
import logging
logger = logging.getLogger("global")

SCREENWIDTH = 640
SCREENHEIGHT = 480
BACKGROUNDCOLOR = (255, 255, 255)

INACTIVECOLOR = (100, 100, 100)
ACTIVECOLOR = (0, 0, 255)

class NeopixelSimulationPygDrawable:
    # TODO: make me happen!
    def __init__(self):
        pass

    def start(self):
        screen = pygame.display.set_mode((SCREENWIDTH, SCREENHEIGHT))
        background = pygame.Surface(screen.get_size())
        background.fill(BACKGROUNDCOLOR)
        screen.blit(background, (0, 0))
        self.__screen = screen
        
        self.__group, self.__surface = self.setup_lights_for_section(section_length=10)

    def draw_loop(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                keepGoing = False
            elif event.type == pygame.KEYDOWN:
                self.__group.sprites()[0].update_color(ACTIVECOLOR)
            elif event.type == pygame.KEYUP:
                self.__group.sprites()[0].update_color(INACTIVECOLOR)

        # group.clear(surface, ) # bah deal with clearing later... lights don't move so we're rendering over them anyway
        self.__group.update()
        self.__group.draw(self.__surface)
        pygame.draw.rect(self.__surface, (0, 100, 100), self.__surface.get_rect(), 1)
        
        self.__screen.blit(self.__surface, ((SCREENWIDTH - self.__surface.get_width()) / 2, (SCREENHEIGHT - self.__surface.get_height()) / 2))

        pygame.display.flip()

    def update_with_colors(self, colors):
        length = len(self.__group.sprites())
        for index, color in enumerate(colors):
            if index >= length:
                break
            self.__group.sprites()[index].update_color(color)
        pass

    def setup_lights_for_section(self, section_length):
        """ 
        Set up lights for a light section
         """

        # calculate radius based on screen height
        light_radius = int(SCREENHEIGHT / (section_length * 4))
        light_diameter = light_radius * 2
        section_surface = pygame.Surface((light_diameter, SCREENHEIGHT))
        section_surface.fill(BACKGROUNDCOLOR)
        section_group = pygame.sprite.Group()

        for i in range(section_length):    
            circle = Circle(radius=light_radius)
            circle.rect.center = (light_radius, light_radius + (i * light_diameter * 2))
            circle.add(section_group)

        return (section_group, section_surface)

class Circle(pygame.sprite.Sprite):
    def __init__(self, radius):
        pygame.sprite.Sprite.__init__(self)
        self.radius = radius
        self.image = pygame.Surface((radius * 2, radius * 2))
        self.image.fill(BACKGROUNDCOLOR)
        self.update_color(INACTIVECOLOR)
        self.rect = self.image.get_rect()

    def update_color(self, color):
        pygame.draw.circle(self.image, color, (self.radius, self.radius), self.radius, 0)
