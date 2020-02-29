"""
Manage a Dynalite connection.

@ Author      : Troy Kelly
@ Date        : 3 Dec 2018
@ Description : Philips Dynalite Library - Unofficial interface for Philips Dynalite over RS485

@ Notes:        Requires a RS485 to IP gateway (Do not use the Dynalite one - use something cheaper)
"""

import asyncio
import time

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
    LOGGER,
)
from .dynet import DynetPacket, PacketError
from .event import DynetEvent
from .inbound import DynetInbound
from .opcodes import SyncType


class Dynalite(object):
    """Class to represent the interaction with Dynalite."""

    def __init__(self, broadcast_func):
        """Initialize the class."""
        self.host = None
        self.port = None
        self.loop = None
        self.broadcast_func = broadcast_func
        self._inBuffer = []
        self._outBuffer = []
        self._lastSent = None
        self._messageDelay = 200
        self._sending = False
        self._reader = None
        self._writer = None
        self.resetting = False

    async def connect_internal(self):
        """Create the actual connection to Dynet."""
        try:
            self._reader, self._writer = await asyncio.open_connection(
                self.host, self.port
            )
            return True
        except (ValueError, OSError, asyncio.TimeoutError) as err:
            LOGGER.warning("Could not connect to Dynet (%s)", err)
            return False

    async def connect(self, host, port):
        """Connect to Dynet."""
        self.host = host
        self.port = port
        LOGGER.debug("Connecting to Dynet on %s:%s", host, port)
        if not self.loop:
            self.loop = asyncio.get_running_loop()
        self.resetting = False
        result = await self.connect_internal()
        if result and not self.resetting:
            self.loop.create_task(self.reader_loop())
        return result

    async def reader_loop(self):
        """Loop to read from the stream reader and reconnect if necessary."""
        while True:
            self.write()  # write if there is something in the buffers
            try:
                data = await self._reader.read(100)
                if len(data) > 0:
                    self.receive(data)
                    continue
            except ConnectionResetError:
                pass
            # we got disconnected or EOF
            if self.resetting:
                self._reader = None
                return  # stop loop
            self._reader = None
            self._writer = None
            self.broadcast(DynetEvent(eventType=EVENT_DISCONNECTED, data={}))
            await asyncio.sleep(1)  # Don't overload the network
            while not await self.connect_internal():
                if self.resetting:
                    self._reader = None
                    return  # stop loop
                await asyncio.sleep(1)  # Don't overload the network
            self.broadcast(DynetEvent(eventType=EVENT_CONNECTED, data={}))

    def broadcast(self, event):
        """Broadcast an event to all listeners - queue."""
        self.loop.call_soon(self.broadcast_func, event)

    def set_channel_level(self, area, channel, level, fade):
        """Set the level of a channel."""
        packet = DynetPacket.set_channel_level_packet(area, channel, level, fade)
        self.write(packet)
        broadcastData = {
            CONF_AREA: area,
            CONF_CHANNEL: channel,
            CONF_TRGT_LEVEL: int(255 - 254.0 * level),
            CONF_ACTION: CONF_ACTION_CMD,
        }
        self.broadcast(DynetEvent(eventType=EVENT_CHANNEL, data=broadcastData))

    def select_preset(self, area, preset, fade):
        """Select a preset in an area."""
        packet = DynetPacket.select_area_preset_packet(area, preset, fade)
        self.write(packet)
        broadcastData = {
            CONF_AREA: area,
            CONF_PRESET: preset,
        }
        self.broadcast(DynetEvent(eventType=EVENT_PRESET, data=broadcastData))

    def request_channel_level(self, area, channel):
        """Request a level for a specific channel."""
        packet = DynetPacket.request_channel_level_packet(area, channel)
        self.write(packet)

    def stop_channel_fade(self, area, channel):
        """Stop fading of a channel - async."""
        packet = DynetPacket.stop_channel_fade_packet(area, channel)
        self.write(packet)

    def request_area_preset(self, area):
        """Request current preset of an area."""
        packet = DynetPacket.request_area_preset_packet(area)
        self.write(packet)

    def receive(self, data=None):
        """Handle data that was received."""
        if data is not None:
            for byte in data:
                self._inBuffer.append(int(byte))
        if len(self._inBuffer) < 8:
            LOGGER.debug(
                "Received %d bytes, not enough to process: %s"
                % (len(self._inBuffer), self._inBuffer)
            )
        packet = None
        while len(self._inBuffer) >= 8 and packet is None:
            firstByte = self._inBuffer[0]
            if SyncType.has_value(firstByte):
                if firstByte == SyncType.DEBUG_MSG.value:
                    bytemsg = "".join(chr(c) for c in self._inBuffer[1:7])
                    LOGGER.debug("Dynet DEBUG message %s" % bytemsg)
                    self._inBuffer = self._inBuffer[8:]
                    continue
                elif firstByte == SyncType.DEVICE.value:
                    LOGGER.debug(
                        "Not handling Dynet DEVICE message %s" % self._inBuffer[:8]
                    )
                    self._inBuffer = self._inBuffer[8:]
                    continue
                elif firstByte == SyncType.LOGICAL.value:
                    try:
                        packet = DynetPacket(msg=self._inBuffer[:8])
                    except PacketError as err:
                        LOGGER.warning(err)
                        packet = None
            if packet is None:
                hexString = ":".join("{:02x}".format(c) for c in self._inBuffer[:8])
                LOGGER.debug(
                    "Unable to process packet %s - moving one byte forward" % hexString
                )
                del self._inBuffer[0]
                continue
            else:
                self._inBuffer = self._inBuffer[8:]
            LOGGER.debug("Have packet: %s" % packet)
            if hasattr(packet, "opcodeType") and packet.opcodeType is not None:
                inboundHandler = DynetInbound()
                if hasattr(inboundHandler, packet.opcodeType.lower()):
                    event = getattr(inboundHandler, packet.opcodeType.lower())(packet)
                    if event:
                        self.broadcast(event)
                else:
                    LOGGER.debug(
                        "Unhandled Dynet Inbound (%s): %s" % (packet.opcodeType, packet)
                    )
            else:
                LOGGER.debug("Unhandled Dynet Inbound: %s" % packet)
        # If there is still buffer to process - start again
        if len(self._inBuffer) >= 8:
            self.loop.call_soon(self.receive)

    def write(self, newPacket=None):
        """Write a packet or trigger write loop."""
        if newPacket is not None:
            self._outBuffer.append(newPacket)
        if self._writer is None:
            LOGGER.debug("write before transport is ready. queuing")
            return
        if self._sending:
            LOGGER.debug("Connection busy - queuing packet")
            self.loop.call_later(1, self.write)
            return
        if self._lastSent is None:
            self._lastSent = int(round(time.time() * 1000))
        current_milli_time = int(round(time.time() * 1000))
        elapsed = current_milli_time - self._lastSent
        delay = 0 - (elapsed - self._messageDelay)
        if delay > 0:
            self.loop.call_later(delay / 1000, self.write)
            return
        if len(self._outBuffer) == 0:
            return
        packet = self._outBuffer[0]
        self._sending = True
        msg = bytearray()
        msg.append(packet.sync)
        msg.append(packet.area)
        msg.append(packet.data[0])
        msg.append(packet.command)
        msg.append(packet.data[1])
        msg.append(packet.data[2])
        msg.append(packet.join)
        msg.append(packet.chk)
        self._writer.write(msg)
        LOGGER.debug("Dynet Sent: %s" % msg)
        self._lastSent = int(round(time.time() * 1000))
        self._sending = False
        del self._outBuffer[0]
        if len(self._outBuffer) > 0:
            self.loop.call_later(self._messageDelay / 1000, self.write)

    async def async_reset(self):
        """Close sockets and timers."""
        self.resetting = True
        # Wait for reader to also close
        while self._reader:
            if self._writer:
                temp_writer = self._writer
                self._writer = None
                temp_writer.close()
                await temp_writer.wait_closed()
            await asyncio.sleep(1)
