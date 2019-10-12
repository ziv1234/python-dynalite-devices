"""Support for the Dynalite devices."""
import asyncio
import logging
import pprint

from .const import DOMAIN, LOGGER


class DynaliteBaseDevice:  # Deriving from Object so it doesn't override the entity (light, switch, device, etc.)
    def __init__(self, area, area_name, name, master_area, bridge):
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
        """Return the name of the device."""
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
        self._hidden = hidden

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self.unique_id)},
            "name": self.name,
            "manufacturer": "Dynalite",
        }

    @property
    def get_master_area(self):
        return self._master_area

    def add_listener(self, listener):
        self._listeners.append(listener)

    def update_listeners(self):
        for listener in self._listeners:
            listener()


class DynaliteChannelBaseDevice(DynaliteBaseDevice):
    """Representation of a Dynalite Channel as a Home Assistant device."""

    def __init__(self, area, area_name, channel, name, type, master_area, bridge, device):
        self._channel = channel
        self._type = type
        self._device = device
        super().__init__(area, area_name, name, master_area, bridge)

    @property
    def unique_id(self):
        """Return the ID of this device."""
        return "dynalite_area_" + str(self._area) + "_channel_" + str(self._channel)


class DynaliteDualPresetDevice(DynaliteBaseDevice):
    """Representation of a Dynalite Preset as a Home Assistant Switch."""

    def __init__(self, area, area_name, name, master_area, bridge):
        super().__init__(area, area_name, name, master_area, bridge)
        self._devices = {}

    def get_device(self, devnum):
        return self._devices.get(devnum)

    @property
    def available(self):
        """Return if dual device is available."""
        return self.get_device(1) and self.get_device(2) and super().available

    def set_device(self, devnum, device):
        self._devices[devnum] = device
        device.add_listener(self.listener)
        if self.available:
            self._bridge.updateDevice(self)

    def listener(self):
        self._bridge.updateDevice(self)
