"""Constants for the Dynalite component."""
import logging
from dynalite_lib import CONF_CHANNEL, CONF_ACTIVE

LOGGER = logging.getLogger(__package__)
DOMAIN = "dynalite-devices"
DATA_CONFIGS = "dynalite_configs"

CONF_AREA_OVERRIDE = "areaoverride"
CONF_CHANNEL_COVER = "channelcover"
CONF_CHANNEL_TYPE = "type"
CONF_CHANNEL_CLASS = "class"
CONF_CLOSE_PRESET = "close"
CONF_DURATION = "duration"
CONF_FACTOR = "factor"
CONF_HIDDEN_ENTITY = "hidden"
CONF_HOST = "host"
CONF_NAME = "name"
CONF_NONE = "none"
CONF_OPEN_PRESET = "open"
CONF_PORT = "port"
CONF_ROOM = "room"
CONF_ROOM_ON = "room_on"
CONF_ROOM_OFF = "room_off"
CONF_STOP_PRESET = "stop"
CONF_TEMPLATE = "template"
CONF_TEMPLATE_OVERRIDE = "templateoverride"
CONF_TILT_PERCENTAGE = "tilt"
CONF_TILT_TIME = "tilt"
CONF_TIME_COVER = "timecover"
CONF_TRIGGER = "trigger"

ATTR_BRIGHTNESS = "brightness"
ATTR_POSITION = "position"
ATTR_TILT_POSITION = "tilt_position"

DEFAULT_CHANNEL_TYPE = "light"
DEFAULT_COVER_CHANNEL_CLASS = "shutter"
# cover goes from closed(0.0) to open (1.0). If it needs less than the range, use a lower number
DEFAULT_COVER_FACTOR = 1.0
DEFAULT_NAME = "dynalite"
DEFAULT_PORT = 12345
DEFAULT_TEMPLATES = {
    CONF_ROOM: {CONF_ROOM_ON: "1", CONF_ROOM_OFF: "4"},
    CONF_TRIGGER: {CONF_TRIGGER: "1"},
    CONF_HIDDEN_ENTITY: {},
    CONF_CHANNEL_COVER: {
        CONF_CHANNEL: "1",
        CONF_CHANNEL_CLASS: DEFAULT_COVER_CHANNEL_CLASS,
        CONF_FACTOR: DEFAULT_COVER_FACTOR,
    },
    CONF_TIME_COVER: {
        CONF_CHANNEL_COVER: "1",
        CONF_CHANNEL_CLASS: DEFAULT_COVER_CHANNEL_CLASS,
        CONF_OPEN_PRESET: "1",
        CONF_CLOSE_PRESET: "2",
        CONF_STOP_PRESET: "4",
        CONF_DURATION: 60,
        CONF_TILT_TIME: 0,
    },
}
