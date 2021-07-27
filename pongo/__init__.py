import os
from configparser import ConfigParser

config_file = os.path.join(__path__[0], 'pongo.config')
config = ConfigParser()
config.read(config_file)
