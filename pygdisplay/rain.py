import pygame, random
from pygame.locals import *
from pygdisplay.screen import PygScreen

CHANCE = 0.5
SCREENX = 800
SCREENY = 600
ACCELERATION = 0.2
DROPSIZE = (3, 3)
COLORSTART = 255
COLOREND = 0
COLORSBETWEEN = 10

class RainPygDrawable:

    def __init__(self):
        self.__updategroup = None
        self.__displaygroup = None
        self.started = False

    def start(self):
        self.started = True
        self.__screen = pygame.display.set_mode((SCREENX, SCREENY))
        self.__background = pygame.Surface(self.__screen.get_rect().size)
        self.__background.fill((0, 0, 0))

        self.__updategroup = pygame.sprite.Group()
        self.__displaygroup = pygame.sprite.RenderUpdates()

        Drop.image = self.drop_image()
        self.prepare(Drop, Trail)

        for thing in [Drop, Trail]:
            thing.updategroup = self.__updategroup
            thing.displaygroup = self.__displaygroup

    def draw_loop(self):
        if not self.started:
            return
        for event in pygame.event.get():
            if event.type == QUIT:
                return

        self.__displaygroup.clear(self.__screen, self.__background)

        self.__updategroup.update()

        # if random.random() < CHANCE:
        #     Drop(random.randrange(SCREENX))

        pygame.display.update(self.__displaygroup.draw(self.__screen))

    def add_raindrop_note(self, percentage):
        if not self.started:
            return
        Drop(int(SCREENX * percentage) + random.randrange(30)) # add some randomness just for fun


    def trail_images(self, f, i):
        length = f - i + 1
        interval = (COLORSTART - COLOREND) / (COLORSBETWEEN + 1)
        images = []
        for x in range(COLORSBETWEEN):
            image = pygame.Surface((1, length)).convert()
            color = COLORSTART - (x + 1)*interval
            image.fill((color, color, color))
            images.append(image)
        return images

    def drop_image(self):
        image = pygame.Surface(DROPSIZE).convert()
        image.fill((COLORSTART, COLORSTART, COLORSTART))
        return image

    def prepare(self, drop, trail):
        y = 0.0
        v = 0.0
        ylist = []
        while int(y) <  SCREENY:
            ylist.insert(0, int(y))
            v = v + ACCELERATION
            y = y + v
        drop.ylist = ylist[:]
        ylist.insert(0, SCREENY)
        trail.imageset = []
        for i in range(len(ylist) - 1):
            trail.imageset.insert(0, self.trail_images(ylist[i], ylist[i + 1]))

class Drop(pygame.sprite.Sprite):
    def __init__(self, x):
        pygame.sprite.Sprite.__init__(self, self.updategroup, self.displaygroup)
        self.rect = self.image.get_rect()
        self.rect.centerx = x
        self.trailindex = 0
        self.ynum = len(self.ylist)
    def update(self):
        self.ynum = self.ynum - 1
        if self.ynum < 0:
            self.kill()
        else:
            self.rect.centery = self.ylist[self.ynum]
            Trail(self, self.trailindex)
            self.trailindex = self.trailindex + 1

class Trail(pygame.sprite.Sprite):
    def __init__(self, drop, trailindex):
        pygame.sprite.Sprite.__init__(self, self.updategroup)
        self.images = self.imageset[trailindex]
        self.rect = self.images[0].get_rect()
        self.rect.midtop = drop.rect.center
        self.update = self.start
    def start(self):
        self.add(self.displaygroup)
        self.update = self.fade
        self.imagenum = 0
        self.fade()
    def fade(self):
        if self.imagenum == len(self.images):
            self.kill()
        else:
            self.image = self.images[self.imagenum]
            self.imagenum = self.imagenum + 1
