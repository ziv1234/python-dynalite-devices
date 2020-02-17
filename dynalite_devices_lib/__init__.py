"""Dynalite Communications"""
import voluptuous as vol

from .const import *
from .dynalite_devices import DynaliteDevices
from dynalite_lib import (
    CONF_CHANNEL,
    CONF_AREA,
    CONF_PRESET,
    CONF_NODEFAULT,
    CONF_LOGLEVEL,
    CONF_FADE,
    CONF_DEFAULT,
    CONF_POLLTIMER,
    CONF_AUTO_DISCOVER,
)

DEFAULT_TEMPLATE_NAMES = [t for t in DEFAULT_TEMPLATES]


def numString(value):
    newValue = str(value)
    if newValue.isdigit():
        return newValue
    else:
        raise vol.Invalid("Not a string with numbers")


TEMPLATE_ROOM_SCHEMA = vol.Schema(
    {vol.Optional(CONF_ROOM_ON): numString, vol.Optional(CONF_ROOM_OFF): numString}
)

TEMPLATE_TRIGGER_SCHEMA = vol.Schema(
    {vol.Optional(CONF_TRIGGER): numString}
)

TEMPLATE_CHANNELCOVER_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_CHANNEL): numString,
        vol.Optional(CONF_CHANNEL_CLASS): str,
        vol.Optional(CONF_FACTOR): vol.Coerce(float),
        vol.Optional(CONF_TILT_PERCENTAGE): vol.Coerce(float),
    }
)

TEMPLATE_TIMECOVER_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_CHANNEL): numString,
        vol.Optional(CONF_CHANNEL_CLASS): str,
        vol.Optional(CONF_OPEN_PRESET): numString,
        vol.Optional(CONF_CLOSE_PRESET): numString,
        vol.Optional(CONF_STOP_PRESET): numString,
        vol.Optional(CONF_DURATION): vol.Coerce(float),
        vol.Optional(CONF_TILT_TIME): vol.Coerce(float),
    }
)

TEMPLATE_DATA_SCHEMA = vol.Any(
    TEMPLATE_ROOM_SCHEMA, TEMPLATE_TRIGGER_SCHEMA, TEMPLATE_CHANNELCOVER_SCHEMA, TEMPLATE_TIMECOVER_SCHEMA
)

PRESET_DATA_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_NAME): str,
        vol.Optional(CONF_FADE): vol.Coerce(float),
        vol.Optional(CONF_HIDDEN_ENTITY, default=False): vol.Coerce(bool),
    }
)

PRESET_SCHEMA = vol.Schema({numString: vol.Any(PRESET_DATA_SCHEMA, None)})


def check_channel_data_schema(conf): # XXX check if still relevant
    """Check that a channel config is valid."""
    if conf[CONF_CHANNEL_TYPE] != "cover":
        for param in [CONF_CHANNEL_CLASS, CONF_FACTOR, CONF_TILT_PERCENTAGE]:
            if param in conf:
                raise vol.Invalid(
                    "parameter " + param + " is only valid for 'cover' type channels"
                )
    return conf


CHANNEL_DATA_SCHEMA = vol.Schema(
    vol.All(
        {
            vol.Optional(CONF_NAME): str,
            vol.Optional(CONF_FADE): vol.Coerce(float),
            vol.Optional(CONF_CHANNEL_TYPE, default=DEFAULT_CHANNEL_TYPE): vol.Any(
                "light", "switch", "cover"
            ),
            vol.Optional(CONF_CHANNEL_CLASS): str,
            vol.Optional(CONF_HIDDEN_ENTITY, default=False): vol.Coerce(bool),
            vol.Optional(CONF_FACTOR): vol.Coerce(float),
            vol.Optional(CONF_TILT_PERCENTAGE): vol.Coerce(float),
            vol.Optional(CONF_PRESET): {numString: vol.Any(vol.Coerce(float), None)},
        },
        check_channel_data_schema,
    )
)

CHANNEL_SCHEMA = vol.Schema({numString: vol.Any(CHANNEL_DATA_SCHEMA, None)})


def check_area_data_schema(conf):
    """Verify that an area config is valid."""
    if CONF_TEMPLATE in conf and conf[CONF_TEMPLATE] not in DEFAULT_TEMPLATES:
        raise vol.Invalid(
            conf[CONF_TEMPLATE]
            + " is not a valid template name. Possible names are: "
            + str(DEFAULT_TEMPLATE_NAMES)
        )

    if CONF_TEMPLATE_OVERRIDE in conf and False:
        if CONF_TEMPLATE not in conf:
            raise vol.Invalid(
                CONF_TEMPLATE_OVERRIDE
                + " may only be present when "
                + CONF_TEMPLATE
                + " is defined"
            )
        template = conf[CONF_TEMPLATE]
        if template == CONF_ROOM:
            TEMPLATE_ROOM_SCHEMA(conf[CONF_TEMPLATE_OVERRIDE])
        elif template == CONF_TRIGGER:
            TEMPLATE_TRIGGER_SCHEMA(conf[CONF_TEMPLATE_OVERRIDE])
        else:
            raise vol.Invalid("Unknown template type " + template)
    return conf


AREA_DATA_SCHEMA = vol.Schema(
    vol.All(
        {
            vol.Required(CONF_NAME): str,
            vol.Optional(CONF_TEMPLATE): str,
            vol.Optional(CONF_TEMPLATE_OVERRIDE): TEMPLATE_DATA_SCHEMA,
            vol.Optional(CONF_FADE): vol.Coerce(float),
            vol.Optional(CONF_NODEFAULT): vol.Coerce(bool),
            vol.Optional(CONF_AREA_OVERRIDE): str,
            vol.Optional(CONF_PRESET): PRESET_SCHEMA,
            vol.Optional(CONF_CHANNEL): CHANNEL_SCHEMA,
        },
        check_area_data_schema,
    )
)

AREA_SCHEMA = vol.Schema({numString: vol.Any(AREA_DATA_SCHEMA, None)})

PLATFORM_DEFAULTS_SCHEMA = vol.Schema({vol.Optional(CONF_FADE): vol.Coerce(float)})


TEMPLATE_SCHEMA = vol.Schema({str: vol.Any(TEMPLATE_DATA_SCHEMA, None)})

BRIDGE_CONFIG_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
        vol.Required(CONF_HOST): str,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
        vol.Optional(CONF_LOGLEVEL): str,
        vol.Optional(CONF_AUTO_DISCOVER, default=False): vol.Coerce(bool),
        vol.Optional(CONF_POLLTIMER, default=1.0): vol.Coerce(float),
        vol.Optional(CONF_AREA): AREA_SCHEMA,
        vol.Optional(CONF_DEFAULT): PLATFORM_DEFAULTS_SCHEMA,
        vol.Optional(CONF_PRESET): PRESET_SCHEMA,
        vol.Optional(CONF_TEMPLATE, default=DEFAULT_TEMPLATES): TEMPLATE_SCHEMA,
        vol.Optional(CONF_ACTIVE, default=False): vol.Coerce(bool),
    }
)
