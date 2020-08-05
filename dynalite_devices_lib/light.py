"""Support for Dynalite channels as lights."""

from typing import TYPE_CHECKING

from .const import ATTR_BRIGHTNESS
from .dynalitebase import DynaliteChannelBaseDevice

if TYPE_CHECKING:  # pragma: no cover
    from .dynalite_devices import DynaliteDevices


class DynaliteChannelLightDevice(DynaliteChannelBaseDevice):
    """Representation of a Dynalite Channel as a Home Assistant Light."""

    def __init__(
        self, area: int, channel: int, bridge: "DynaliteDevices", hidden: bool
    ) -> None:
        """Initialize the light."""
        self._level = 0.0
        self._direction = "stop"
        super().__init__(area, channel, bridge, hidden)

    @property
    def category(self) -> str:
        """Return the category of the entity: light, switch, or cover."""
        return "light"

    @property
    def brightness(self) -> int:
        """Return the brightness of this light between 0..255."""
        return int(self._level * 255)

    @property
    def level(self) -> float:
        """Return the brightness of this light between 0..255."""
        return self._level

    @property
    def direction(self) -> str:
        """Return the brightness of this light between 0..1."""
        return self._direction

    @property
    def is_on(self) -> bool:
        """Return true if device is on."""
        return self._level > 0

    def update_level(self, actual_level: float, target_level: float) -> None:
        """Update the current level."""
        old_level = self._level
        self._level = actual_level
        if target_level > actual_level:
            self._direction = "open"
        elif target_level < actual_level:
            self._direction = "close"
        else:
            self._direction = "stop"

        if self._level != old_level:
            self.update_listeners()

    async def async_turn_on(self, **kwargs) -> None:
        """Turn light on."""
        # pylint: disable=unused-argument
        if ATTR_BRIGHTNESS in kwargs:
            brightness = kwargs[ATTR_BRIGHTNESS] / 255.0
        else:
            brightness = 1.0
        fade = self._bridge.get_channel_fade(self._area, self._channel)
        self._bridge.set_channel_level(self._area, self._channel, brightness, fade)

    async def async_turn_off(self, **kwargs) -> None:
        """Turn light off."""
        # pylint: disable=unused-argument
        await self.async_turn_on(**{ATTR_BRIGHTNESS: 0})
