"""Constants for the Dynalite component."""
import logging
from dynalite_lib import CONF_CHANNEL, CONF_ACTIVE

LOGGER = logging.getLogger(__package__)
DOMAIN = "dynalite-devices"
DATA_CONFIGS = "dynalite_configs"

CONF_AREAOVERRIDE = "areaoverride"
CONF_CHANNELCOVER = "channelcover"
CONF_CHANNELTYPE = "type"
CONF_CHANNELCLASS = "class"
CONF_FACTOR = "factor"
CONF_HIDDENENTITY = "hidden"
CONF_HOST = "host"
CONF_NAME = "name"
CONF_NONE = "none"
CONF_PORT = "port"
CONF_ROOM = "room"
CONF_ROOM_ON = "room_on"
CONF_ROOM_OFF = "room_off"
CONF_TEMPLATE = "template"
CONF_TEMPLATEOVERRIDE = "templateoverride"
CONF_TILTPERCENTAGE = "tilt"
CONF_TRIGGER = "trigger"

ATTR_BRIGHTNESS = "brightness"
ATTR_POSITION = "position"
ATTR_TILT_POSITION = "tilt_position"

DEFAULT_CHANNELTYPE = "light"
DEFAULT_COVERCHANNELCLASS = "shutter"
# cover goes from closed(0.0) to open (1.0). If it needs less than the range, use a lower number
DEFAULT_COVERFACTOR = 1.0
DEFAULT_NAME = "dynalite"
DEFAULT_PORT = 12345
DEFAULT_TEMPLATES = {
    CONF_ROOM: {CONF_ROOM_ON: "1", CONF_ROOM_OFF: "4"},
    CONF_TRIGGER: {CONF_TRIGGER: "1"},
    CONF_HIDDENENTITY: {},
    CONF_CHANNELCOVER: {
        CONF_CHANNEL: "1",
        CONF_CHANNELCLASS: DEFAULT_COVERCHANNELCLASS,
        CONF_FACTOR: DEFAULT_COVERFACTOR,
    },
}
