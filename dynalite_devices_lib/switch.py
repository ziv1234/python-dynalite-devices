"""Support for the Dynalite channels and presets as switches."""

from .const import CONF_PRESET, CONF_ROOM, CONF_TEMPLATE
from .dynalitebase import (
    DynaliteBaseDevice,
    DynaliteChannelBaseDevice,
    DynaliteMultiDevice,
)


class DynaliteChannelSwitchDevice(DynaliteChannelBaseDevice):
    """Representation of a Dynalite Channel as a Home Assistant Switch."""

    def __init__(self, area, channel, bridge):
        """Initialize the switch."""
        self._level = 0
        super().__init__(area, channel, bridge)

    @property
    def category(self):
        """Return the category of the entity: light, switch, or cover."""
        return "switch"

    @property
    def is_on(self):
        """Return true if switch is on."""
        return self._level > 0

    def update_level(self, actual_level, target_level):
        """Update the current level."""
        self._level = actual_level

    async def async_turn_on(self, **kwargs):
        """Turn switch on."""
        fade = self._bridge.get_channel_fade(self._area, self._channel)
        self._bridge.set_channel_level(self._area, self._channel, 1, fade)

    async def async_turn_off(self, **kwargs):
        """Turn switch off."""
        fade = self._bridge.get_channel_fade(self._area, self._channel)
        self._bridge.set_channel_level(self._area, self._channel, 0, fade)


class DynalitePresetSwitchDevice(DynaliteBaseDevice):
    """Representation of a Dynalite Preset as a Home Assistant Switch."""

    def __init__(self, area, preset, bridge):
        """Initialize the switch."""
        self._preset = preset
        self._level = 0
        super().__init__(area, bridge)

    @property
    def available(self):
        """Return if device is available."""
        return self._bridge.available(CONF_PRESET, self._area, self._preset)

    @property
    def name(self):
        """Return the name of the device."""
        return self._bridge.get_preset_name(self._area, self._preset)

    @property
    def category(self):
        """Return the category of the entity: light, switch, or cover."""
        return "switch"

    @property
    def unique_id(self):
        """Return the ID of this cover."""
        return "dynalite_area_" + str(self._area) + "_preset_" + str(self._preset)

    def set_level(self, level):
        """Set the current level and potentially trigger listeners."""
        old_level = self._level
        self._level = level
        if old_level != self._level:
            self.update_listeners()

    @property
    def is_on(self):
        """Return true if device is on."""
        return self._level > 0

    async def async_turn_on(self, **kwargs):
        """Turn switch on."""
        fade = self._bridge.get_preset_fade(self._area, self._preset)
        self._bridge.select_preset(self._area, self._preset, fade)

    async def async_turn_off(self, **kwargs):
        """Turn switch off - doesn't do anything for presets."""
        self.set_level(0)


class DynaliteDualPresetSwitchDevice(DynaliteMultiDevice):
    """Representation of a Dynalite Preset as a Home Assistant Switch."""

    def __init__(self, area, bridge):
        """Initialize the switch."""
        super().__init__(2, area, bridge)

    @property
    def available(self):
        """Return if device is available."""
        return self._bridge.available(CONF_TEMPLATE, self._area, CONF_ROOM)

    @property
    def category(self):
        """Return the category of the entity: light, switch, or cover."""
        return "switch"

    @property
    def unique_id(self):
        """Return the ID of this room switch."""
        return "dynalite_area_" + str(self._area) + "_room_switch"

    @property
    def is_on(self):
        """Return true if device is on."""
        return self.get_device(1).is_on

    async def async_turn_on(self, **kwargs):
        """Turn switch on."""
        await self.get_device(1).async_turn_on()

    async def async_turn_off(self, **kwargs):
        """Turn switch off."""
        await self.get_device(2).async_turn_on()
