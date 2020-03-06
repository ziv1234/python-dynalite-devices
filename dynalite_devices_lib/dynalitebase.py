"""Support for the Dynalite devices."""
from .const import CONF_CHANNEL


class DynaliteBaseDevice:  # Deriving from Object so it doesn't override the entity (light, switch, device, etc.)
    """Base class for Dynalite devices."""

    def __init__(self, area, bridge):
        """Initialize the device."""
        self._area = area
        self._bridge = bridge
        self._listeners = []

    @property
    def area_name(self):
        """Return the name of the area."""
        return self._bridge.get_area_name(self._area)

    @property
    def get_master_area(self):
        """Get the master area when combining entities from different Dynet areas to the same area."""
        return self._bridge.get_master_area(self._area)

    def add_listener(self, listener):
        """Add a listener for changes."""
        self._listeners.append(listener)

    def update_listeners(self, stop_fade=False):
        """Update all listeners."""
        for listener in self._listeners:
            listener(self, stop_fade)


class DynaliteChannelBaseDevice(DynaliteBaseDevice):
    """Representation of a Dynalite Channel as a Home Assistant device."""

    def __init__(self, area, channel, bridge):
        """Initialize the device."""
        self._channel = channel
        super().__init__(area, bridge)

    @property
    def available(self):
        """Return if device is available."""
        return self._bridge.available(CONF_CHANNEL, self._area, self._channel)

    @property
    def name(self):
        """Return the name of the device."""
        return self._bridge.get_channel_name(self._area, self._channel)

    @property
    def unique_id(self):
        """Return the ID of this device."""
        return "dynalite_area_" + str(self._area) + "_channel_" + str(self._channel)

    def stop_fade(self):
        """Update the listeners if STOP FADE is received."""
        self.update_listeners(True)


class DynaliteMultiDevice(DynaliteBaseDevice):
    """Representation of two Dynalite Presets as an on/off switch."""

    def __init__(self, num_devices, area, bridge):
        """Initialize the device."""
        self._devices = {}
        self._num_devices = num_devices
        super().__init__(area, bridge)

    @property
    def name(self):
        """Return the name of the device."""
        return self._bridge.get_multi_name(self._area)

    def get_device(self, devnum):
        """Get the first or second device."""
        return self._devices.get(devnum)

    def set_device(self, devnum, device):
        """Set one of the attached devices."""
        self._devices[devnum] = device
        device.add_listener(self.listener)

    def listener(self, device, stop_fade):
        """Update the device since its internal devices changed."""
        self._bridge.update_device(self)
