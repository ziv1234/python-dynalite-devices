"""Constants for the Dynalite component."""
import logging

LOGGER = logging.getLogger(__package__)
DOMAIN = "dynalite-devices"

CONF_COVERS = 'cover'
from dynalite_lib.dynalite import (CONF_CHANNEL)

CONF_CHANNELTYPE = 'type'
CONF_CHANNELCLASS = 'class'
CONF_HIDDENENTITY = 'hidden'
CONF_FACTOR = 'factor'
CONF_TILTPERCENTAGE = 'tilt'
CONF_AUTODISCOVER = 'autodiscover'
CONF_AREAOVERRIDE = 'areaoverride'
CONF_ROOM_ON = 'room_on'
CONF_ROOM_OFF = 'room_off'
CONF_TEMPLATE = 'template'
CONF_TEMPLATEOVERRIDE = 'templateoverride'

CONF_ROOM = 'room'
CONF_TRIGGER = 'trigger'
CONF_CHANNELCOVER = 'channelcover'
CONF_AREA_CREATE_MANUAL = 'manual'
CONF_AREA_CREATE_ASSIGN = 'assign'
CONF_AREA_CREATE_AUTO = 'auto'

DATA_CONFIGS = "dynalite_configs"

DEFAULT_NAME = 'dynalite'
DEFAULT_PORT = 12345
DEFAULT_LOGGING = 'info'
DEFAULT_CHANNELTYPE = 'light'
DEFAULT_COVERCHANNELCLASS = 'shutter'
DEFAULT_COVERFACTOR = 1.0 # cover goes from closed(0.0) to open (1.0). If it needs less than the range, use a lower number
DEFAULT_TEMPLATES = {
    CONF_ROOM:{CONF_ROOM_ON: '1', CONF_ROOM_OFF: '4'}, 
    CONF_TRIGGER:{CONF_TRIGGER: '1'}, 
    CONF_HIDDENENTITY:{}, 
    CONF_CHANNELCOVER:{CONF_CHANNEL: '1', CONF_CHANNELCLASS: DEFAULT_COVERCHANNELCLASS, CONF_FACTOR: DEFAULT_COVERFACTOR},
}
