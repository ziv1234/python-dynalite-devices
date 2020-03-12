"""
Library to handle Dynet networks.

@ Author      : Troy Kelly
@ Date        : 23 Sept 2018
@ Description : Philips Dynalite Library - Unofficial interface for Philips Dynalite over RS485

@ Notes:        Requires a RS485 to IP gateway (Do not use the Dynalite one - use something cheaper)
"""

import json
from typing import List, Optional

from .opcodes import OpcodeType, SyncType


class PacketError(Exception):
    """Class for Dynet packet errors."""

    def __init__(self, message: str) -> None:
        """Initialize the error."""
        self.message = message
        super().__init__(message)


class DynetPacket:
    """Class for a Dynet network packet."""

    def __init__(self, msg: List[int] = None) -> None:
        """Initialize the packet."""
        self.opcode_type: Optional[str] = None
        self.area = -1
        self.data: List[int] = []
        self.command = -1
        if msg is not None:
            self.from_msg(msg)

    def to_msg(self, area: int, command: int, data: List[int]) -> None:
        """Convert packet to a binary message."""
        my_bytes: List[int] = []
        my_bytes.append(SyncType.LOGICAL.value)
        my_bytes.append(area)
        my_bytes.append(data[0])
        my_bytes.append(command)
        my_bytes.append(data[1])
        my_bytes.append(data[2])
        my_bytes.append(255)  # join
        my_bytes.append(self.calc_sum(my_bytes))
        self.from_msg(my_bytes)

    def from_msg(self, msg: List[int]) -> None:
        """Decode a Dynet message."""
        message_length = len(msg)
        if message_length < 8:
            raise PacketError(f"Message too short ({len(msg)} bytes): {msg}")
        if message_length > 8:
            raise PacketError(f"Message too long ({len(msg)} bytes): {msg}")
        self.msg = bytearray()
        for byte in msg:
            self.msg.append(byte)
        sync = self.msg[0]
        self.area = self.msg[1]
        self.data = [self.msg[2], self.msg[4], self.msg[5]]
        self.command = self.msg[3]
        chk = self.msg[7]
        if chk != self.calc_sum(msg):
            raise PacketError(
                f"Message with the wrong checksum - {[int(byte) for byte in msg]}"
            )
        assert sync == SyncType.LOGICAL.value
        if OpcodeType.has_value(self.command):
            self.opcode_type = OpcodeType(self.command).name

    @staticmethod
    def calc_sum(msg: List[int]) -> int:
        """Calculate the checksum."""
        msg = msg[:7]
        return -(sum(ord(c) for c in "".join(map(chr, msg))) % 256) & 0xFF

    def __repr__(self):
        """Print the packet."""
        return json.dumps(self.__dict__)

    @staticmethod
    def set_channel_level_packet(
        area: int, channel: int, level: float, fade: float
    ) -> "DynetPacket":
        """Create a packet to set level of a channel."""
        channel_bank = 0xFF if (channel <= 4) else (int((channel - 1) / 4) - 1)
        target_level = int(255 - 254 * level)
        opcode = 0x80 + ((channel - 1) % 4)
        fade_time = int(fade / 0.02)
        if (fade_time) > 0xFF:
            fade_time = 0xFF
        packet = DynetPacket()
        packet.to_msg(
            area=area, command=opcode, data=[target_level, channel_bank, fade_time],
        )
        return packet

    @staticmethod
    def select_area_preset_packet(area: int, preset: int, fade: float) -> "DynetPacket":
        """Create a packet to select a preset in an area."""
        preset = preset - 1
        bank = int((preset) / 8)
        opcode = preset - (bank * 8)
        if opcode > 3:
            opcode = opcode + 6
        fade_low = int(fade / 0.02) - (int((fade / 0.02) / 256) * 256)
        fade_high = int((fade / 0.02) / 256)
        packet = DynetPacket()
        packet.to_msg(
            area=area, command=opcode, data=[fade_low, fade_high, bank],
        )
        return packet

    @staticmethod
    def request_channel_level_packet(area: int, channel: int) -> "DynetPacket":
        """Create a packet to request the level of a specific channel."""
        packet = DynetPacket()
        packet.to_msg(
            area=area,
            command=OpcodeType.REQUEST_CHANNEL_LEVEL.value,
            data=[channel - 1, 0, 0],
        )
        return packet

    @staticmethod
    def stop_channel_fade_packet(area: int, channel: int) -> "DynetPacket":
        """Create a packet to stop fade of a channel."""
        packet = DynetPacket()
        packet.to_msg(
            area=area, command=OpcodeType.STOP_FADING.value, data=[channel - 1, 0, 0],
        )
        return packet

    @staticmethod
    def request_area_preset_packet(area: int) -> "DynetPacket":
        """Create a packet to request the current preset in an area."""
        packet = DynetPacket()
        packet.to_msg(
            area=area, command=OpcodeType.REQUEST_PRESET.value, data=[0, 0, 0],
        )
        return packet

    @staticmethod
    def report_channel_level_packet(
        area: int, channel: int, target_level: float, actual_level: float
    ) -> "DynetPacket":
        """Create a packet that reports the level of a channel."""
        packet = DynetPacket()
        packet.to_msg(
            area=area,
            command=OpcodeType.REPORT_CHANNEL_LEVEL.value,
            data=[
                channel - 1,
                int(255 - 254 * target_level),
                int(255 - 254 * actual_level),
            ],
        )
        return packet

    @staticmethod
    def report_area_preset_packet(area: int, preset: int) -> "DynetPacket":
        """Create a packet that reports the current preset in an area."""
        packet = DynetPacket()
        packet.to_msg(
            area=area, command=OpcodeType.REPORT_PRESET.value, data=[preset - 1, 0, 0],
        )
        return packet
