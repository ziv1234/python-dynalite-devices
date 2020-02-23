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

    def __init__(self, config, loop=None, newDeviceFunc=None, updateDeviceFunc=None):
        """Initialize the system."""
        self.config = copy.deepcopy(config)
        active_val = self.config[CONF_ACTIVE] if CONF_ACTIVE in self.config else CONF_ACTIVE_OFF
        # fix in the case of boolean values
        if active_val is True:
            active_val = CONF_ACTIVE_ON
        elif active_val is False:
            active_val = CONF_ACTIVE_OFF
        self.config[CONF_ACTIVE] = active_val
        self.auto_discover = self.config[CONF_AUTO_DISCOVER] if CONF_AUTO_DISCOVER in self.config else False
        self.loop = loop
        self.newDeviceFunc = newDeviceFunc
        self.updateDeviceFunc = updateDeviceFunc
        self.devices = []
        self.waiting_devices = []
        self.configured = False
        self.connected = False
        self.added_presets = {}
        self.added_channels = {}
        self.added_room_switches = {}
        self.added_time_covers = {}
        self.timer_active = False
        self.timer_callbacks = set()

    async def async_setup(self, tries=0):
        """Set up a Dynalite bridge based on host parameter in the config."""
        LOGGER.debug("bridge async_setup - %s", self.config)
        if not self.loop:
            self.loop = asyncio.get_running_loop()
        await self.async_configure()
        LOGGER.debug("received CONFIGURED message XXX")
        self.configured = True
        if self.newDeviceFunc and self.waiting_devices:
            self.newDeviceFunc(self.waiting_devices)
            self.waiting_devices = []
        # Configure the dynalite object
        self._dynalite = Dynalite(config=self.config, loop=self.loop)
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

    async def async_configure(self, config=None):
        """Configure a Dynalite bridge based on host parameter in the config."""
        LOGGER.debug("bridge async_configure - %s", config)
        if config:
            self.config = copy.deepcopy(config)
        # insert the templates
        if CONF_TEMPLATE not in self.config:
            LOGGER.debug(CONF_TEMPLATE + " not in config - using defaults")
            self.config[CONF_TEMPLATE] = DEFAULT_TEMPLATES
        else:
            for template in DEFAULT_TEMPLATES:
                if template not in self.config[CONF_TEMPLATE]:
                    LOGGER.debug(
                        "%s not in " + CONF_TEMPLATE + " using default", template
                    )
                    self.config[CONF_TEMPLATE][template] = DEFAULT_TEMPLATES[template]
                else:
                    for param in DEFAULT_TEMPLATES[template]:
                        if param not in self.config[CONF_TEMPLATE][template]:
                            self.config[CONF_TEMPLATE][template][
                                param
                            ] = DEFAULT_TEMPLATES[template][param]
        # add the entities implicitly defined by templates
        for curArea in self.config[CONF_AREA]:
            areaConfig = self.config[CONF_AREA][curArea]
            if CONF_TEMPLATE in areaConfig:
                template = self.config[CONF_AREA][curArea][CONF_TEMPLATE]
                template_params = self.getTemplateParams(curArea)
                if template == CONF_ROOM:
                    areaConfig[CONF_NO_DEFAULT] = True
                    for conf in [CONF_ROOM_ON, CONF_ROOM_OFF]:
                        self.ensurePresetInConfig(curArea, template_params[conf])
                        areaConfig[conf] = template_params[conf]
                elif template == CONF_TRIGGER:
                    areaConfig[CONF_NO_DEFAULT] = True
                    self.ensurePresetInConfig(curArea, template_params[CONF_TRIGGER], False, areaConfig[CONF_NAME])
                    areaConfig[CONF_TRIGGER] = template_params[CONF_TRIGGER]
                elif template == CONF_CHANNEL_COVER:
                    areaConfig[CONF_NO_DEFAULT] = True
                    curChannel = template_params[CONF_CHANNEL]
                    self.ensureChannelInConfig(curArea, curChannel, False, areaConfig[CONF_NAME])
                    areaConfig[CONF_CHANNEL][str(curChannel)][CONF_CHANNEL_TYPE] = "cover"
                    for conf in [CONF_CHANNEL_CLASS, CONF_FACTOR, CONF_TILT_PERCENTAGE]:
                        areaConfig[CONF_CHANNEL][str(curChannel)][conf] = template_params[conf]
                elif template == CONF_TIME_COVER:
                    areaConfig[CONF_NO_DEFAULT] = True
                    curChannel = template_params[CONF_CHANNEL_COVER]
                    if int(curChannel) > 0:
                        areaConfig[CONF_CHANNEL_COVER] = curChannel
                        self.ensureChannelInConfig(curArea, curChannel)
                    for conf in [CONF_OPEN_PRESET, CONF_CLOSE_PRESET, CONF_STOP_PRESET]:
                        self.ensurePresetInConfig(curArea, template_params[conf])
                        areaConfig[conf] = template_params[conf]
                    for conf in [CONF_CHANNEL_CLASS, CONF_DURATION, CONF_TILT_TIME]:
                        areaConfig[conf] = template_params[conf]
            # now register the channels and presets XXX presets TODO
            LOGGER.error("XXX area %s", curArea)
            if CONF_CHANNEL in areaConfig:
                for channel in areaConfig[CONF_CHANNEL]:
                    LOGGER.error("XXX channel %s", channel)
                    self.create_channel_if_new(int(curArea), int(channel))
        LOGGER.debug("bridge async_setup (after templates) - %s" % self.config)
        # register the rooms (switches on presets 1/4)
        self.registerRooms()
        # register the time covers
        self.registerTimeCovers()
        return True

    def ensurePresetInConfig(self, area, preset, hidden=True, name=None):
        areaConfig = self.config[CONF_AREA][area]
        if CONF_PRESET not in areaConfig:
            areaConfig[CONF_PRESET] = {}
        if str(preset) not in areaConfig[CONF_PRESET]:
            curConf = {CONF_HIDDEN_ENTITY: hidden}
            if name:
                curConf[CONF_NAME] = name
            areaConfig[CONF_PRESET][str(preset)] = curConf

    def ensureChannelInConfig(self, area, channel, hidden=True, name=None):
        areaConfig = self.config[CONF_AREA][area]
        if CONF_CHANNEL not in areaConfig:
            areaConfig[CONF_CHANNEL] = {}
        if str(channel) not in areaConfig[CONF_CHANNEL]:
            curConf = {CONF_HIDDEN_ENTITY: hidden}
            if name:
                curConf[CONF_NAME] = name
            areaConfig[CONF_CHANNEL][str(channel)] = curConf

    def registerRooms(self):
        """Register the room switches from two normal presets each."""
        for curArea, areaConfig in self.config[CONF_AREA].items():
            if CONF_TEMPLATE in areaConfig and areaConfig[CONF_TEMPLATE] == CONF_ROOM:
                if int(curArea) in self.added_room_switches:
                    continue
                newDevice = DynaliteDualPresetSwitchDevice(
                    curArea,
                    areaConfig[CONF_NAME],
                    areaConfig[CONF_NAME],
                    self.getMasterArea(curArea),
                    self,
                )
                self.added_room_switches[int(curArea)] = newDevice
                self.setPresetIfReady(curArea, areaConfig[CONF_ROOM_ON], 1, newDevice)
                self.setPresetIfReady(curArea, areaConfig[CONF_ROOM_OFF], 2, newDevice)
                self.registerNewDevice("switch", newDevice, False)

    def registerTimeCovers(self):
        """Register the time covers from three presets and a channel each."""
        for curArea, areaConfig in self.config[CONF_AREA].items():
            if CONF_TEMPLATE in areaConfig and areaConfig[CONF_TEMPLATE] == CONF_TIME_COVER:
                if int(curArea) in self.added_time_covers:
                    continue
                if areaConfig[CONF_TILT_TIME] == 0:
                    newDevice = DynaliteTimeCoverDevice(
                        curArea,
                        areaConfig[CONF_NAME],
                        areaConfig[CONF_NAME],
                        areaConfig[CONF_DURATION],
                        areaConfig[CONF_CHANNEL_CLASS],
                        self.getMasterArea(curArea),
                        self,
                    )
                else:
                    newDevice = DynaliteTimeCoverWithTiltDevice(
                        curArea,
                        areaConfig[CONF_NAME],
                        areaConfig[CONF_NAME],
                        areaConfig[CONF_DURATION],
                        areaConfig[CONF_CHANNEL_CLASS],
                        areaConfig[CONF_TILT_TIME],
                        self.getMasterArea(curArea),
                        self,
                    )
                self.added_time_covers[int(curArea)] = newDevice
                self.setPresetIfReady(curArea, areaConfig[CONF_OPEN_PRESET], 1, newDevice)
                self.setPresetIfReady(curArea, areaConfig[CONF_CLOSE_PRESET], 2, newDevice)
                self.setPresetIfReady(curArea, areaConfig[CONF_STOP_PRESET], 3, newDevice)
                if CONF_CHANNEL_COVER in areaConfig:
                    self.setChannelIfReady(curArea, areaConfig[CONF_CHANNEL_COVER], 4, newDevice)
                else:
                    # No channel attached, only presets.
                    dummyDevice = DynaliteBaseDevice(
                        curArea,
                        areaConfig[CONF_NAME],
                        areaConfig[CONF_NAME],
                        self.getMasterArea(curArea),
                        self,
                    )
                    newDevice.set_device(4, dummyDevice)
                self.registerNewDevice("cover", newDevice, False)

    def registerNewDevice(self, category, device, hidden):
        """Register a new device and group all the ones prior to CONFIGURED event together."""
        self.devices.append(device)
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

    def getTemplateIndex(self, area, template, conf):
        """Get a specific index from a specific template in an area."""
        # First check if explicitly defined in area
        try:
            return self.config[CONF_AREA][str(area)][conf]
        except KeyError:
            pass
        # get from templates - always defined either by the user or by the defaults
        try:
            return self.config[CONF_TEMPLATE][template]
        except KeyError:
            pass
        # not found
        return None

    def getTemplateParams(self, area):
        """Extract all the parameters of a template."""
        result = {}
        area_config = self.config[CONF_AREA][str(area)]
        template = area_config.get(CONF_TEMPLATE)
        if not template:
            return result
        for conf in self.config[CONF_TEMPLATE][template]:
            value = self.getTemplateIndex(area, template, conf)
            result[conf] = value
        return result

    def setPresetIfReady(self, area, preset, deviceNum, multiDevice):
        """Try to set a preset of a multi device if it was already registered."""
        try:
            device = self.added_presets[int(area)][int(preset)]
            multiDevice.set_device(deviceNum, device)
        except KeyError:
            pass

    def setChannelIfReady(self, area, channel, deviceNum, multiDevice):
        """Try to set a preset of a multi device if it was already registered."""
        try:
            device = self.added_channels[int(area)][int(channel)]
            multiDevice.set_device(deviceNum, device)
        except KeyError:
            pass

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
        elif event.eventType == EVENT_CONFIGURED: # XXX REMOVE
            assert False
            LOGGER.debug("received CONFIGURED message")
            self.configured = True
            if self.newDeviceFunc and self.waiting_devices:
                self.newDeviceFunc(self.waiting_devices)
                self.waiting_devices = []
        return

    def get_channel_name(self, area, channel):
        # XXX
        return "XXX Area " + str(area) + " Channel " + str(channel)

    def getMasterArea(self, area):
        """Get the master area when combining entities from different Dynet areas to the same area."""
        if str(area) not in self.config[CONF_AREA]:
            LOGGER.error("getMasterArea - we should not get here")
            raise BridgeError("getMasterArea - area " + str(area) + "is not in config")
        areaConfig = self.config[CONF_AREA][str(area)]
        masterArea = areaConfig[CONF_NAME]
        if CONF_AREA_OVERRIDE in areaConfig:
            overrideArea = areaConfig[CONF_AREA_OVERRIDE]
            masterArea = overrideArea if overrideArea.lower() != CONF_NONE else ""
        return masterArea

    def create_preset_if_new(self, area, preset):
        """Register a new preset."""
        LOGGER.debug("create_preset_if_new - area=%s preset=%s", area, preset)

        try:
            if self.added_presets[area][preset]:
                return
        except KeyError:
            pass

        if str(area) not in self.config[CONF_AREA]:
            LOGGER.debug("adding area " + str(area) + " that is not in config")
            self.config[CONF_AREA][str(area)] = {CONF_NAME: "Area " + str(area)}
        areaConfig = self.config[CONF_AREA][str(area)]

        try:
            # If the name is explicitly defined, use it
            presetName = areaConfig[CONF_PRESET][str(preset)][CONF_NAME]  
        except KeyError:
            presetName = "Preset " + str(preset)
            if CONF_NO_DEFAULT not in areaConfig or not areaConfig[CONF_NO_DEFAULT]:
                try:
                    presetName = self.config[CONF_PRESET][str(preset)][CONF_NAME]
                except KeyError:
                    pass
        curName = areaConfig[CONF_NAME] + " " + presetName  
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

        self.registerNewDevice("switch", newDevice, hidden)
        newDevice.set_level(0) # XXX 
        if area not in self.added_presets:
            self.added_presets[area] = {}
        self.added_presets[area][preset] = newDevice
        LOGGER.debug(
            "Creating Dynalite preset area=%s preset=%s name=%s hidden=%s", area, preset, curName, hidden
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

        if str(area) not in self.config[CONF_AREA]:
            LOGGER.debug("adding area " + str(area) + " that is not in config")
            self.config[CONF_AREA][str(area)] = {CONF_NAME: "Area " + str(area)}
        areaConfig = self.config[CONF_AREA][str(area)]

        try:
            # If the name is explicitly defined, use it
            channelName = areaConfig[CONF_CHANNEL][str(channel)][CONF_NAME]  
        except (KeyError, TypeError):
            # If not explicitly defined, use "areaname Channel X"
            channelName = "Channel " + str(channel)
        curName = areaConfig[CONF_NAME] + " " + channelName
        try:
            channelConfig = areaConfig[CONF_CHANNEL][str(channel)]
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
                 (self.config[CONF_AREA][str(area)].get(CONF_TEMPLATE) == CONF_HIDDEN_ENTITY)
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
        LOGGER.debug("Creating Dynalite channel area=%s channel=%s name=%s", area, channel, curName)
        # if it is a channel from a timecover, register it
        try:
            template = areaConfig[CONF_TEMPLATE]  
            if template == CONF_TIME_COVER:
                # in a template room, the channels will all be in the time cover
                hidden = True  
                # if it is not there yet, it will be added when the time cover will be created
                if int(area) in self.added_time_covers:  
                    multiDevice = self.added_time_covers[int(area)]
                    if int(channel) == int(areaConfig[CONF_CHANNEL_COVER]):
                        multiDevice.set_device(4, newDevice)
        except KeyError:
            pass

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
        