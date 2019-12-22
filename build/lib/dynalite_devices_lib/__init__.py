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
    CONF_AUTODISCOVER,
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

TEMPLATE_TRIGGER_SCHEMA = numString

TEMPLATE_CHANNELCOVER_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_CHANNEL): numString,
        vol.Optional(CONF_CHANNELCLASS): str,
        vol.Optional(CONF_FACTOR): vol.Coerce(float),
        vol.Optional(CONF_TILTPERCENTAGE): vol.Coerce(float),
    }
)

TEMPLATE_DATA_SCHEMA = vol.Any(
    TEMPLATE_ROOM_SCHEMA, TEMPLATE_TRIGGER_SCHEMA, TEMPLATE_CHANNELCOVER_SCHEMA
)

PRESET_DATA_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_NAME): str,
        vol.Optional(CONF_FADE): vol.Coerce(float),
        vol.Optional(CONF_HIDDENENTITY, default=False): vol.Coerce(bool),
    }
)

PRESET_SCHEMA = vol.Schema({numString: vol.Any(PRESET_DATA_SCHEMA, None)})


def check_channel_data_schema(conf):
    """Check that a channel config is valid."""
    if conf[CONF_CHANNELTYPE] != "cover":
        for param in [CONF_CHANNELCLASS, CONF_FACTOR, CONF_TILTPERCENTAGE]:
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
            vol.Optional(CONF_CHANNELTYPE, default=DEFAULT_CHANNELTYPE): vol.Any(
                "light", "switch", "cover"
            ),
            vol.Optional(CONF_CHANNELCLASS): str,
            vol.Optional(CONF_HIDDENENTITY, default=False): vol.Coerce(bool),
            vol.Optional(CONF_FACTOR): vol.Coerce(float),
            vol.Optional(CONF_TILTPERCENTAGE): vol.Coerce(float),
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

    if CONF_TEMPLATEOVERRIDE in conf and False:
        if CONF_TEMPLATE not in conf:
            raise vol.Invalid(
                CONF_TEMPLATEOVERRIDE
                + " may only be present when "
                + CONF_TEMPLATE
                + " is defined"
            )
        template = conf[CONF_TEMPLATE]
        if template == CONF_ROOM:
            TEMPLATE_ROOM_SCHEMA(conf[CONF_TEMPLATEOVERRIDE])
        elif template == CONF_TRIGGER:
            TEMPLATE_TRIGGER_SCHEMA(conf[CONF_TEMPLATEOVERRIDE])
        else:
            raise vol.Invalid("Unknown template type " + template)
    return conf


AREA_DATA_SCHEMA = vol.Schema(
    vol.All(
        {
            vol.Required(CONF_NAME): str,
            vol.Optional(CONF_TEMPLATE): str,
            vol.Optional(CONF_TEMPLATEOVERRIDE): TEMPLATE_DATA_SCHEMA,
            vol.Optional(CONF_FADE): vol.Coerce(float),
            vol.Optional(CONF_NODEFAULT): vol.Coerce(bool),
            vol.Optional(CONF_AREAOVERRIDE): str,
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
        vol.Optional(CONF_AUTODISCOVER, default=True): vol.Coerce(bool),
        vol.Optional(CONF_POLLTIMER, default=1.0): vol.Coerce(float),
        vol.Optional(CONF_AREA): AREA_SCHEMA,
        vol.Optional(CONF_DEFAULT): PLATFORM_DEFAULTS_SCHEMA,
        vol.Optional(CONF_PRESET): PRESET_SCHEMA,
        vol.Optional(CONF_TEMPLATE, default=DEFAULT_TEMPLATES): TEMPLATE_SCHEMA,
    }
)
