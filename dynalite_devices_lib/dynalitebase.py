"""Support for the Dynalite devices."""

from .const import DOMAIN


class DynaliteBaseDevice:  # Deriving from Object so it doesn't override the entity (light, switch, device, etc.)
    """Base class for Dynalite devices."""

    def __init__(self, area, area_name, name, master_area, bridge):
        """Initialize the device."""
        self._area = area
        self._area_name = area_name
        self._name = name
        self._master_area = master_area
        self._bridge = bridge
        self._hidden = False
        self._listeners = []

    @property
    def name(self):
        """Return the name of the device."""
        return self._name

    @property
    def area_name(self):
        """Return the name of the area."""
        return self._area_name

    @property
    def available(self):
        """Return if device is available."""
        return self._bridge.available

    @property
    def hidden(self):
        """Return true if this switch should be hidden from UI."""
        return self._hidden

    def set_hidden(self, hidden):
        """Set device hidden property."""
        self._hidden = hidden

    @property
    def device_info(self):
        """Rerturn the device info."""
        return {
            "identifiers": {(DOMAIN, self.unique_id)},
            "name": self.name,
            "manufacturer": "Dynalite",
        }

    @property
    def get_master_area(self):
        """Get the master area when combining entities from different Dynet areas to the same area."""
        return self._master_area

    def add_listener(self, listener):
        """Add a listener for changes."""
        self._listeners.append(listener)

    def update_listeners(self, stop_fade=False):
        """Update all listeners."""
        for listener in self._listeners:
            listener(self, stop_fade)


class DynaliteChannelBaseDevice(DynaliteBaseDevice):
    """Representation of a Dynalite Channel as a Home Assistant device."""

    def __init__(
        self, area, area_name, channel, name, type, master_area, bridge, device
    ):
        """Initialize the device."""
        self._channel = channel
        self._type = type
        self._device = device
        super().__init__(area, area_name, name, master_area, bridge)

    @property
    def unique_id(self):
        """Return the ID of this device."""
        return "dynalite_area_" + str(self._area) + "_channel_" + str(self._channel)

    def stop_fade(self):
        """Update the listeners if STOP FADE is received."""
        self.update_listeners(True)

class DynaliteMultiDevice(DynaliteBaseDevice):
    """Representation of two Dynalite Presets as an on/off switch."""

    def __init__(self, num_devices, area, area_name, name, master_area, bridge):
        """Initialize the device."""
        super().__init__(area, area_name, name, master_area, bridge)
        self._devices = {}
        self._num_devices = num_devices

    def get_device(self, devnum):
        """Get the first or second device."""
        return self._devices.get(devnum)

    @property
    def available(self):
        """Return if dual device is available."""
        for i in range(1, self._num_devices + 1):
            if not self.get_device(i):
                return False
        return super().available

    def set_device(self, devnum, device):
        """Set one of the attached devices."""
        self._devices[devnum] = device
        device.add_listener(self.listener)
        if self.available:
            self._bridge.updateDevice(self)

    def listener(self, device, stop_fade):
        """Update the device since its internal devices changed."""
        self._bridge.updateDevice(self)
