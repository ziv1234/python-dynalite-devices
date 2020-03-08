"""Configure the areas, presets, and channels."""

from .const import (
    CONF_AREA_OVERRIDE,
    CONF_CHANNEL,
    CONF_CHANNEL_COVER,
    CONF_CHANNEL_TYPE,
    CONF_CLOSE_PRESET,
    CONF_DEVICE_CLASS,
    CONF_DURATION,
    CONF_FADE,
    CONF_HIDDEN_ENTITY,
    CONF_NAME,
    CONF_NO_DEFAULT,
    CONF_OPEN_PRESET,
    CONF_PRESET,
    CONF_ROOM,
    CONF_ROOM_OFF,
    CONF_ROOM_ON,
    CONF_STOP_PRESET,
    CONF_TEMPLATE,
    CONF_TILT_TIME,
    CONF_TIME_COVER,
    CONF_TRIGGER,
    DEFAULT_CHANNEL_TYPE,
)


def configure_preset(preset, preset_config, default_fade, hidden=False):
    """Return the configuration of a preset."""
    result = {
        CONF_NAME: preset_config.get(CONF_NAME, f"Preset {preset}"),
        CONF_FADE: preset_config.get(CONF_FADE, default_fade),
    }
    if hidden:
        result[CONF_HIDDEN_ENTITY] = True
    return result


def configure_channel(channel, channel_config, default_fade, hidden=False):
    """Return the configuration of a channel."""
    result = {
        CONF_NAME: channel_config.get(CONF_NAME, f"Channel {channel}"),
        CONF_FADE: channel_config.get(CONF_FADE, default_fade),
        CONF_CHANNEL_TYPE: channel_config.get(CONF_CHANNEL_TYPE, DEFAULT_CHANNEL_TYPE),
    }
    if hidden:
        result[CONF_HIDDEN_ENTITY] = True
    return result


PRESET_CONFS = {
    CONF_ROOM: [CONF_ROOM_ON, CONF_ROOM_OFF],
    CONF_TRIGGER: [CONF_TRIGGER],
    CONF_TIME_COVER: [CONF_OPEN_PRESET, CONF_CLOSE_PRESET, CONF_STOP_PRESET],
}

TIME_COVER_VALUE_CONFS = [CONF_DEVICE_CLASS, CONF_DURATION, CONF_TILT_TIME]


def configure_area(area, area_config, default_fade, templates, default_presets):
    """Return the configuration of an area."""
    result = {
        CONF_NAME: area_config.get(CONF_NAME, f"Area {area}"),
        CONF_FADE: area_config.get(CONF_FADE, default_fade),
    }
    for conf in [CONF_TEMPLATE, CONF_AREA_OVERRIDE]:
        if conf in area_config:
            result[conf] = area_config[conf]
    # User defined presets and channels first, then template presets, then defaults
    area_presets = {
        int(preset): configure_preset(
            preset, area_config[CONF_PRESET][preset], result[CONF_FADE]
        )
        for preset in area_config.get(CONF_PRESET, {})
    }
    area_channels = {
        int(channel): configure_channel(
            channel, area_config[CONF_CHANNEL][channel], result[CONF_FADE]
        )
        for channel in area_config.get(CONF_CHANNEL, {})
    }
    # add the entities implicitly defined by templates
    template = area_config.get(CONF_TEMPLATE)
    if template:
        # ensure presets are there
        for conf in PRESET_CONFS[template]:
            preset = int(area_config.get(conf, templates[template][conf]))
            result[conf] = preset
            if preset not in area_presets:
                area_presets[preset] = configure_preset(
                    preset, {}, result[CONF_FADE], template != CONF_TRIGGER
                )
    if template == CONF_TIME_COVER:  # time cover also has non-preset conf
        for conf in TIME_COVER_VALUE_CONFS:
            result[conf] = area_config.get(conf, templates[template][conf])
        channel_cover = int(
            area_config.get(CONF_CHANNEL_COVER, templates[template][CONF_CHANNEL_COVER])
        )
        result[CONF_CHANNEL_COVER] = channel_cover
        if 0 < channel_cover < 255 and channel_cover not in area_channels:
            area_channels[channel_cover] = configure_channel(
                channel_cover, {}, result[CONF_FADE], True
            )
    # Default presets
    if not area_config.get(CONF_NO_DEFAULT, False) and not template:
        for preset in default_presets:
            if preset not in area_presets:
                area_presets[preset] = default_presets[preset]
    result[CONF_PRESET] = area_presets
    result[CONF_CHANNEL] = area_channels
    return result
