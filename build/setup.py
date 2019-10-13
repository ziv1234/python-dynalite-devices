from distutils.core import setup
from mypyc.build import mypycify

setup(name='mypyc_output',
      ext_modules=mypycify([], ['dynalite_devices_lib/switch.py'], ),
)
