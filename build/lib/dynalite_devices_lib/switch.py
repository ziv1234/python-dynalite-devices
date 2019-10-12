"""Support for the Dynalite channels and presets as switches."""
import asyncio
import logging
from .const import DOMAIN, LOGGER
import pprint

from .dynalitebase import (
    DynaliteChannelBaseDevice,
    DynaliteBaseDevice,
    DynaliteDualPresetDevice,
)


class DynaliteChannelSwitchDevice(DynaliteChannelBaseDevice):
    """Representation of a Dynalite Channel as a Home Assistant Switch."""

    def __init__(self, area, area_name, channel, name, type, master_area, bridge, device):
        """Initialize the switch."""
        self._level = 0
        super().__init__(area, area_name, channel, name, type, master_area, bridge, device)

    @property
    def category(self):
        return "switch"

    @property
    def is_on(self):
        """Return true if switch is on."""
        return self._level > 0

    def update_level(self, actual_level, target_level):
        self._level = actual_level

    async def async_turn_on(self, **kwargs):
        self._device.turnOn()

    async def async_turn_off(self, **kwargs):
        self._device.turnOff()


class DynalitePresetSwitchDevice(DynaliteBaseDevice):
    """Representation of a Dynalite Preset as a Home Assistant Switch."""

    def __init__(self, area, area_name, preset, name, master_area, bridge, device):
        """Initialize the switch."""
        self._preset = preset
        self._level = 0
        self._device = device
        super().__init__(area, area_name, name, master_area, bridge)

    @property
    def category(self):
        return "switch"

    @property
    def unique_id(self):
        """Return the ID of this cover."""
        return "dynalite_area_" + str(self._area) + "_preset_" + str(self._preset)

    @property
    def is_on(self):
        """Return true if device is on."""
        new_level = self._device.active
        if new_level != self._level:
            self.update_listeners()  # XXX should this move to update_level?
        self._level = new_level
        return self._level

    def update_level(self, actual_level, target_level):
        self._level = actual_level

    async def async_turn_on(self, **kwargs):
        self._device.turnOn()

    async def async_turn_off(self, **kwargs):
        self._device.turnOff()


class DynaliteDualPresetSwitchDevice(DynaliteDualPresetDevice):
    """Representation of a Dynalite Preset as a Home Assistant Switch."""

    def __init__(self, area, area_name, name, master_area, bridge):
        """Initialize the switch."""
        super().__init__(area, area_name, name, master_area, bridge)

    @property
    def category(self):
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
        await self.get_device(1).async_turn_on()

    async def async_turn_off(self, **kwargs):
        await self.get_device(2).async_turn_on()
