"""Support for the Dynalite channels as covers."""
from .const import ATTR_POSITION, ATTR_TILT_POSITION, LOGGER

from .dynalitebase import DynaliteChannelBaseDevice, DynaliteMultiDevice
import asyncio

class DynaliteChannelCoverDevice(DynaliteChannelBaseDevice):
    """Representation of a Dynalite Channel as a Home Assistant Cover."""

    def __init__(
        self,
        area,
        area_name,
        channel,
        name,
        type,
        device_class,
        cover_factor,
        master_area,
        bridge,
        device,
    ):
        """Initialize the cover."""
        self._device_class = device_class
        self._cover_factor = cover_factor
        self._actual_level = 0
        self._target_level = 0
        self._current_position = 0
        super().__init__(
            area, area_name, channel, name, type, master_area, bridge, device
        )

    @property
    def category(self):
        """Return the category of the entity: light, switch, or cover."""
        return "cover"

    @property
    def has_tilt(self):
        """Return whether cover supports tilt."""
        return False

    @property
    def device_class(self):
        """Return the class of the cover."""
        return self._device_class

    def update_level(self, actual_level, target_level):
        """Update the current level."""
        prev_actual_level = self._actual_level
        self._actual_level = actual_level
        self._target_level = target_level
        level_diff = actual_level - prev_actual_level
        factored_diff = level_diff / self._cover_factor
        self._current_position = min(1, max(0, self._current_position + factored_diff))
        if self._current_position > 0.99999:
            self._current_position = 1
        if self._current_position < 0.00001:
            self._current_position = 0
        if getattr(self, "update_tilt", False):
            self.update_tilt(factored_diff)

    @property
    def current_cover_position(self):
        """Return the position of the cover from 0 to 100."""
        return int(self._current_position * 100)

    @property
    def is_opening(self):
        """Return whether cover is currently opening."""
        return self._current_position < 1 and self._target_level > self._actual_level

    @property
    def is_closing(self):
        """Return whether cover is currently closing."""
        return self._current_position > 0 and self._target_level < self._actual_level

    @property
    def is_closed(self):
        """Return whether cover is closed."""
        return self._current_position == 0

    async def async_open_cover(self, **kwargs):
        """Open the cover."""
        self._device.turnOn()

    async def async_close_cover(self, **kwargs):
        """Close the cover."""
        self._device.turnOff()

    async def async_set_cover_position(self, **kwargs):
        """Set the cover to a specific position."""
        target_position = kwargs[ATTR_POSITION] / 100
        position_diff = target_position - self._current_position
        level_diff = position_diff * self._cover_factor
        target_level = min(1, max(0, self._actual_level + level_diff))
        self._device.turnOn(brightness=target_level)

    async def async_stop_cover(self, **kwargs):
        """Stop the cover."""
        self._device.stopFade()


class DynaliteChannelCoverWithTiltDevice(DynaliteChannelCoverDevice):
    """Representation of a Dynalite Channel as a Home Assistant Cover that uses up and down for tilt."""

    def __init__(
        self,
        area,
        area_name,
        channel,
        name,
        type,
        device_class,
        cover_factor,
        tilt_percentage,
        master_area,
        bridge,
        device,
    ):
        """Initialize the cover."""
        super().__init__(
            area,
            area_name,
            channel,
            name,
            type,
            device_class,
            cover_factor,
            master_area,
            bridge,
            device,
        )
        self._tilt_percentage = tilt_percentage
        self._current_tilt = 0

    @property
    def has_tilt(self):
        """Return whether cover supports tilt."""
        return True

    def update_tilt(self, diff):
        """Update the current tilt based on diff and tilt_percentage."""
        tilt_diff = diff / self._tilt_percentage
        self._current_tilt = max(0, min(1, self._current_tilt + tilt_diff))

    @property
    def current_cover_tilt_position(self):
        """Return the current cover tilt."""
        return int(self._current_tilt * 100)

    async def apply_tilt_diff(self, tilt_diff):
        """Move the cover up or down based on a diff."""
        position_diff = tilt_diff * self._tilt_percentage
        target_position = int(
            100 * max(0, min(1, self._current_position + position_diff))
        )
        await self.async_set_cover_position(position=target_position)

    async def async_open_cover_tilt(self, **kwargs):
        """Open the cover tilt."""
        if self._current_tilt == 1:
            return
        else:
            await self.apply_tilt_diff(1 - self._current_tilt)

    async def async_close_cover_tilt(self, **kwargs):
        """Close the cover tilt."""
        if self._current_tilt == 0:
            return
        else:
            await self.apply_tilt_diff(0 - self._current_tilt)

    async def async_set_cover_tilt_position(self, **kwargs):
        """Set the cover tilt position."""
        target_position = kwargs[ATTR_TILT_POSITION] / 100
        await self.apply_tilt_diff(target_position - self._current_tilt)

    async def async_stop_cover_tilt(self, **kwargs):
        """Stop cover tilt."""
        await self.async_stop_cover()

class DynaliteTimeCoverDevice(DynaliteMultiDevice):
    """Representation of a Dynalite Channel as a Home Assistant Cover."""

    def __init__(
        self,
        area,
        area_name,
        name,
        duration,
        device_class,
        master_area,
        bridge,
    ):
        """Initialize the cover."""
        self._device_class = device_class
        self._current_position = 0
        self._duration = duration
        self._direction = "stop"
        super().__init__(4, area, area_name, name, master_area, bridge)

    @property
    def category(self):
        """Return the category of the entity: light, switch, or cover."""
        return "cover"

    @property
    def unique_id(self):
        """Return the ID of this room switch."""
        return "dynalite_area_" + str(self._area) + "_time_cover"

    @property
    def has_tilt(self):
        """Return whether cover supports tilt."""
        return False

    @property
    def device_class(self):
        """Return the class of the cover."""
        return self._device_class

    def update_level(self, actual_level, target_level):
        """Update the current level."""
        if actual_level == target_level:
            self._direction = "stop"
            self._bridge.remove_timer_listener(self.timer_callback)
        else:
            self._direction = "open" if target_level > actual_level else "close"
            self._bridge.add_timer_listener(self.timer_callback)
        self._bridge.updateDevice(self)
            
    def timer_callback(self):
        if self._direction == "open":
            self._current_position += 1.0 / self._duration
            if self._current_position >= 1.0:
                self._current_position = 1.0
                self._direction = "stop"
                self._bridge.remove_timer_listener(self.timer_callback)
        elif self._direction == "close":    
            self._current_position -= 1.0 / self._duration
            if self._current_position <= 0.0:
                self._current_position = 0.0
                self._direction = "stop"
                self._bridge.remove_timer_listener(self.timer_callback)
        elif self._direction == "stop":
            self._bridge.remove_timer_listener(self.timer_callback)

        if getattr(self, "update_tilt", False):
            self.update_tilt()

        self._bridge.updateDevice(self)

    @property
    def current_cover_position(self):
        """Return the position of the cover from 0 to 100."""
        return int(self._current_position * 100)

    @property
    def is_opening(self):
        """Return whether cover is currently opening."""
        return self._direction == "open"

    @property
    def is_closing(self):
        """Return whether cover is currently closing."""
        return self._direction == "close"

    @property
    def is_closed(self):
        """Return whether cover is closed."""
        return self._current_position == 0

    async def async_open_cover(self, **kwargs):
        """Open the cover."""
        await self.get_device(1).async_turn_on()
        self.update_level(self._current_position, 1.0)

    async def async_close_cover(self, **kwargs):
        """Close the cover."""
        await self.get_device(2).async_turn_on()
        self.update_level(self._current_position, 0.0)

    async def async_set_cover_position(self, **kwargs):
        """Set the cover to a specific position."""
        target_position = kwargs[ATTR_POSITION] / 100
        position_diff = target_position - self._current_position
        if position_diff > 0:
            await self.async_open_cover()
            while self._current_position < target_position and self._direction == "open":
                LOGGER.debug("XXX position current=%s target=%s direction=%s", self._current_position, target_position, self._direction)
                await asyncio.sleep(1)
            LOGGER.debug("XXX last position current=%s target=%s direction=%s", self._current_position, target_position, self._direction)
            if self._direction == "open":
                await self.async_stop_cover()
        elif position_diff < 0:
            await self.async_close_cover()
            while self._current_position > target_position and self._direction == "close":
                LOGGER.debug("XXX position current=%s target=%s direction=%s", self._current_position, target_position, self._direction)
                await asyncio.sleep(1)
            LOGGER.debug("XXX last position current=%s target=%s direction=%s", self._current_position, target_position, self._direction)
            if self._direction == "close":
                await self.async_stop_cover()
        else:
            await self.async_stop_cover()
        
    async def async_stop_cover(self, **kwargs):
        """Stop the cover."""
        await self.get_device(3).async_turn_on()
        self.update_level(self._current_position, self._current_position)
        
    def listener(self, device, stop_fade):
        LOGGER.debug("XXX listener device=%s", device.unique_id)
        if device == self.get_device(1):
            LOGGER.debug("XXX listener open level=%s", device.level)
            if device.level > 0:
                LOGGER.debug("XXX listener activate")
                self.update_level(self._current_position, 1.0)
        elif device == self.get_device(2):
            LOGGER.debug("XXX listener close level=%s", device.level)
            if device.level > 0:
                LOGGER.debug("XXX listener activate")
                self.update_level(self._current_position, 0.0)
        elif device == self.get_device(3):
            LOGGER.debug("XXX listener stop level=%s", device.level)
            if device.level > 0:
                LOGGER.debug("XXX listener activate")
                self.update_level(self._current_position, self._current_position)
        elif device == self.get_device(4):
            LOGGER.debug("XXX listener stop level=%s stop=%s", device.level, stop_fade)
            if stop_fade or device.direction == "stop":
                LOGGER.debug("XXX listener channel stop")
                self.update_level(self._current_position, self._current_position)
            elif device.direction == "open":
                LOGGER.debug("XXX listener channel open")
                self.update_level(self._current_position, 1.0)
            else:
                LOGGER.debug("XXX listener channel close")
                self.update_level(self._current_position, 0.0)
                
        else:
            LOGGER.error("listener received update from unknown device")
        super().listener(device, stop_fade)

class DynaliteTimeCoverWithTiltDevice(DynaliteTimeCoverDevice):
    """Representation of a Dynalite Channel as a Home Assistant Cover that uses up and down for tilt."""

    def __init__(
        self,
        area,
        area_name,
        name,
        duration,
        device_class,
        tilt_duration,
        master_area,
        bridge,
    ):
        """Initialize the cover."""
        super().__init__(
            area,
            area_name,
            name,
            duration,
            device_class,
            master_area,
            bridge,
        )
        self._tilt_duration = tilt_duration
        self._current_tilt = 0

    @property
    def has_tilt(self):
        """Return whether cover supports tilt."""
        return True

    def update_tilt(self):
        """Update the current tilt based on diff and tilt_percentage."""
        if self._direction == "open":
            mult = 1
        elif self._direction == "close":
            mult = -1
        else:
            LOGGER.error("update_tilt called with invalid direction %s", self._direction)
            return
        tilt_diff = mult / self._tilt_duration
        self._current_tilt = max(0, min(1, self._current_tilt + tilt_diff))

    @property
    def current_cover_tilt_position(self):
        """Return the current cover tilt."""
        return int(self._current_tilt * 100)

    async def apply_tilt_diff(self, tilt_diff):
        """Move the cover up or down based on a diff."""
        factor = self._tilt_duration / self._duration
        position_diff = tilt_diff * factor
        target_position = int(
            100 * max(0, min(1, self._current_position + position_diff))
        )
        await self.async_set_cover_position(position=target_position)

    async def async_open_cover_tilt(self, **kwargs):
        """Open the cover tilt."""
        if self._current_tilt == 1:
            return
        else:
            await self.apply_tilt_diff(1 - self._current_tilt)

    async def async_close_cover_tilt(self, **kwargs):
        """Close the cover tilt."""
        if self._current_tilt == 0:
            return
        else:
            await self.apply_tilt_diff(0 - self._current_tilt)

    async def async_set_cover_tilt_position(self, **kwargs):
        """Set the cover tilt position."""
        target_position = kwargs[ATTR_TILT_POSITION] / 100
        await self.apply_tilt_diff(target_position - self._current_tilt)

    async def async_stop_cover_tilt(self, **kwargs):
        """Stop cover tilt."""
        await self.async_stop_cover()
