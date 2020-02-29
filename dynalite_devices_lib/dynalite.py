"""
Manage a Dynalite connection.

@ Author      : Troy Kelly
@ Date        : 3 Dec 2018
@ Description : Philips Dynalite Library - Unofficial interface for Philips Dynalite over RS485

@ Notes:        Requires a RS485 to IP gateway (Do not use the Dynalite one - use something cheaper)
"""

import asyncio

from .const import (
    CONF_ACTION,
    CONF_ACTION_CMD,
    CONF_AREA,
    CONF_CHANNEL,
    CONF_PRESET,
    CONF_TRGT_LEVEL,
    EVENT_CHANNEL,
    EVENT_CONNECTED,
    EVENT_DISCONNECTED,
    EVENT_PRESET,
)
from .dynet import Dynet, DynetControl
from .event import DynetEvent


class Dynalite(object):
    """Class to represent the interaction with Dynalite."""

    def __init__(self, port, host, active, poll_timer, broadcast_func, loop=None):
        """Initialize the class."""
        self.host = host
        self.port = port
        self.active = active
        self.poll_timer = poll_timer
        self.loop = loop if loop else asyncio.get_event_loop()
        self._dynet = None
        self.control = None
        self.broadcast_func = broadcast_func

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
            broadcaster=self.broadcast,
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

    def broadcast(self, event):
        """Broadcast an event to all listeners - queue."""
        self.loop.call_soon(self.broadcast_func, event)

    def set_channel_level(self, area, channel, level, fade):
        """Set the level of a channel."""
        self.control.set_channel_level(
            area=area, channel=channel, level=level, fade=fade,
        )
        broadcastData = {
            CONF_AREA: area,
            CONF_CHANNEL: channel,
            CONF_TRGT_LEVEL: int(255 - 254.0 * level),
            CONF_ACTION: CONF_ACTION_CMD,
        }
        self.broadcast(DynetEvent(eventType=EVENT_CHANNEL, data=broadcastData))

    def select_preset(self, area, preset, fade):
        """Select a preset in an area."""
        self.control.set_area_preset(area=area, preset=preset, fade=fade)
        broadcastData = {
            CONF_AREA: area,
            CONF_PRESET: preset,
        }
        self.broadcast(DynetEvent(eventType=EVENT_PRESET, data=broadcastData))
