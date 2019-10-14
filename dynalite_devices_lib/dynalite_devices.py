"""Class to create devices from a Dynalite hub."""

import copy

from .const import (
    LOGGER,
    CONF_TEMPLATEOVERRIDE,
    DEFAULT_COVERCHANNELCLASS,
    DEFAULT_COVERFACTOR,
    CONF_TRIGGER,
    CONF_FACTOR,
    CONF_CHANNELTYPE,
    CONF_HIDDENENTITY,
    CONF_TILTPERCENTAGE,
    CONF_AREAOVERRIDE,
    CONF_CHANNELCLASS,
    CONF_TEMPLATE,
    CONF_ROOM_ON,
    CONF_ROOM_OFF,
    DEFAULT_TEMPLATES,
    CONF_ROOM,
    DEFAULT_CHANNELTYPE,
    CONF_CHANNELCOVER,
    CONF_NONE,
)
from dynalite_lib import (
    CONF_CHANNEL,
    CONF_AREA,
    CONF_NAME,
    CONF_PRESET,
    CONF_NODEFAULT,
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
    Dynalite,
)

from .light import DynaliteChannelLightDevice
from .switch import (
    DynaliteChannelSwitchDevice,
    DynalitePresetSwitchDevice,
    DynaliteDualPresetSwitchDevice,
)
from .cover import DynaliteChannelCoverDevice, DynaliteChannelCoverWithTiltDevice


class BridgeError(Exception):
    """For errors in the Dynalite bridge."""

    def __init__(self, message):
        """Initialize the exception."""
        self.message = message


class DynaliteDevices:
    """Manages a single Dynalite bridge."""

    def __init__(self, config, loop, newDeviceFunc=None, updateDeviceFunc=None):
        """Initialize the system."""
        self.config = copy.deepcopy(config)
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

    async def async_setup(self, tries=0):
        """Set up a Dynalite bridge based on host parameter in the config."""
        LOGGER.debug("bridge async_setup - %s", self.config)

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
                if template == CONF_ROOM:
                    areaConfig[CONF_NODEFAULT] = True
                    if CONF_PRESET not in areaConfig:
                        areaConfig[CONF_PRESET] = {}
                    roomOn = self.getTemplateIndex(
                        int(curArea), CONF_ROOM, CONF_ROOM_ON
                    )
                    if str(roomOn) not in areaConfig[CONF_PRESET]:
                        areaConfig[CONF_PRESET][str(roomOn)] = {CONF_HIDDENENTITY: True}
                    roomOff = self.getTemplateIndex(
                        int(curArea), CONF_ROOM, CONF_ROOM_OFF
                    )
                    if str(roomOff) not in areaConfig[CONF_PRESET]:
                        areaConfig[CONF_PRESET][str(roomOff)] = {
                            CONF_HIDDENENTITY: True
                        }
                elif template == CONF_TRIGGER:
                    if CONF_PRESET not in areaConfig:
                        areaConfig[CONF_PRESET] = {}
                    areaConfig[CONF_NODEFAULT] = True
                    trigger = self.getTemplateIndex(
                        int(curArea), CONF_TRIGGER, CONF_TRIGGER
                    )
                    if str(trigger) not in areaConfig[CONF_PRESET]:
                        areaConfig[CONF_PRESET][str(trigger)] = {
                            CONF_HIDDENENTITY: False,
                            CONF_NAME: areaConfig[CONF_NAME],
                        }
                elif template == CONF_CHANNELCOVER:
                    areaConfig[CONF_NODEFAULT] = True
                    curChannel = self.getTemplateIndex(
                        int(curArea), CONF_CHANNELCOVER, CONF_CHANNEL
                    )
                    if CONF_CHANNEL not in areaConfig:
                        areaConfig[CONF_CHANNEL] = {}
                    if str(curChannel) not in areaConfig[CONF_CHANNEL]:
                        areaConfig[CONF_CHANNEL][str(curChannel)] = {
                            CONF_NAME: areaConfig[CONF_NAME],
                            CONF_CHANNELTYPE: "cover",
                            CONF_HIDDENENTITY: False,
                        }
                    if self.getTemplateIndex(
                        curArea, CONF_CHANNELCOVER, CONF_CHANNELCLASS
                    ):
                        areaConfig[CONF_CHANNEL][str(curChannel)][
                            CONF_CHANNELCLASS
                        ] = self.getTemplateIndex(
                            curArea, CONF_CHANNELCOVER, CONF_CHANNELCLASS
                        )
                    if self.getTemplateIndex(curArea, CONF_CHANNELCOVER, CONF_FACTOR):
                        areaConfig[CONF_CHANNEL][str(curChannel)][
                            CONF_FACTOR
                        ] = self.getTemplateIndex(
                            curArea, CONF_CHANNELCOVER, CONF_FACTOR
                        )
                    if self.getTemplateIndex(
                        curArea, CONF_CHANNELCOVER, CONF_TILTPERCENTAGE
                    ):
                        areaConfig[CONF_CHANNEL][str(curChannel)][
                            CONF_TILTPERCENTAGE
                        ] = self.getTemplateIndex(
                            curArea, CONF_CHANNELCOVER, CONF_TILTPERCENTAGE
                        )
        LOGGER.debug("bridge async_setup (after templates) - %s" % self.config)

        # Configure the dynalite object
        self._dynalite = Dynalite(config=self.config, loop=self.loop)
        eventHandler = self._dynalite.addListener(listenerFunction=self.handleEvent)
        eventHandler.monitorEvent("*")
        newPresetHandler = self._dynalite.addListener(
            listenerFunction=self.handleNewPreset
        )
        newPresetHandler.monitorEvent(EVENT_NEWPRESET)
        presetChangeHandler = self._dynalite.addListener(
            listenerFunction=self.handlePresetChange
        )
        presetChangeHandler.monitorEvent(EVENT_PRESET)
        newChannelHandler = self._dynalite.addListener(
            listenerFunction=self.handleNewChannel
        )
        newChannelHandler.monitorEvent(EVENT_NEWCHANNEL)
        channelChangeHandler = self._dynalite.addListener(
            listenerFunction=self.handleChannelChange
        )
        channelChangeHandler.monitorEvent(EVENT_CHANNEL)
        self._dynalite.start()

        # register the rooms (switches on presets 1/4)
        self.registerRooms()

        return True

    def registerRooms(self):
        """Register the room switches from two normal presets each."""
        for curArea in self.config[CONF_AREA]:
            if (
                CONF_TEMPLATE in self.config[CONF_AREA][curArea]
                and self.config[CONF_AREA][curArea][CONF_TEMPLATE] == CONF_ROOM
            ):
                newDevice = DynaliteDualPresetSwitchDevice(
                    curArea,
                    self.config[CONF_AREA][curArea][CONF_NAME],
                    self.config[CONF_AREA][curArea][CONF_NAME],
                    self.getMasterArea(curArea),
                    self,
                )
                self.added_room_switches[int(curArea)] = newDevice
                self.setPresetIfReady(curArea, CONF_ROOM, CONF_ROOM_ON, 1, newDevice)
                self.setPresetIfReady(curArea, CONF_ROOM, CONF_ROOM_OFF, 2, newDevice)
                self.registerNewDevice("switch", newDevice)

    def registerNewDevice(self, category, device):
        """Register a new device and group all the ones prior to CONFIGURED event together."""
        self.devices.append(device)
        if (
            self.configured
        ):  # after initial configuration, every new device gets sent on its own. The initial ones are bunched together
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
        my_template = self.config[CONF_TEMPLATE][
            template
        ]  # always defined either by the user or by the defaults
        index = None
        if conf in my_template:
            index = my_template[conf]
        try:
            index = self.config[CONF_AREA][str(area)][CONF_TEMPLATEOVERRIDE][conf]
        except KeyError:
            pass
        return index

    def setPresetIfReady(self, area, template, conf, deviceNum, dualDevice):
        """Try to set a preset of a dual device if it was already registered."""
        preset = self.getTemplateIndex(area, template, conf)
        if not preset:
            return
        try:
            device = self.added_presets[int(area)][int(preset)]
            dualDevice.set_device(deviceNum, device)
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
        elif event.eventType == EVENT_CONFIGURED:
            LOGGER.debug("received CONFIGURED message")
            self.configured = True
            if self.newDeviceFunc and self.waiting_devices:
                self.newDeviceFunc(self.waiting_devices)
                self.waiting_devices = []
        return

    def getMasterArea(self, area):
        """Get the master area when combining entities from different Dynet areas to the same area."""
        if str(area) not in self.config[CONF_AREA]:
            LOGGER.error("getMasterArea - we should not get here")
            raise BridgeError("getMasterArea - area " + str(area) + "is not in config")
        areaConfig = self.config[CONF_AREA][str(area)]
        masterArea = areaConfig[CONF_NAME]
        if CONF_AREAOVERRIDE in areaConfig:
            overrideArea = areaConfig[CONF_AREAOVERRIDE]
            masterArea = overrideArea if overrideArea.lower() != CONF_NONE else ""
        return masterArea

    def handleNewPreset(self, event=None, dynalite=None):
        """Register a new preset."""
        LOGGER.debug("handleNewPreset - event=%s", event.data)
        if not hasattr(event, "data"):
            return
        if CONF_AREA not in event.data:
            return
        curArea = event.data[CONF_AREA]
        if CONF_PRESET not in event.data:
            return
        curPreset = event.data[CONF_PRESET]

        if str(curArea) not in self.config[CONF_AREA]:
            LOGGER.debug("adding area " + str(curArea) + " that is not in config")
            self.config[CONF_AREA][str(curArea)] = {CONF_NAME: "Area " + str(curArea)}

        try:
            curName = self.config[CONF_AREA][str(curArea)][CONF_PRESET][str(curPreset)][
                CONF_NAME
            ]  # If the name is explicitly defined, use it
        except KeyError:
            presetName = "Preset " + str(curPreset)
            if (
                CONF_NODEFAULT not in self.config[CONF_AREA][str(curArea)]
                or not self.config[CONF_AREA][str(curArea)][CONF_NODEFAULT]
            ):
                try:
                    presetName = self.config[CONF_PRESET][str(curPreset)][
                        CONF_NAME
                    ]  # XXX need to check for nodefault flag
                except KeyError:
                    pass
            curName = (
                self.config[CONF_AREA][str(curArea)][CONF_NAME] + " " + presetName
            )  # If not explicitly defined, use "areaname presetname"
        curDevice = self._dynalite.devices[CONF_AREA][curArea].preset[curPreset]
        newDevice = DynalitePresetSwitchDevice(
            curArea,
            self.config[CONF_AREA][str(curArea)][CONF_NAME],
            curPreset,
            curName,
            self.getMasterArea(curArea),
            self,
            curDevice,
        )
        self.registerNewDevice("switch", newDevice)
        if curArea not in self.added_presets:
            self.added_presets[curArea] = {}
        self.added_presets[curArea][curPreset] = newDevice

        try:
            hidden = self.config[CONF_AREA][str(curArea)][CONF_PRESET][str(curPreset)][
                CONF_HIDDENENTITY
            ]
        except KeyError:
            hidden = False

        try:
            template = self.config[CONF_AREA][str(curArea)][
                CONF_TEMPLATE
            ]  # templates may make some elements hidden
            if template == CONF_ROOM:
                hidden = (
                    True
                )  # in a template room, the presets will all be in the room switch
                if (
                    int(curArea) in self.added_room_switches
                ):  # if it is not there yet, it will be added when the room switch will be created
                    roomSwitch = self.added_room_switches[int(curArea)]
                    if int(curPreset) == int(
                        self.getTemplateIndex(curArea, CONF_ROOM, CONF_ROOM_ON)
                    ):
                        roomSwitch.set_device(1, newDevice)
                    if int(curPreset) == int(
                        self.getTemplateIndex(curArea, CONF_ROOM, CONF_ROOM_OFF)
                    ):
                        roomSwitch.set_device(2, newDevice)
            elif template == CONF_TRIGGER:
                triggerPreset = self.getTemplateIndex(curArea, template, CONF_TRIGGER)
                if int(curPreset) != int(triggerPreset):
                    hidden = True
            elif template in [CONF_HIDDENENTITY, CONF_CHANNELCOVER]:
                hidden = True
            else:
                LOGGER.error(
                    "Unknown template "
                    + template
                    + ". Should have been caught in config_validation"
                )
        except KeyError:
            pass

        if hidden:
            newDevice.set_hidden(True)
        LOGGER.debug(
            "Creating Dynalite preset area=%s preset=%s name=%s"
            % (curArea, curPreset, curName)
        )

    def handlePresetChange(self, event=None, dynalite=None):
        """Change the selected preset."""
        LOGGER.debug("handlePresetChange - event=%s" % event.data)
        if not hasattr(event, "data"):
            return
        if CONF_AREA not in event.data:
            return
        curArea = event.data[CONF_AREA]
        if CONF_PRESET not in event.data:
            return

        # Update all the preset devices
        if int(curArea) in self.added_presets:
            for curPresetInArea in self.added_presets[int(curArea)]:
                self.updateDevice(self.added_presets[int(curArea)][curPresetInArea])

    def handleNewChannel(self, event=None, dynalite=None):
        """Register a new channel."""
        LOGGER.debug("handleNewChannel - event=%s" % event.data)
        if not hasattr(event, "data"):
            return
        if CONF_AREA not in event.data:
            return
        curArea = event.data[CONF_AREA]
        if CONF_CHANNEL not in event.data:
            return
        curChannel = event.data[CONF_CHANNEL]

        if str(curArea) not in self.config[CONF_AREA]:
            LOGGER.debug("adding area " + str(curArea) + " that is not in config")
            self.config[CONF_AREA][str(curArea)] = {CONF_NAME: "Area " + str(curArea)}

        try:
            curName = self.config[CONF_AREA][str(curArea)][CONF_CHANNEL][
                str(curChannel)
            ][
                CONF_NAME
            ]  # If the name is explicitly defined, use it
        except (KeyError, TypeError):
            curName = (
                self.config[CONF_AREA][str(curArea)][CONF_NAME]
                + " Channel "
                + str(curChannel)
            )  # If not explicitly defined, use "areaname Channel X"
        curDevice = self._dynalite.devices[CONF_AREA][curArea].channel[curChannel]
        try:
            channelConfig = self.config[CONF_AREA][str(curArea)][CONF_CHANNEL][
                str(curChannel)
            ]
        except KeyError:
            channelConfig = None
        LOGGER.debug("handleNewChannel - channelConfig=%s" % channelConfig)
        channelType = (
            channelConfig[CONF_CHANNELTYPE].lower()
            if channelConfig and CONF_CHANNELTYPE in channelConfig
            else DEFAULT_CHANNELTYPE
        )
        hassArea = self.getMasterArea(curArea)
        if channelType == "light":
            newDevice = DynaliteChannelLightDevice(
                curArea,
                self.config[CONF_AREA][str(curArea)][CONF_NAME],
                curChannel,
                curName,
                channelType,
                hassArea,
                self,
                curDevice,
            )
            self.registerNewDevice("light", newDevice)
        elif channelType == "switch":
            newDevice = DynaliteChannelSwitchDevice(
                curArea,
                self.config[CONF_AREA][str(curArea)][CONF_NAME],
                curChannel,
                curName,
                channelType,
                hassArea,
                self,
                curDevice,
            )
            self.registerNewDevice("switch", newDevice)
        elif channelType == "cover":
            factor = (
                channelConfig[CONF_FACTOR]
                if CONF_FACTOR in channelConfig
                else DEFAULT_COVERFACTOR
            )
            deviceClass = (
                channelConfig[CONF_CHANNELCLASS]
                if CONF_CHANNELCLASS in channelConfig
                else DEFAULT_COVERCHANNELCLASS
            )
            if CONF_TILTPERCENTAGE in channelConfig:
                newDevice = DynaliteChannelCoverWithTiltDevice(
                    curArea,
                    self.config[CONF_AREA][str(curArea)][CONF_NAME],
                    curChannel,
                    curName,
                    channelType,
                    deviceClass,
                    factor,
                    channelConfig[CONF_TILTPERCENTAGE],
                    hassArea,
                    self,
                    curDevice,
                )
            else:
                newDevice = DynaliteChannelCoverDevice(
                    curArea,
                    self.config[CONF_AREA][str(curArea)][CONF_NAME],
                    curChannel,
                    curName,
                    channelType,
                    deviceClass,
                    factor,
                    hassArea,
                    self,
                    curDevice,
                )
            self.registerNewDevice("cover", newDevice)
        else:
            LOGGER.info("unknown chnanel type %s - ignoring", channelType)
            return
        if curArea not in self.added_channels:
            self.added_channels[curArea] = {}
        self.added_channels[curArea][curChannel] = newDevice
        if channelConfig and channelConfig[CONF_HIDDENENTITY]:
            newDevice.set_hidden(True)
        if self.config[CONF_AREA][str(curArea)].get(CONF_TEMPLATE) == CONF_HIDDENENTITY:
            newDevice.set_hidden(True)
        LOGGER.debug(
            "Creating Dynalite channel area=%s channel=%s name=%s"
            % (curArea, curChannel, curName)
        )

    def handleChannelChange(self, event=None, dynalite=None):
        """Change the level of a channel."""
        LOGGER.debug("handleChannelChange - event=%s" % event.data)
        LOGGER.debug("handleChannelChange called event = %s" % event.msg)
        if not hasattr(event, "data"):
            return
        if CONF_AREA not in event.data:
            return
        curArea = event.data[CONF_AREA]
        if CONF_CHANNEL not in event.data:
            return
        curChannel = event.data[CONF_CHANNEL]
        if CONF_TRGT_LEVEL not in event.data:
            return

        action = event.data[CONF_ACTION]
        if action == CONF_ACTION_REPORT:
            actual_level = (255 - event.data[CONF_ACT_LEVEL]) / 254
            target_level = (255 - event.data[CONF_TRGT_LEVEL]) / 254
        elif action == CONF_ACTION_CMD:
            target_level = (255 - event.data[CONF_TRGT_LEVEL]) / 254
            actual_level = (
                target_level
            )  # when there is only a "set channel level" command, assume that this is both the actual and the target
        else:
            LOGGER.error("unknown action for channel change %s", action)
            return
        try:
            channelToSet = self.added_channels[int(curArea)][int(curChannel)]
            channelToSet.update_level(actual_level, target_level)
            self.updateDevice(
                channelToSet
            )  # to only call if it was already added to ha
        except KeyError:
            pass
