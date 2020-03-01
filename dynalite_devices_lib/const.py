"""Constants for the Dynalite component."""
import logging

LOGGER = logging.getLogger(__package__)
DOMAIN = "dynalite-devices"
DATA_CONFIGS = "dynalite_configs"

CONF_ACT_LEVEL = "actual_level"
CONF_ACTION = "action"
CONF_ACTION_CMD = "cmd"
CONF_ACTION_REPORT = "report"
CONF_ACTION_STOP = "stop"
CONF_ACTIVE = "active"
CONF_ACTIVE_INIT = "init"
CONF_ACTIVE_OFF = "off"
CONF_ACTIVE_ON = "on"
CONF_ALL = "ALL"
CONF_AREA = "area"
CONF_AREA_OVERRIDE = "areaoverride"
CONF_AUTO_DISCOVER = "autodiscover"
CONF_CHANNEL = "channel"
CONF_CHANNEL_CLASS = "class"
CONF_CHANNEL_COVER = "channelcover"
CONF_CHANNEL_TYPE = "type"
CONF_CLOSE_PRESET = "close"
CONF_DEFAULT = "default"
CONF_DEVICE_CLASS = "class"
CONF_DURATION = "duration"
CONF_FADE = "fade"
CONF_HIDDEN_ENTITY = "hidden"
CONF_HOST = "host"
CONF_JOIN = "join"
CONF_NAME = "name"
CONF_NO_DEFAULT = "nodefault"
CONF_NONE = "none"
CONF_OPEN_PRESET = "open"
CONF_POLL_TIMER = "polltimer"
CONF_PORT = "port"
CONF_PRESET = "preset"
CONF_ROOM = "room"
CONF_ROOM_OFF = "room_off"
CONF_ROOM_ON = "room_on"
CONF_STOP_PRESET = "stop"
CONF_TEMPLATE = "template"
CONF_TILT_TIME = "tilt"
CONF_TIME_COVER = "timecover"
CONF_TRGT_LEVEL = "target_level"
CONF_TRIGGER = "trigger"

ATTR_BRIGHTNESS = "brightness"
ATTR_POSITION = "position"
ATTR_TILT_POSITION = "tilt_position"

DEFAULT_CHANNEL_TYPE = "light"
DEFAULT_COVER_CHANNEL_CLASS = "shutter"
DEFAULT_NAME = "dynalite"
DEFAULT_PORT = 12345
DEFAULT_TEMPLATES = {
    CONF_ROOM: {CONF_ROOM_ON: "1", CONF_ROOM_OFF: "4"},
    CONF_TRIGGER: {CONF_TRIGGER: "1"},
    CONF_HIDDEN_ENTITY: {},
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
DEFAULT_PRESETS = {
    "1": {CONF_NAME: "On"},
    "4": {CONF_NAME: "Off"},
}

EVENT_CHANNEL = "CHANNEL"
EVENT_CONNECTED = "CONNECTED"
EVENT_DISCONNECTED = "DISCONNECTED"
EVENT_PRESET = "PRESET"

# if a request for channel level didn't get acknowledge, when to retry
# (subsequent retries will be 2x, 4x, 8x, etc.)
INITIAL_RETRY_DELAY = 1
# initial retry timeout for the beginning, since it could take time to settle
# on Dynet for large environments
STARTUP_RETRY_DELAY = 60
# Minimal retry frequency in seconds - default 1 hour, so if something never
# answers, it will be pinged once an hour XXX consider changing
MAXIMUM_RETRY_DELAY = 60 * 60
# no retry value for delay
NO_RETRY_DELAY_VALUE = -1
