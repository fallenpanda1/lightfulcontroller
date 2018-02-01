import multiprocessing
from multiprocessing import Process
import time

def do_the_pyglet():
	print("DOING THE PYGLET")
	import pyglet

	window = pyglet.window.Window()

	label = pyglet.text.Label('Hello, world',
	                          font_name='Times New Roman',
	                          font_size=36,
	                          x=window.width//2, y=window.height//2,
	                          anchor_x='center', anchor_y='center')

	@window.event
	def on_draw():
	    window.clear()
	    label.draw()


	print("LINE BEFORE DOING")
	pyglet.app.run()
	print("LINE AFTER DOING")


	while(True):
		time.sleep(1)

if __name__ == '__main__':
	multiprocessing.set_start_method('spawn')
	process = Process(target=do_the_pyglet)
	process.start()
	print("STARTED")
	process.join()