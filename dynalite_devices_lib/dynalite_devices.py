"""Class to create devices from a Dynalite hub."""

import asyncio

from .config import DynaliteConfig
from .const import (
    CONF_ACT_LEVEL,
    CONF_ACTION,
    CONF_ACTION_CMD,
    CONF_ACTION_REPORT,
    CONF_ACTION_STOP,
    CONF_ACTIVE_INIT,
    CONF_ACTIVE_ON,
    CONF_ALL,
    CONF_AREA,
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
    CONF_NONE,
    CONF_OPEN_PRESET,
    CONF_PRESET,
    CONF_ROOM,
    CONF_ROOM_OFF,
    CONF_ROOM_ON,
    CONF_STOP_PRESET,
    CONF_TEMPLATE,
    CONF_TILT_TIME,
    CONF_TIME_COVER,
    CONF_TRGT_LEVEL,
    DEFAULT_CHANNEL_TYPE,
    EVENT_CHANNEL,
    EVENT_CONNECTED,
    EVENT_DISCONNECTED,
    EVENT_PRESET,
    LOGGER,
)
from .cover import DynaliteTimeCoverDevice, DynaliteTimeCoverWithTiltDevice
from .dynalite import Dynalite
from .dynalitebase import DynaliteBaseDevice
from .light import DynaliteChannelLightDevice
from .switch import (
    DynaliteChannelSwitchDevice,
    DynaliteDualPresetSwitchDevice,
    DynalitePresetSwitchDevice,
)


class BridgeError(Exception):
    """For errors in the Dynalite bridge."""

    def __init__(self, message):
        """Initialize the exception."""
        self.message = message
        super().__init__(message)


class DynaliteDevices:
    """Manages a single Dynalite bridge."""

    def __init__(self, new_device_func=None, update_device_func=None):
        """Initialize the system."""
        self._host = None
        self._port = None
        self.name = None  # public
        self._poll_timer = None
        self._default_fade = None
        self._active = None
        self._auto_discover = None
        self._loop = None
        self._new_device_func = new_device_func
        self._update_device_func = update_device_func
        self._configured = False
        self.connected = False  # public
        self._added_presets = {}
        self._added_channels = {}
        self._added_room_switches = {}
        self._added_time_covers = {}
        self._waiting_devices = []
        self._timer_active = False
        self._timer_callbacks = set()
        self._area = {}
        self._dynalite = Dynalite(broadcast_func=self.handle_event)
        self._resetting = False

    async def async_setup(self):
        """Set up a Dynalite bridge based on host parameter in the config."""
        LOGGER.debug("bridge async_setup")
        if not self._loop:
            self._loop = asyncio.get_running_loop()
        # Run the dynalite object. Assumes self.configure() has been called
        self._resetting = False
        self.connected = await self._dynalite.connect(self._host, self._port)
        return self.connected

    def configure(self, config):
        """Configure a Dynalite bridge."""
        LOGGER.debug("bridge async_configure - %s", config)
        self._configured = False
        configurator = DynaliteConfig(config)
        # insert the global values
        self._host = configurator.host
        self._port = configurator.port
        self.name = configurator.name
        self._auto_discover = configurator.auto_discover
        self._active = configurator.active
        self._poll_timer = configurator.poll_timer
        self._default_fade = configurator.default_fade
        self._area = configurator.area
        # now register the channels and presets and ask for initial status if needed
        for area in self._area:
            if self._active in [CONF_ACTIVE_INIT, CONF_ACTIVE_ON]:
                self._dynalite.request_area_preset(area)
            for channel in self._area[area][CONF_CHANNEL]:
                self.create_channel_if_new(area, channel)
                if self._active in [CONF_ACTIVE_INIT, CONF_ACTIVE_ON]:
                    self._dynalite.request_channel_level(area, channel)
            for preset in self._area[area][CONF_PRESET]:
                self.create_preset_if_new(area, preset)
        # register the rooms (switches on presets 1/4)
        # all the devices should be created for channels and presets
        self.register_rooms()
        # register the time covers
        self.register_time_covers()
        # callback for all devices
        if self._new_device_func and self._waiting_devices:
            self._new_device_func(self._waiting_devices)
            self._waiting_devices = []
        self._configured = True

    def register_rooms(self):
        """Register the room switches from two normal presets each."""
        for area, area_config in self._area.items():
            if area_config.get(CONF_TEMPLATE, "") == CONF_ROOM:
                if area in self._added_room_switches:
                    continue
                new_device = DynaliteDualPresetSwitchDevice(area, self)
                self._added_room_switches[area] = new_device
                new_device.set_device(
                    1, self._added_presets[area][area_config[CONF_ROOM_ON]]
                )
                new_device.set_device(
                    2, self._added_presets[area][area_config[CONF_ROOM_OFF]]
                )
                self.register_new_device("switch", new_device, False)

    def register_time_covers(self):
        """Register the time covers from three presets and a channel each."""
        for area, area_config in self._area.items():
            if area_config.get(CONF_TEMPLATE, "") == CONF_TIME_COVER:
                if area in self._added_time_covers:
                    continue
                if area_config[CONF_TILT_TIME] == 0:
                    new_device = DynaliteTimeCoverDevice(area, self, self._poll_timer)
                else:
                    new_device = DynaliteTimeCoverWithTiltDevice(
                        area, self, self._poll_timer
                    )
                self._added_time_covers[area] = new_device
                new_device.set_device(
                    1, self._added_presets[area][area_config[CONF_OPEN_PRESET]]
                )
                new_device.set_device(
                    2, self._added_presets[area][area_config[CONF_CLOSE_PRESET]]
                )
                new_device.set_device(
                    3, self._added_presets[area][area_config[CONF_STOP_PRESET]]
                )
                if area_config[CONF_CHANNEL_COVER] != 0:
                    channel_device = self._added_channels[area][
                        area_config[CONF_CHANNEL_COVER]
                    ]
                else:
                    channel_device = DynaliteBaseDevice(area, self)
                new_device.set_device(4, channel_device)
                self.register_new_device("cover", new_device, False)

    def register_new_device(self, category, device, hidden):
        """Register a new device and group all the ones prior to CONFIGURED event together."""
        # after initial configuration, every new device gets sent on its own. The initial ones are bunched together
        if not hidden:
            if self._configured:
                if self._new_device_func:
                    self._new_device_func([device])
            else:  # send all the devices together when configured
                self._waiting_devices.append(device)

    def available(self, conf, area, item_num):
        """Return whether a device on the bridge is available."""
        if not self.connected:
            return False
        if conf in [CONF_CHANNEL, CONF_PRESET]:
            return bool(self._area.get(area, {}).get(conf, {}).get(item_num, False))
        assert conf == CONF_TEMPLATE
        return self._area.get(area, {}).get(CONF_TEMPLATE, "") == item_num

    def update_device(self, device):
        """Update one or more devices."""
        if self._update_device_func:
            self._update_device_func(device)

    def handle_event(self, event=None):
        """Handle all events."""
        LOGGER.debug("handle_event - type=%s event=%s", event.event_type, event.data)
        assert event.event_type in [
            EVENT_CONNECTED,
            EVENT_DISCONNECTED,
            EVENT_PRESET,
            EVENT_CHANNEL,
        ]
        if event.event_type == EVENT_CONNECTED:
            LOGGER.debug("Received CONNECTED message")
            self.connected = True
            self.update_device(CONF_ALL)
        elif event.event_type == EVENT_DISCONNECTED:
            LOGGER.debug("Received DISCONNECTED message")
            self.connected = False
            self.update_device(CONF_ALL)
        elif event.event_type == EVENT_PRESET:
            LOGGER.debug("Received PRESET message")
            self.handle_preset_selection(event)
        elif event.event_type == EVENT_CHANNEL:
            LOGGER.debug("Received PRESET message")
            self.handle_channel_change(event)

    def ensure_area(self, area):
        """Configure a default area if it is not yet in config."""
        if area not in self._area:
            LOGGER.debug("adding area %s that is not in config", area)
            # consider adding default presets to new areas (XXX)
            self._area[area] = DynaliteConfig.configure_area(
                area, {}, self._default_fade, {}, {}
            )

    def create_preset_if_new(self, area, preset):
        """Register a new preset."""
        LOGGER.debug("create_preset_if_new - area=%s preset=%s", area, preset)
        # if already configured, ignore
        if self._added_presets.get(area, {}).get(preset, False):
            return
        # if no autodiscover and not in config, ignore
        if not self._auto_discover:
            if not self._area.get(area, {}).get(CONF_PRESET, {}).get(preset, False):
                raise BridgeError(
                    f"No auto discovery and unknown preset (area {area} preset {preset}"
                )
        self.ensure_area(area)
        area_config = self._area[area]
        if preset not in area_config[CONF_PRESET]:
            area_config[CONF_PRESET][preset] = DynaliteConfig.configure_preset(
                preset,
                {},
                area_config[CONF_FADE],
                area_config.get(CONF_TEMPLATE, False),
            )
            # if the area is a template is a template, new presets should be hidden
            if area_config.get(CONF_TEMPLATE, False):
                area_config[CONF_PRESET][preset][CONF_HIDDEN_ENTITY] = True
        hidden = area_config[CONF_PRESET][preset].get(CONF_HIDDEN_ENTITY, False)
        new_device = DynalitePresetSwitchDevice(area, preset, self,)
        new_device.set_level(0)
        self.register_new_device("switch", new_device, hidden)
        if area not in self._added_presets:
            self._added_presets[area] = {}
        self._added_presets[area][preset] = new_device
        LOGGER.debug(
            "Creating Dynalite preset area=%s preset=%s hidden=%s", area, preset, hidden
        )

    def handle_preset_selection(self, event=None):
        """Change the selected preset."""
        LOGGER.debug("handle_preset_selection - event=%s", event.data)
        area = event.data[CONF_AREA]
        preset = event.data[CONF_PRESET]
        try:
            self.create_preset_if_new(area, preset)
        except BridgeError:
            # Unknown and no autodiscover
            return
        # Update all the preset devices
        for cur_preset_in_area in self._added_presets[area]:
            device = self._added_presets[area][cur_preset_in_area]
            if cur_preset_in_area == preset:
                device.set_level(1)
            else:
                device.set_level(0)
            self.update_device(device)
        # If active is set to full, query all channels in the area
        if self._active == CONF_ACTIVE_ON:
            for channel in self._area[area].get(CONF_CHANNEL, {}):
                self._dynalite.request_channel_level(area, channel)

    def create_channel_if_new(self, area, channel):
        """Register a new channel."""
        LOGGER.debug("create_channel_if_new - area=%s, channel=%s", area, channel)
        if channel == CONF_ALL:
            return
        # if already configured, ignore
        if self._added_channels.get(area, {}).get(channel, False):
            return
        # if no autodiscover and not in config, ignore
        if not self._auto_discover:
            if not self._area.get(area, {}).get(CONF_CHANNEL, {}).get(channel, False):
                raise BridgeError(
                    f"No auto discovery and unknown channel (area {area} channel {channel}"
                )
        self.ensure_area(area)
        area_config = self._area[area]
        if channel not in area_config[CONF_CHANNEL]:
            area_config[CONF_CHANNEL][channel] = DynaliteConfig.configure_channel(
                channel,
                {},
                area_config[CONF_FADE],
                area_config.get(CONF_TEMPLATE, False),
            )
        channel_config = area_config[CONF_CHANNEL][channel]
        LOGGER.debug("create_channel_if_new - channel_config=%s", channel_config)
        channel_type = channel_config.get(
            CONF_CHANNEL_TYPE, DEFAULT_CHANNEL_TYPE
        ).lower()
        hidden = channel_config.get(CONF_HIDDEN_ENTITY, False)
        if channel_type == "light":
            new_device = DynaliteChannelLightDevice(area, channel, self,)
            self.register_new_device("light", new_device, hidden)
        elif channel_type == "switch":
            new_device = DynaliteChannelSwitchDevice(area, channel, self,)
            self.register_new_device("switch", new_device, hidden)
        else:
            LOGGER.info("unknown chnanel type %s - ignoring", channel_type)
            return
        if area not in self._added_channels:
            self._added_channels[area] = {}
        self._added_channels[area][channel] = new_device
        LOGGER.debug("Creating Dynalite channel area=%s channel=%s", area, channel)

    def handle_channel_change(self, event=None):
        """Change the level of a channel."""
        LOGGER.debug("handle_channel_change - event=%s", event.data)
        LOGGER.debug("handle_channel_change called event = %s", event.msg)
        area = event.data[CONF_AREA]
        channel = event.data[CONF_CHANNEL]
        try:
            self.create_channel_if_new(area, channel)
        except BridgeError:
            # Unknown and no autodiscover
            return
        action = event.data[CONF_ACTION]
        assert action in [CONF_ACTION_REPORT, CONF_ACTION_CMD, CONF_ACTION_STOP]
        if action == CONF_ACTION_REPORT:
            actual_level = (255 - event.data[CONF_ACT_LEVEL]) / 254
            target_level = (255 - event.data[CONF_TRGT_LEVEL]) / 254
            channel_to_set = self._added_channels[area][channel]
            channel_to_set.update_level(actual_level, target_level)
            self.update_device(channel_to_set)
        elif action == CONF_ACTION_CMD:
            target_level = (255 - event.data[CONF_TRGT_LEVEL]) / 254
            # when there is only a "set channel level" command, assume that this is both the actual and the target
            actual_level = target_level
            channel_to_set = self._added_channels[area][channel]
            channel_to_set.update_level(actual_level, target_level)
            self.update_device(channel_to_set)
        elif action == CONF_ACTION_STOP:
            if channel == CONF_ALL:
                for channel in self._added_channels.get(area, {}):
                    channel_to_set = self._added_channels[area][channel]
                    channel_to_set.stop_fade()
                    self.update_device(channel_to_set)
            else:
                channel_to_set = self._added_channels[area][channel]
                channel_to_set.stop_fade()
                self.update_device(channel_to_set)

    def add_timer_listener(self, callback_func):
        """Add a listener to the timer and start if needed."""
        self._timer_callbacks.add(callback_func)
        if not self._timer_active:
            self._loop.call_later(self._poll_timer, self.timer_func)
            self._timer_active = True

    def remove_timer_listener(self, callback_func):
        """Remove a listener from a timer."""
        self._timer_callbacks.discard(callback_func)

    def timer_func(self):
        """Call callbacks and either schedule timer or stop."""
        if self._timer_callbacks and not self._resetting:
            for callback in self._timer_callbacks:
                self._loop.call_soon(callback)
            self._loop.call_later(self._poll_timer, self.timer_func)
        else:
            self._timer_active = False

    def set_channel_level(self, area, channel, level, fade):
        """Set the level for a channel."""
        fade = self._area[area][CONF_CHANNEL][channel][CONF_FADE]
        self._dynalite.set_channel_level(area, channel, level, fade)

    def select_preset(self, area, preset, fade):
        """Select a preset in an area."""
        self._dynalite.select_preset(area, preset, fade)

    def get_area_name(self, area):
        """Return the name of an area."""
        return self._area[area][CONF_NAME]

    def get_channel_name(self, area, channel):
        """Return the name of a channel."""
        return f"{self._area[area][CONF_NAME]} {self._area[area][CONF_CHANNEL][channel][CONF_NAME]}"

    def get_channel_fade(self, area, channel):
        """Return the fade of a channel."""
        return self._area[area][CONF_CHANNEL][channel][CONF_FADE]

    def get_preset_name(self, area, preset):
        """Return the name of a preset."""
        return f"{self._area[area][CONF_NAME]} {self._area[area][CONF_PRESET][preset][CONF_NAME]}"

    def get_preset_fade(self, area, preset):
        """Return the fade of a preset."""
        return self._area[area][CONF_PRESET][preset][CONF_FADE]

    def get_multi_name(self, area):
        """Return the name of a multi-device."""
        return self._area[area][CONF_NAME]

    def get_device_class(self, area):
        """Return the class for a blind."""
        return self._area[area][CONF_DEVICE_CLASS]

    def get_cover_duration(self, area):
        """Return the class for a blind."""
        return self._area[area][CONF_DURATION]

    def get_cover_tilt_duration(self, area):
        """Return the class for a blind."""
        return self._area[area][CONF_TILT_TIME]

    def get_master_area(self, area):
        """Get the master area when combining entities from different Dynet areas to the same area."""
        assert area in self._area
        area_config = self._area[area]
        master_area = area_config[CONF_NAME]
        if CONF_AREA_OVERRIDE in area_config:
            override_area = area_config[CONF_AREA_OVERRIDE]
            master_area = override_area if override_area.lower() != CONF_NONE else ""
        return master_area

    async def async_reset(self):
        """Reset the connections and timers."""
        self._resetting = True
        await self._dynalite.async_reset()
        while self._timer_active:
            await asyncio.sleep(0.1)
