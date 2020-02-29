"""
Library to handle Dynet networks.

@ Author      : Troy Kelly
@ Date        : 23 Sept 2018
@ Description : Philips Dynalite Library - Unofficial interface for Philips Dynalite over RS485

@ Notes:        Requires a RS485 to IP gateway (Do not use the Dynalite one - use something cheaper)
"""

import asyncio
import json

from .const import LOGGER
from .opcodes import OpcodeType, SyncType


class DynetError(Exception):
    """Class for Dynet errors."""

    def __init__(self, message):
        """Initialize the error."""
        self.message = message


class PacketError(Exception):
    """Class for Dynet packet errors."""

    def __init__(self, message):
        """Initialize the error."""
        self.message = message


class DynetPacket(object):
    """Class for a Dynet network packet."""

    def __init__(self, msg=None):
        """Initialize the packet."""
        self.opcodeType = None
        self.sync = None
        self.area = None
        self.data = []
        self.command = None
        self.join = None
        self.chk = None
        if msg is not None:
            self.fromMsg(msg)

    def toMsg(self, sync=SyncType.LOGICAL, area=0, command=0, data=[0, 0, 0], join=255):
        """Convert packet to a binary message."""
        bytes = []
        bytes.append(sync)
        bytes.append(area)
        bytes.append(data[0])
        bytes.append(command)
        bytes.append(data[1])
        bytes.append(data[2])
        bytes.append(join)
        bytes.append(self.calcsum(bytes))
        self.fromMsg(bytes)

    def fromMsg(self, msg):
        """Decode a Dynet message."""
        messageLength = len(msg)
        if messageLength < 8:
            raise PacketError("Message too short (%d bytes): %s" % (len(msg), msg))
        if messageLength > 8:
            raise PacketError("Message too long (%d bytes): %s" % (len(msg), msg))
        self._msg = msg
        self.sync = self._msg[0]
        self.area = self._msg[1]
        self.data = [self._msg[2], self._msg[4], self._msg[5]]
        self.command = self._msg[3]
        self.join = self._msg[6]
        self.chk = self._msg[7]
        if self.sync == 28:
            if OpcodeType.has_value(self.command):
                self.opcodeType = OpcodeType(self.command).name

    def toJson(self):
        """Convert to JSON."""
        return json.dumps(self.__dict__)

    def calcsum(self, msg):
        """Calculate the checksum."""
        msg = msg[:7]
        return -(sum(ord(c) for c in "".join(map(chr, msg))) % 256) & 0xFF

    def __repr__(self):
        """Print the packet."""
        return json.dumps(self.__dict__)

    def set_channel_level_packet(area, channel, level, fade):
        """Create a packet to set level of a channel."""
        channel_bank = 0xFF if (channel <= 4) else (int((channel - 1) / 4) - 1)
        target_level = int(255 - 254 * level)
        opcode = 0x80 + ((channel - 1) % 4)
        fade_time = int(fade / 0.02)
        if (fade_time) > 0xFF:
            fade_time = 0xFF
        packet = DynetPacket()
        packet.toMsg(
            sync=28,
            area=area,
            command=opcode,
            data=[target_level, channel_bank, fade_time],
            join=255,
        )
        return packet

    def select_area_preset_packet(area, preset, fade):
        """Create a packet to select a preset in an area."""
        preset = preset - 1
        bank = int((preset) / 8)
        opcode = preset - (bank * 8)
        if opcode > 3:
            opcode = opcode + 6
        fadeLow = int(fade / 0.02) - (int((fade / 0.02) / 256) * 256)
        fadeHigh = int((fade / 0.02) / 256)
        packet = DynetPacket()
        packet.toMsg(
            sync=28, area=area, command=opcode, data=[fadeLow, fadeHigh, bank], join=255
        )
        return packet

    def request_channel_level_packet(area, channel):
        """Create a packet to request the level of a specific channel."""
        packet = DynetPacket()
        packet.toMsg(
            sync=28,
            area=area,
            command=OpcodeType.REQUEST_CHANNEL_LEVEL.value,
            data=[channel - 1, 0, 0],
            join=255,
        )
        return packet

    def stop_channel_fade_packet(area, channel):
        """Create a packet to stop fade of a channel."""
        packet = DynetPacket()
        packet.toMsg(
            sync=28,
            area=area,
            command=OpcodeType.STOP_FADING.value,
            data=[channel - 1, 0, 0],
            join=255,
        )
        return packet

    def request_area_preset_packet(area):
        """Create a packet to request the current preset in an area."""
        packet = DynetPacket()
        packet.toMsg(
            sync=28,
            area=area,
            command=OpcodeType.REQUEST_PRESET.value,
            data=[0, 0, 0],
            join=255,
        )
        return packet


class DynetConnection(asyncio.Protocol):
    """Class for an asyncio protocol for the connection to Dynet."""

    def __init__(
        self,
        connectionMade=None,
        connectionLost=None,
        receiveHandler=None,
        connectionPause=None,
        connectionResume=None,
        loop=None,
    ):
        """Initialize the connection."""
        self._transport = None
        self._paused = False
        self._loop = loop
        self.connectionMade = connectionMade
        self.connectionLost = connectionLost
        self.receiveHandler = receiveHandler
        self.connectionPause = connectionPause
        self.connectionResume = connectionResume

    def connection_made(self, transport):
        """Call when connection is made."""
        self._transport = transport
        self._paused = False
        if self.connectionMade is not None:
            if self._loop is None:
                self.connectionMade(transport)
            else:
                self._loop.call_soon(self.connectionMade, transport)

    def connection_lost(self, exc=None):
        """Call when connection is lost."""
        self._transport = None
        if self.connectionLost is not None:
            if self._loop is None:
                self.connectionLost(exc)
            else:
                self._loop.call_soon(self.connectionLost, exc)

    def pause_writing(self):
        """Call when connection is paused."""
        self._paused = True
        if self.connectionPause is not None:
            if self._loop is None:
                self.connectionPause()
            else:
                self._loop.call_soon(self.connectionPause)

    def resume_writing(self):
        """Call when connection is resumed."""
        self._paused = False
        if self.connectionResume is not None:
            if self._loop is None:
                self.connectionResume()
            else:
                self._loop.call_soon(self.connectionResume)

    def data_received(self, data):
        """Call when data is received."""
        if self.receiveHandler is not None:
            if self._loop is None:
                self.receiveHandler(data)
            else:
                self._loop.call_soon(self.receiveHandler, data)

    def eof_received(self):
        """Call when EOF for connection."""
        LOGGER.debug("EOF Received")
