"""
@ Author      : Troy Kelly
@ Date        : 3 Dec 2018
@ Description : Philips Dynalite Library - Unofficial interface for Philips Dynalite over RS485

@ Notes:        Requires a RS485 to IP gateway (Do not use the Dynalite one - use something cheaper)
"""

import asyncio
import logging
from .dynet import Dynet, DynetControl
from .event import DynetEvent

from .const import (
    CONF_HOST,
    CONF_PORT,
    CONF_DEFAULT,
    CONF_AREA,
    CONF_NAME,
    CONF_FADE,
    CONF_LEVEL,
    CONF_PRESET,
    CONF_AUTO_DISCOVER,
    CONF_POLL_TIMER,
    CONF_CHANNEL,
    CONF_NO_DEFAULT,
    CONF_ACTION,
    CONF_ACTION_REPORT,
    CONF_ACTION_CMD,
    CONF_TRGT_LEVEL,
    CONF_ACT_LEVEL,
    CONF_ALL,
    EVENT_CONNECTED,
    EVENT_DISCONNECTED,
    EVENT_CONFIGURED,
    EVENT_NEWPRESET,
    EVENT_NEWCHANNEL,
    EVENT_PRESET,
    EVENT_CHANNEL,
    STARTUP_RETRY_DELAY,
    INITIAL_RETRY_DELAY,
    MAXIMUM_RETRY_DELAY,
    NO_RETRY_DELAY_VALUE,
    CONF_ACTIVE,
    CONF_ACTIVE_ON,
    CONF_ACTIVE_INIT,
    LOGGER,
    DEFAULT_PORT,
    CONF_ACTIVE_OFF,
)


class Broadcaster(object):
    """Class to broadcast event to listeners."""

    def __init__(self, listenerFunction=None, loop=None):
        """Initialize the broadcaster."""
        if listenerFunction is None:
            raise BroadcasterError("A broadcaster bust have a listener Function")
        self._listenerFunction = listenerFunction
        self._monitoredEvents = []
        self._loop = loop

    def monitorEvent(self, eventType=None):
        """Set broadcaster to monitor an event or all."""
        if eventType is None:
            raise BroadcasterError("Must supply an event type to monitor")
        eventType = eventType.upper()
        if eventType not in self._monitoredEvents:
            self._monitoredEvents.append(eventType.upper())

    def unmonitorEvent(self, eventType=None):
        """Stop monitoring an event."""
        if eventType is None:
            raise BroadcasterError("Must supply an event type to un-monitor")
        eventType = eventType.upper()
        if eventType in self._monitoredEvents:
            self._monitoredEvents.remove(eventType.upper())

    def update(self, event=None, dynalite=None):
        """Update listener with an event if relevant."""
        if event is None:
            return
        if (
            event.eventType not in self._monitoredEvents
            and "*" not in self._monitoredEvents
        ):
            return
        if self._loop:
            self._loop.create_task(self._callUpdater(event=event, dynalite=dynalite))
        else:
            self._listenerFunction(event=event, dynalite=dynalite)

    @asyncio.coroutine
    def _callUpdater(self, event=None, dynalite=None):
        """Call listener callback function."""
        self._listenerFunction(event=event, dynalite=dynalite)

class Dynalite(object):
    """Class to represent the interaction with Dynalite."""

    def __init__(self, port, host, active, poll_timer, loop=None):
        """Initialize the class."""
        self.host = host
        self.port = port
        self.active = active
        self.poll_timer = poll_timer
        self.loop = loop if loop else asyncio.get_event_loop()
        self._listeners = []
        self._dynet = None
        self.control = None

    def start(self):
        """Queue request to start the class."""
        self.loop.create_task(self._start())

    async def _start(self):
        """Start the class."""
        self._dynet = Dynet(
            host=self.host,
            port=self.port,
            active=self.active,
            loop=self.loop,
            broadcaster=self.processTraffic,
            onConnect=self._connected,
            onDisconnect=self._disconnection,
        )
        self.control = DynetControl(self._dynet, self.loop, self.active)
        self.connect()  

    def connect(self):
        """Queue command to connect to Dynet."""
        self.loop.create_task(self._connect())

    async def _connect(self):
        """Connect to Dynet."""
        await self._dynet.async_connect()

    @asyncio.coroutine
    def _connected(self, dynet=None, transport=None):
        """Handle a successful connection."""
        self.broadcast(DynetEvent(eventType=EVENT_CONNECTED, data={}))

    @asyncio.coroutine
    def _disconnection(self, dynet=None):
        """Handle a disconnection and try to reconnect."""
        self.broadcast(DynetEvent(eventType=EVENT_DISCONNECTED, data={}))
        yield from asyncio.sleep(1)  # Don't overload the network
        self.connect()

    def processTraffic(self, event):
        """Process an event that arrived from Dynet - queue."""
        self.loop.create_task(self._processTraffic(event))

    @asyncio.coroutine
    def _processTraffic(self, event):
        """Process an event that arrived from Dynet - async."""
        # The logic here is:
        # - new area is created - ask for the current preset
        # - preset selected - turn the preset on but don't send it as a command
        # - new channel is created - ask for the current level
        # - channel update - update the level and if it is fading (actual != target), schedule a timer to ask again
        # - channel set command - request current level (may not be the target because of fade)

        # First handle, and then broadcast so broadcast receivers have updated device levels and presets
        self.broadcast(event)

    def broadcast(self, event):
        """Broadcast an event to all listeners - queue."""
        self.loop.create_task(self._broadcast(event))

    @asyncio.coroutine
    def _broadcast(self, event):
        """Broadcast an event to all listeners - async."""
        for listenerFunction in self._listeners:
            listenerFunction.update(event=event, dynalite=self)

    def addListener(self, listenerFunction=None):
        """Create a new listener to the class."""
        broadcaster = Broadcaster(listenerFunction=listenerFunction, loop=self.loop)
        self._listeners.append(broadcaster)
        return broadcaster

    def set_channel_level(self, area, channel, level):
        self.control.set_channel_level(
            area=int(area),
            channel=int(channel),
            level=level,
            fade=0, # XXX add fade
        )
        broadcastData = {
            CONF_AREA: int(area),
            CONF_CHANNEL: int(channel),
            CONF_TRGT_LEVEL: 255 - 254.0 * level,
            CONF_ACTION: CONF_ACTION_CMD,
        }
        self.processTraffic(DynetEvent(eventType=EVENT_CHANNEL, data=broadcastData))

    def select_preset(self, area, preset):
        # XXX add fade
        if not self.control:
            return
        self.control.areaPreset(
            area=self.area.value, preset=self.value, fade=0
        )