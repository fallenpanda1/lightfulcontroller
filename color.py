from forbiddenfruit import curse
"""Color utilities
Note: we use forbiddenfruit to monkey-patch the int primitive and add helper functions.
This is so we can be more declarative when manipulating colors:
> blue = make_color(0, 0, 255)
> red = make_color(255, 0, 0)
> mixture = blue.with_alpha(0.5).blended_with(red)
> print(mixture.b)

A less hacky approach would have been to introduce a Color object, but that's a lot less performant than raw int32.
"""

"""Color Constructors"""

def make_color(r, g, b, a=255):
	"""color creation"""
	return (a << 24) + (r << 16) + (g << 8) + b

"""Color Components"""

def a(self):
	return (self >> 24) % 256
curse(int, "a", a)

def r(self):
	return (self >> 16) % 256
curse(int, "r", r)

def g(self):
	return (self >> 8) % 256
curse(int, "g", g)

def b(self):
	return self % 256
curse(int, "b", b)

"""Color Helpers"""

def blended_with(self, other):
	"""returns a color blended between self and color. blending is based on self's alpha value
	e.g. if self.alpha = 1, then it ignores the other color, and if self.alpha = 0.5, an equal 
	amount of each color is used.
	"""
	alpha = self.a() / 255
	other_alpha = 1 - alpha
	r = round(self.r() * alpha + other.r() * other_alpha)
	g = round(self.g() * alpha + other.g() * other_alpha)
	b = round(self.b() * alpha + other.b() * other_alpha)
	return make_color(r, g, b)
curse(int, "blended_with", blended_with)

def with_alpha(self, alpha):
	"""return color with alpha applied (alpha takes up the leftmost 8 bits of the int32 color)"""
	return make_color(self.r(), self.g(), self.b(), int(alpha * 255))
curse(int, "with_alpha", with_alpha) # e.g. red.with_alpha(0.5), where red is an int
