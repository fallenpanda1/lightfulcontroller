import logging
import time

from pyglet import graphics, image, sprite, window
from pyglet.gl import pyglet

logger = logging.getLogger("global")

"""
REMINDER: On macOS, pyglet throws some sort of "ApplePersistenceIgnoreState"
when being shut down. Seems harmless.. suppress by running 'defaults write
org.python.python ApplePersistenceIgnoreState NO' command line.
"""


def tick():
    """global tick for all Pyglet windows"""
    pyglet.clock.tick()

    for win in pyglet.app.windows:
        win.switch_to()
        win.dispatch_events()
        win.dispatch_event('on_draw')
        win.flip()

# global close of all Pyglet windows


def exit():
    for win in pyglet.app.windows:
        win.close()


class VirtualNeopixelWindow(window.Window):
    """ TODO: Fill me in """

    def start(self):
        self.batch = graphics.Batch()
        self.particles = list()
        self.particle_image = image.load('media/images/particle.png')
        self.particle_sprites = []
        self.time_to_draw_next_frame = time.time()

        # set up pixels! (just 10x10 grid for now)
        rows = 20
        cols = 4
        # remember that rows counterintuitively corresponds to height, cols to
        # width
        # add 2 for buffer space for rows and cols
        row_increment = 1.0 * self.height / (rows + 0.25)
        col_increment = 1.0 * self.width / (cols + 0.25)
        for x in range(0, cols):
            for y in range(0, rows):

                # for odd columns, the light strip is reversed downward, so
                # flip y position
                if x % 2 == 1:
                    y = rows - y - 1

                # add one so don't start at edge of screen
                xpos = col_increment * (x + 0.25)
                # add one so don't start at edge of screen
                ypos = row_increment * (y + 0.25)

                s = sprite.Sprite(
                    self.particle_image, x=xpos, y=ypos, batch=self.batch)
                s.scale = 1.5
                self.particle_sprites.append(s)

    def on_draw(self):
        now = time.time()
        # stop limiting to 60 fps?
        if True or now >= self.time_to_draw_next_frame:
            self.clear()
            self.batch.draw()
            fps = 60
            self.time_to_draw_next_frame = now + 1.0 / fps

    # todo: this is happening on separate thread so might cause problems
    def update_with_colors(self, color_array):
        # remove invalid colors since I accidentally added useless pixels in
        # hanging_door show get rid of first 10 and 50-60 (dead pixels)
        new_color_array = color_array[10:50]
        new_color_array.extend(color_array[60:])
        num_sprites = len(self.particle_sprites)

        for index, color in enumerate(new_color_array):
            if index >= num_sprites:
                return
            self.particle_sprites[index].color = color
