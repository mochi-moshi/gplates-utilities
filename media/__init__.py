
import os
basedir = os.path.dirname(__file__)

LOGO_PATH = os.path.join(basedir, "logo.ico")

del basedir

__all__ = ['LOGO_PATH']