# dynamically set __all__ to every py/pyc file in this directory.
# this is so 'from shows import *' imports all shows. this would let us
# potentially dynamically populate UI with a list of shows and allow a show
# to be instantiated without needing some sort of factory.
# (TODO: is avoiding some factory code REALLY necessary?)
from os.path import dirname, basename, isfile
import glob
modules = glob.glob(dirname(__file__)+"/*.py*")
__all__ = [ basename(f)[:-3] for f in modules if isfile(f) and not f.endswith('__init__.py')]
from . import *
