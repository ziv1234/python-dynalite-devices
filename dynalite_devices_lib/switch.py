"""Support for the Dynalite channels and presets as switches."""

from typing import TYPE_CHECKING

from .const import CONF_PRESET, CONF_ROOM, CONF_TEMPLATE
from .dynalitebase import (
    DynaliteBaseDevice,
    DynaliteChannelBaseDevice,
    DynaliteMultiDevice,
)

if TYPE_CHECKING:  # pragma: no cover
    from .dynalite_devices import DynaliteDevices


class DynaliteChannelSwitchDevice(DynaliteChannelBaseDevice):
    """Representation of a Dynalite Channel as a Home Assistant Switch."""

    def __init__(
        self, area: int, channel: int, bridge: "DynaliteDevices", hidden: bool
    ) -> None:
        """Initialize the switch."""
        self._level = 0.0
        super().__init__(area, channel, bridge, hidden)

    @property
    def category(self) -> str:
        """Return the category of the entity: light, switch, or cover."""
        return "switch"

    @property
    def is_on(self) -> bool:
        """Return true if switch is on."""
        return self._level > 0

    def update_level(self, actual_level: float, target_level: float) -> None:
        """Update the current level."""
        # pylint: disable=unused-argument
        self._level = actual_level

    async def async_turn_on(self, **kwargs) -> None:
        """Turn switch on."""
        # pylint: disable=unused-argument
        fade = self._bridge.get_channel_fade(self._area, self._channel)
        self._bridge.set_channel_level(self._area, self._channel, 1, fade)

    async def async_turn_off(self, **kwargs) -> None:
        """Turn switch off."""
        # pylint: disable=unused-argument
        fade = self._bridge.get_channel_fade(self._area, self._channel)
        self._bridge.set_channel_level(self._area, self._channel, 0, fade)


class DynalitePresetSwitchDevice(DynaliteBaseDevice):
    """Representation of a Dynalite Preset as a Home Assistant Switch."""

    def __init__(
        self, area: int, preset: int, bridge: "DynaliteDevices", hidden: bool
    ) -> None:
        """Initialize the switch."""
        self._preset = preset
        self._level = 0
        super().__init__(area, bridge, hidden)

    @property
    def available(self) -> bool:
        """Return if device is available."""
        return self._bridge.available(CONF_PRESET, self._area, self._preset)

    @property
    def name(self) -> str:
        """Return the name of the device."""
        return self._bridge.get_preset_name(self._area, self._preset)

    @property
    def category(self) -> str:
        """Return the category of the entity: light, switch, or cover."""
        return "switch"

    @property
    def unique_id(self) -> str:
        """Return the ID of this cover."""
        return "dynalite_area_" + str(self._area) + "_preset_" + str(self._preset)

    def set_level(self, level: int) -> None:
        """Set the current level and potentially trigger listeners."""
        old_level = self._level
        self._level = level
        if old_level != self._level:
            self.update_listeners()

    @property
    def is_on(self) -> bool:
        """Return true if device is on."""
        return self._level > 0

    async def async_turn_on(self, **kwargs) -> None:
        """Turn switch on."""
        # pylint: disable=unused-argument
        fade = self._bridge.get_preset_fade(self._area, self._preset)
        self._bridge.select_preset(self._area, self._preset, fade)

    async def async_turn_off(self, **kwargs) -> None:
        """Turn switch off - doesn't do anything for presets."""
        # pylint: disable=unused-argument
        self.set_level(0)


class DynaliteDualPresetSwitchDevice(DynaliteMultiDevice):
    """Representation of a Dynalite Preset as a Home Assistant Switch."""

    def __init__(self, area: int, bridge: "DynaliteDevices", hidden: bool) -> None:
        """Initialize the switch."""
        super().__init__(2, area, bridge, hidden)

    @property
    def available(self) -> bool:
        """Return if device is available."""
        return self._bridge.available(CONF_TEMPLATE, self._area, CONF_ROOM)

    @property
    def category(self) -> str:
        """Return the category of the entity: light, switch, or cover."""
        return "switch"

    @property
    def unique_id(self) -> str:
        """Return the ID of this room switch."""
        return "dynalite_area_" + str(self._area) + "_room_switch"

    @property
    def is_on(self) -> bool:
        """Return true if device is on."""
        device = self.get_device(1)
        assert isinstance(device, DynalitePresetSwitchDevice)
        return device.is_on

    async def async_turn_on(self, **kwargs) -> None:
        """Turn switch on."""
        # pylint: disable=unused-argument
        device = self.get_device(1)
        assert isinstance(device, DynalitePresetSwitchDevice)
        await device.async_turn_on()

    async def async_turn_off(self, **kwargs) -> None:
        """Turn switch off."""
        # pylint: disable=unused-argument
        device = self.get_device(2)
        assert isinstance(device, DynalitePresetSwitchDevice)
        await device.async_turn_on()
