"""Support for the Dynalite devices."""
from typing import TYPE_CHECKING, Callable, Dict, List

from .const import CONF_CHANNEL

if TYPE_CHECKING:  # pragma: no cover
    from .dynalite_devices import DynaliteDevices


class DynaliteBaseDevice:
    """Base class for Dynalite devices."""

    def __init__(self, area: int, bridge: "DynaliteDevices", hidden: bool) -> None:
        """Initialize the device."""
        self._area = area
        self._bridge = bridge
        self._listeners: List[Callable[[DynaliteBaseDevice, bool], None]] = []
        self._hidden = hidden

    @property
    def area_name(self) -> str:
        """Return the name of the area."""
        return self._bridge.get_area_name(self._area)

    @property
    def get_master_area(self) -> str:
        """Get the master area when combining entities from different Dynet areas to the same area."""
        return self._bridge.get_master_area(self._area)

    @property
    def hidden(self) -> bool:
        """Get whether the device should be hidden from the calling platform."""
        return self._hidden

    def add_listener(
        self, listener: Callable[["DynaliteBaseDevice", bool], None]
    ) -> None:
        """Add a listener for changes."""
        self._listeners.append(listener)

    def update_listeners(self, stop_fade: bool = False) -> None:
        """Update all listeners."""
        for listener in self._listeners:
            listener(self, stop_fade)


class DynaliteChannelBaseDevice(DynaliteBaseDevice):
    """Representation of a Dynalite Channel as a Home Assistant device."""

    def __init__(
        self, area: int, channel: int, bridge: "DynaliteDevices", hidden: bool
    ) -> None:
        """Initialize the device."""
        self._channel = channel
        super().__init__(area, bridge, hidden)

    @property
    def available(self) -> bool:
        """Return if device is available."""
        return self._bridge.available(CONF_CHANNEL, self._area, self._channel)

    @property
    def name(self) -> str:
        """Return the name of the device."""
        return self._bridge.get_channel_name(self._area, self._channel)

    @property
    def unique_id(self) -> str:
        """Return the ID of this device."""
        return "dynalite_area_" + str(self._area) + "_channel_" + str(self._channel)

    def stop_fade(self) -> None:
        """Update the listeners if STOP FADE is received."""
        self.update_listeners(True)


class DynaliteMultiDevice(DynaliteBaseDevice):
    """Representation of two Dynalite Presets as an on/off switch."""

    def __init__(
        self, num_devices: int, area: int, bridge: "DynaliteDevices", hidden: bool
    ) -> None:
        """Initialize the device."""
        self._devices: Dict[int, DynaliteBaseDevice] = {}
        self._num_devices = num_devices
        super().__init__(area, bridge, hidden)

    @property
    def name(self) -> str:
        """Return the name of the device."""
        return self._bridge.get_multi_name(self._area)

    def get_device(self, devnum: int) -> DynaliteBaseDevice:
        """Get one of the devices."""
        assert devnum in self._devices
        return self._devices[devnum]

    def set_device(self, devnum: int, device: DynaliteBaseDevice) -> None:
        """Set one of the attached devices."""
        self._devices[devnum] = device
        device.add_listener(self.listener)

    def listener(self, device: DynaliteBaseDevice, stop_fade: bool) -> None:
        """Update the device since its internal devices changed."""
        # pylint: disable=unused-argument
        self._bridge.update_device(self)
