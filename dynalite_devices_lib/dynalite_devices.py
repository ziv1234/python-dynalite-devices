"""Class to create devices from a Dynalite hub."""

import copy
import asyncio

from .const import (
    LOGGER,
    DEFAULT_COVER_CHANNEL_CLASS,
    CONF_TRIGGER,
    CONF_CHANNEL_TYPE,
    CONF_AUTO_DISCOVER,
    CONF_HIDDEN_ENTITY,
    CONF_AREA_OVERRIDE,
    CONF_CHANNEL_CLASS,
    CONF_TEMPLATE,
    CONF_ROOM_ON,
    CONF_ROOM_OFF,
    DEFAULT_TEMPLATES,
    CONF_ROOM,
    DEFAULT_CHANNEL_TYPE,
    CONF_CHANNEL_COVER,
    CONF_NONE,
    CONF_TIME_COVER,
    CONF_OPEN_PRESET,
    CONF_CLOSE_PRESET,
    CONF_STOP_PRESET,
    CONF_DURATION,
    CONF_TILT_TIME,
    CONF_CHANNEL,
    CONF_AREA,
    CONF_ACTIVE,
    CONF_ACTIVE_ON,
    CONF_ACTIVE_OFF,
    CONF_ACTIVE_INIT,
    CONF_POLL_TIMER,
    CONF_NAME,
    CONF_PRESET,
    CONF_NO_DEFAULT,
    EVENT_NEWPRESET,
    EVENT_NEWCHANNEL,
    EVENT_PRESET,
    EVENT_CHANNEL,
    EVENT_CONNECTED,
    EVENT_DISCONNECTED,
    EVENT_CONFIGURED,
    CONF_ACTION,
    CONF_ACTION_REPORT,
    CONF_ACTION_CMD,
    CONF_TRGT_LEVEL,
    CONF_ACT_LEVEL,
    CONF_ALL,
    CONF_HOST,
    CONF_PORT,
    DEFAULT_PORT,
    DEFAULT_NAME,
    CONF_DEFAULT,
    CONF_FADE,
    
)
from .dynalite import Dynalite
from .light import DynaliteChannelLightDevice
from .switch import (
    DynaliteChannelSwitchDevice,
    DynalitePresetSwitchDevice,
    DynaliteDualPresetSwitchDevice,
)
from .cover import DynaliteTimeCoverDevice, DynaliteTimeCoverWithTiltDevice
from .dynalitebase import DynaliteBaseDevice


class BridgeError(Exception):
    """For errors in the Dynalite bridge."""

    def __init__(self, message):
        """Initialize the exception."""
        self.message = message


class DynaliteDevices:
    """Manages a single Dynalite bridge."""

    def __init__(self, loop=None, newDeviceFunc=None, updateDeviceFunc=None):
        """Initialize the system."""
        self.active = None
        self.auto_discover = None
        self.loop = loop
        self.newDeviceFunc = newDeviceFunc
        self.updateDeviceFunc = updateDeviceFunc
        self.configured = False
        self.connected = False
        self.added_presets = {}
        self.added_channels = {}
        self.added_room_switches = {}
        self.added_time_covers = {}
        self.waiting_devices = []
        self.timer_active = False
        self.timer_callbacks = set()
        self.template = {}
        self.area = {}

    async def async_setup(self):
        """Set up a Dynalite bridge based on host parameter in the config."""
        LOGGER.debug("bridge async_setup")
        if not self.loop:
            self.loop = asyncio.get_running_loop()
        # Run the dynalite object. Assumes self.configure() has been called
        # self._dynalite = Dynalite(host=self.host, port=self.port, active=self.active, poll_timer=self.poll_timer, loop=self.loop)
        self._dynalite = Dynalite(self.port, self.host, self.active, self.poll_timer, self.loop)
        eventHandler = self._dynalite.addListener(listenerFunction=self.handleEvent)
        eventHandler.monitorEvent("*")
        presetChangeHandler = self._dynalite.addListener(
            listenerFunction=self.handle_preset_selection
        )
        presetChangeHandler.monitorEvent(EVENT_PRESET)
        channelChangeHandler = self._dynalite.addListener(
            listenerFunction=self.handle_channel_change
        )
        channelChangeHandler.monitorEvent(EVENT_CHANNEL)
        self._dynalite.start()
        return True

    def configure(self, config):
        """Configure a Dynalite bridge based on host parameter in the config."""
        LOGGER.debug("bridge async_configure - %s", config)
        self.configured = False
        # insert the global values
        self.host = config[CONF_HOST]
        self.port = config.get(CONF_PORT, DEFAULT_PORT)
        self.name = config.get(CONF_NAME, f"{DEFAULT_NAME}-{self.host}")
        self.auto_discover = config.get(CONF_AUTO_DISCOVER, False)
        self.active = config.get(CONF_ACTIVE, CONF_ACTIVE_INIT)
        if self.active is True:
            self.active = CONF_ACTIVE_ON
        if self.active is False:
            self.active = CONF_ACTIVE_OFF
        self.poll_timer = config.get(CONF_POLL_TIMER, 1.0)
        self.default_fade = config.get(CONF_DEFAULT, {}).get(CONF_FADE, 0)
        # create the templates
        config_templates = config.get(CONF_TEMPLATE, {})
        for template in DEFAULT_TEMPLATES:
            self.template[template] = {}
            cur_template = config_templates.get(template, {})
            for conf in DEFAULT_TEMPLATES[template]:
                self.template[template][conf] = cur_template.get(conf, DEFAULT_TEMPLATES[template][conf])
        # create default presets
        config_presets = config.get(CONF_DEFAULT,{})
        default_presets = {}
        for preset in config_presets:
            cur_config = config_presets[preset]
            default_presets[int(preset)] = {
                CONF_NAME: cur_config.get(CONF_NAME, f"Preset {preset}"),
                CONF_FADE: cur_config.get(CONF_FADE, self.default_fade)
            }
        # create the areas with their channels and presets
        for area_val in config.get(CONF_AREA, {}): # may be a string '123'
            area = int(area_val)
            area_config = config[CONF_AREA].get(area_val)
            self.area[area] = {
                CONF_NAME: area_config.get(CONF_NAME, f"Area {area}"),
                CONF_FADE: area_config.get(CONF_FADE, self.default_fade),
            }
            area_presets = {}
            area_channels = {}
            # User defined presets and channels first, then template presets, then defaults
            for preset in area_config.get(CONF_PRESET, {}):
                preset_config = area_config[CONF_PRESET][preset]
                area_presets[int(preset)] = {
                    CONF_NAME: preset_config.get(CONF_NAME, f"Preset {preset}"),
                    CONF_FADE: preset_config.get(CONF_FADE, self.area[area][CONF_FADE]),
                }
            for channel in area_config.get(CONF_CHANNEL, {}):
                channel_config = area_config[CONF_CHANNEL][channel]
                area_channels[int(channel)] = {
                    CONF_NAME: channel_config.get(CONF_NAME, f"Channel {channel}"),
                    CONF_FADE: channel_config.get(CONF_FADE, self.area[area][CONF_FADE]),
                }
            # add the entities implicitly defined by templates
            template = area_config.get(CONF_TEMPLATE)
            if template:
                # Which type of value is a specific CONF
                conf_presets = [
                    CONF_ROOM_ON, 
                    CONF_ROOM_OFF, 
                    CONF_TRIGGER, 
                    CONF_OPEN_PRESET,
                    CONF_CLOSE_PRESET,
                    CONF_STOP_PRESET,
                ]
                conf_values = [CONF_CHANNEL_CLASS, CONF_DURATION, CONF_TILT_TIME]
                conf_channels = [CONF_CHANNEL_COVER]
                
                for conf in self.template[template]:
                    conf_value = area_config.get(conf, self.template[template][conf])
                    if conf in conf_presets:
                        preset = int(conf_value)
                        if preset not in area_presets:
                            area_presets[preset] = {
                                CONF_NAME: f"Preset {preset}",
                                CONF_FADE: self.area[area][CONF_FADE],
                                # Trigger is the only exception
                                CONF_HIDDEN_ENTITY: (template != CONF_TRIGGER)
                            }
                        self.area[area][conf] = preset
                    elif conf in conf_channels:
                        channel = int(conf_value)
                        if channel not in area_channels:
                            area_channels[channel] = {
                                CONF_NAME: f"Channel {channel}",
                                CONF_FADE: self.area[area][CONF_FADE],
                                CONF_HIDDEN_ENTITY: True
                            }
                        self.area[area][conf] = channel
                    else:
                        assert conf in conf_values
                        self.area[area][conf] = conf_value
            # Default presets
            if not area_config.get(CONF_NO_DEFAULT, False):
                for preset in default_presets:
                    if preset not in area_presets:
                        area_presets[preset] = default_presets[preset]
            self.area[area][CONF_PRESET] = area_presets
            self.area[area][CONF_CHANNEL] = area_channels
            # now register the channels and presets
            for channel in area_channels:
                self.create_channel_if_new(area, channel)
            for preset in area_presets:
                self.create_preset_if_new(area, preset)

        # register the rooms (switches on presets 1/4)
        # all the devices should be created for channels and presets
        self.register_rooms()
        # register the time covers
        self.register_time_covers()
        # callback for all devices
        if self.newDeviceFunc and self.waiting_devices:
            self.newDeviceFunc(self.waiting_devices)
            self.waiting_devices = []
        self.configured = True

    def register_rooms(self):
        """Register the room switches from two normal presets each."""
        for area, area_config in self.area.items():
            if area_config.get(CONF_TEMPLATE, "") == CONF_ROOM:
                if area in self.added_room_switches:
                    continue
                new_device = DynaliteDualPresetSwitchDevice(
                    area,
                    self,
                )
                self.added_room_switches[area] = new_device
                new_device.set_device(1, self.added_presets[area][area_config][CONF_ROOM_ON])
                new_device.set_device(2, self.added_presets[area][area_config][CONF_ROOM_OFF])
                self.registerNewDevice("switch", new_device, False)

    def register_time_covers(self):
        """Register the time covers from three presets and a channel each."""
        for area, area_config in self.area.items():
            if area_config.get(CONF_TEMPLATE, "") == CONF_TIME_COVER:
                if area in self.added_time_covers:
                    continue
                if area_config[CONF_TILT_TIME] == 0:
                    new_device = DynaliteTimeCoverDevice(area, self)
                else:
                    new_device = DynaliteTimeCoverWithTiltDevice(area, self)
                self.added_time_covers[area] = new_device
                new_device.set_device(1, self.added_presets[area][area_config][CONF_OPEN_PRESET])
                new_device.set_device(2, self.added_presets[area][area_config][CONF_CLOSE_PRESET])
                new_device.set_device(3, self.added_presets[area][area_config][CONF_STOP_PRESET])
                if area_config[CONF_CHANNEL_COVER] != 0:
                    channel_device = self.added_channels[area][area_config][CONF_CHANNEL_COVER]
                else:
                    channel_device = DynaliteBaseDevice(area, self)
                new_device.set_device(4, channel_device)
                self.registerNewDevice("cover", newDevice, False)

    def registerNewDevice(self, category, device, hidden):
        """Register a new device and group all the ones prior to CONFIGURED event together."""
        # after initial configuration, every new device gets sent on its own. The initial ones are bunched together
        if not hidden:
            if self.configured:  
                if self.newDeviceFunc:
                    self.newDeviceFunc([device])
            else:  # send all the devices together when configured
                self.waiting_devices.append(device)

    @property
    def available(self):
        """Return whether bridge is available."""
        return self.connected

    def updateDevice(self, device):
        """Update one or more devices."""
        if self.updateDeviceFunc:
            self.updateDeviceFunc(device)

    def handleEvent(self, event=None, dynalite=None):
        """Handle all events."""
        LOGGER.debug("handleEvent - type=%s event=%s" % (event.eventType, event.data))
        if event.eventType == EVENT_CONNECTED:
            LOGGER.debug("received CONNECTED message")
            self.connected = True
            self.updateDevice(CONF_ALL)
        elif event.eventType == EVENT_DISCONNECTED:
            LOGGER.debug("received DISCONNECTED message")
            self.connected = False
            self.updateDevice(CONF_ALL)
        return

    def get_channel_name(self, area, channel):
        return f"{self.area[area][CONF_NAME]} {self.area[area][CONF_CHANNEL][channel][CONF_NAME]}"

    def getMasterArea(self, area):
        """Get the master area when combining entities from different Dynet areas to the same area."""
        if area not in self.area:
            LOGGER.error("getMasterArea - we should not get here")
            raise BridgeError("getMasterArea - area " + str(area) + "is not in config")
        area_config = self.area[area]
        master_area = area_config[CONF_NAME]
        if CONF_AREA_OVERRIDE in area_config:
            override_area = area_config[CONF_AREA_OVERRIDE]
            master_area = override_area if override_area.lower() != CONF_NONE else ""
        return master_area

    def create_preset_if_new(self, area, preset):
        """Register a new preset."""
        LOGGER.debug("create_preset_if_new - area=%s preset=%s", area, preset)

        try:
            if self.added_presets[area][preset]:
                return
        except KeyError:
            pass

        if area not in self.area:
            LOGGER.debug(f"adding area {area} that is not in config")
            self.area[area] = {CONF_NAME: F"Area {area}", CONF_FADE: self.default_fade}
        areaConfig = self.area[area]

        if CONF_PRESET not in areaConfig:
            areaConfig[CONF_PRESET] = {}
        if preset not in areaConfig[CONF_PRESET]:
            areaConfig[CONF_PRESET][preset] = {
                CONF_NAME: f"Preset {preset}",
                CONF_FADE: areaConfig[CONF_FADE],
                CONF_HIDDEN_ENTITY: not self.auto_discover,
            }
        try:
            # If the name is explicitly defined, use it
            presetName = areaConfig[CONF_PRESET][str(preset)][CONF_NAME]  
        except KeyError:
            presetName = "Preset " + str(preset)
        
        newDevice = DynalitePresetSwitchDevice(
            area,
            preset,
            self,
        )

        try:
            hidden = areaConfig[CONF_PRESET][str(preset)][CONF_HIDDEN_ENTITY]
        except KeyError:
            hidden = False

        try:
            # templates may make some elements hidden or register the preset
            template = areaConfig[CONF_TEMPLATE]  
            if template == CONF_ROOM:
                # in a template room, the presets will all be in the room switch
                hidden = True  
                # if it is not there yet, it will be added when the room switch will be created
                if int(area) in self.added_room_switches:  
                    multiDevice = self.added_room_switches[int(area)]
                    if int(preset) == int(areaConfig[CONF_ROOM_ON]):
                        multiDevice.set_device(1, newDevice)
                    if int(preset) == int(areaConfig[CONF_ROOM_OFF]):
                        multiDevice.set_device(2, newDevice)
            elif template == CONF_TRIGGER:
                if int(preset) != areaConfig[CONF_TRIGGER]:
                    hidden = True
            elif template in [CONF_HIDDEN_ENTITY, CONF_CHANNEL_COVER]:
                hidden = True
            elif template == CONF_TIME_COVER:
                # in a template room, the presets will all be in the time cover
                hidden = True  
                # if it is not there yet, it will be added when the time cover will be created
                if int(area) in self.added_time_covers:
                    multiDevice = self.added_time_covers[int(area)]
                    if int(preset) == int(areaConfig[CONF_OPEN_PRESET]):
                        multiDevice.set_device(1, newDevice)
                    if int(preset) == int(areaConfig[CONF_CLOSE_PRESET]):
                        multiDevice.set_device(2, newDevice)
                    if int(preset) == int(areaConfig[CONF_STOP_PRESET]):
                        multiDevice.set_device(3, newDevice)
            else:
                LOGGER.error(
                    "Unknown template "
                    + template
                    + ". Should have been caught in config_validation"
                )
        except KeyError:
            pass

        newDevice.set_level(0)
        self.registerNewDevice("switch", newDevice, hidden)
        if area not in self.added_presets:
            self.added_presets[area] = {}
        self.added_presets[area][preset] = newDevice
        LOGGER.debug(
            "Creating Dynalite preset area=%s preset=%s hidden=%s", area, preset, hidden
        )

    def handle_preset_selection(self, event=None, dynalite=None):
        """Change the selected preset."""
        LOGGER.debug("handle_preset_selection - event=%s", event.data)
        area = event.data[CONF_AREA]
        preset = event.data[CONF_PRESET]
        self.create_preset_if_new(area, preset)

        # Update all the preset devices
        for curPresetInArea in self.added_presets[int(area)]:
            device = self.added_presets[area][curPresetInArea]
            if curPresetInArea == preset:
                device.set_level(1)
            else:
                device.set_level(0)
            self.updateDevice(device)

    def create_channel_if_new(self, area, channel):
        """Register a new channel."""
        LOGGER.debug("create_channel_if_new - area=%s, channel=%s", area, channel)
        LOGGER.debug("%s", self.added_channels)
        try:
            if self.added_channels[area][channel]:
                return
        except KeyError:
            pass

        if area not in self.area:
            LOGGER.debug(f"adding area {area} that is not in config")
            self.area[area] = {CONF_NAME: F"Area {area}", CONF_FADE: self.default_fade}
        areaConfig = self.area[area]

        if CONF_CHANNEL not in areaConfig:
            areaConfig[CONF_CHANNEL] = {}
        if channel not in areaConfig[CONF_CHANNEL]:
            areaConfig[CONF_CHANNEL][channel] = {
                CONF_NAME: f"Channel {channel}",
                CONF_FADE: areaConfig[CONF_FADE],
                CONF_HIDDEN_ENTITY: not self.auto_discover,
            }
        try:
            # If the name is explicitly defined, use it
            channelName = areaConfig[CONF_CHANNEL][channel][CONF_NAME]  
        except (KeyError, TypeError):
            # If not explicitly defined, use "areaname Channel X"
            channelName = "Channel " + str(channel)

        try:
            channelConfig = areaConfig[CONF_CHANNEL][channel]
        except KeyError:
            channelConfig = None
        LOGGER.debug("handleNewChannel - channelConfig=%s" % channelConfig)
        channelType = (
            channelConfig[CONF_CHANNEL_TYPE].lower()
            if channelConfig and CONF_CHANNEL_TYPE in channelConfig
            else DEFAULT_CHANNEL_TYPE
        )
        hassArea = self.getMasterArea(area)
        hidden = (channelConfig and CONF_HIDDEN_ENTITY in channelConfig and channelConfig[CONF_HIDDEN_ENTITY]) or \
                 (self.area[area].get(CONF_TEMPLATE) == CONF_HIDDEN_ENTITY)
        if channelType == "light":
            newDevice = DynaliteChannelLightDevice(
                area,
                channel,
                self,
            )
            self.registerNewDevice("light", newDevice, hidden)
        elif channelType == "switch":
            newDevice = DynaliteChannelSwitchDevice(
                area,
                channel,
                self,
            )
            self.registerNewDevice("switch", newDevice, hidden)
        else:
            LOGGER.info("unknown chnanel type %s - ignoring", channelType)
            return
        if area not in self.added_channels:
            self.added_channels[area] = {}
        self.added_channels[area][channel] = newDevice
        LOGGER.debug("Creating Dynalite channel area=%s channel=%s name=%s", area, channel, channelName)

    def handle_channel_change(self, event=None, dynalite=None):
        """Change the level of a channel."""
        LOGGER.debug("handle_channel_change - event=%s" % event.data)
        LOGGER.debug("handle_channel_change called event = %s" % event.msg)
        area = event.data[CONF_AREA]
        channel = event.data[CONF_CHANNEL]
        self.create_channel_if_new(area, channel)

        action = event.data[CONF_ACTION]
        if action == CONF_ACTION_REPORT:
            actual_level = (255 - event.data[CONF_ACT_LEVEL]) / 254
            target_level = (255 - event.data[CONF_TRGT_LEVEL]) / 254
        elif action == CONF_ACTION_CMD:
            if CONF_TRGT_LEVEL in event.data:
                target_level = (255 - event.data[CONF_TRGT_LEVEL]) / 254
                # when there is only a "set channel level" command, assume that this is both the actual and the target
                actual_level = target_level
            else: # stop fade command
                try:
                    if channel == CONF_ALL:
                        for channel in self.added_channels[int(area)]:
                            channelToSet = self.added_channels[int(area)][channel]
                            channelToSet.stop_fade()
                            self.updateDevice(channelToSet)  
                    else:
                        channelToSet = self.added_channels[int(area)][int(channel)]
                        channelToSet.stop_fade()
                        self.updateDevice(channelToSet)  
                except KeyError:
                    pass
                return
        else:
            LOGGER.error("unknown action for channel change %s", action)
            return
        try:
            channelToSet = self.added_channels[int(area)][int(channel)]
            channelToSet.update_level(actual_level, target_level)
            # to only call if it was already added to ha
            self.updateDevice(channelToSet)  
        except KeyError:
            pass
            
    def add_timer_listener(self, callback_func):
        self.timer_callbacks.add(callback_func)
        if not self.timer_active:
            self.loop.call_later(1, self.timer_func)
            self.timer_active = True
            
    def remove_timer_listener(self, callback_func):
        self.timer_callbacks.discard(callback_func)
        
    def timer_func(self):
        if self.timer_callbacks:
            for callback in self.timer_callbacks:
                self.loop.call_soon(callback)
            self.loop.call_later(1, self.timer_func)
        else:
            self.timer_active = False
            
    def set_channel_level(self, area, channel, level):
        self._dynalite.set_channel_level(area, channel, level)
        
    def select_preset(self, area, preset):
        self._dynalite.select_preset(area, preset)
        