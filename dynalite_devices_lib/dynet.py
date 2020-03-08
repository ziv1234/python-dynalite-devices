"""
Library to handle Dynet networks.

@ Author      : Troy Kelly
@ Date        : 23 Sept 2018
@ Description : Philips Dynalite Library - Unofficial interface for Philips Dynalite over RS485

@ Notes:        Requires a RS485 to IP gateway (Do not use the Dynalite one - use something cheaper)
"""

import json

from .opcodes import OpcodeType, SyncType


class PacketError(Exception):
    """Class for Dynet packet errors."""

    def __init__(self, message):
        """Initialize the error."""
        self.message = message
        super().__init__(message)


class DynetPacket:
    """Class for a Dynet network packet."""

    def __init__(self, msg=None):
        """Initialize the packet."""
        self.opcode_type = None
        self.area = None
        self.data = []
        self.command = None
        if msg is not None:
            self.from_msg(msg)

    def to_msg(self, area, command, data):
        """Convert packet to a binary message."""
        my_bytes = bytearray()
        my_bytes.append(SyncType.LOGICAL.value)
        my_bytes.append(area)
        my_bytes.append(data[0])
        my_bytes.append(command)
        my_bytes.append(data[1])
        my_bytes.append(data[2])
        my_bytes.append(255)  # join
        my_bytes.append(self.calc_sum(my_bytes))
        self.from_msg(my_bytes)

    def from_msg(self, msg):
        """Decode a Dynet message."""
        message_length = len(msg)
        if message_length < 8:
            raise PacketError(f"Message too short ({len(msg)} bytes): {msg}")
        if message_length > 8:
            raise PacketError(f"Message too long ({len(msg)} bytes): {msg}")
        self.msg = msg
        sync = msg[0]
        self.area = msg[1]
        self.data = [msg[2], msg[4], msg[5]]
        self.command = msg[3]
        chk = self.msg[7]
        if chk != self.calc_sum(msg):
            raise PacketError(
                f"Message with the wrong checksum - {[int(byte) for byte in msg]}"
            )
        if sync == SyncType.LOGICAL.value:
            if OpcodeType.has_value(self.command):
                self.opcode_type = OpcodeType(self.command).name

    @staticmethod
    def calc_sum(msg):
        """Calculate the checksum."""
        msg = msg[:7]
        return -(sum(ord(c) for c in "".join(map(chr, msg))) % 256) & 0xFF

    def __repr__(self):
        """Print the packet."""
        return json.dumps(self.__dict__)

    @staticmethod
    def set_channel_level_packet(area, channel, level, fade):
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
    def select_area_preset_packet(area, preset, fade):
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
    def request_channel_level_packet(area, channel):
        """Create a packet to request the level of a specific channel."""
        packet = DynetPacket()
        packet.to_msg(
            area=area,
            command=OpcodeType.REQUEST_CHANNEL_LEVEL.value,
            data=[channel - 1, 0, 0],
        )
        return packet

    @staticmethod
    def stop_channel_fade_packet(area, channel):
        """Create a packet to stop fade of a channel."""
        packet = DynetPacket()
        packet.to_msg(
            area=area, command=OpcodeType.STOP_FADING.value, data=[channel - 1, 0, 0],
        )
        return packet

    @staticmethod
    def request_area_preset_packet(area):
        """Create a packet to request the current preset in an area."""
        packet = DynetPacket()
        packet.to_msg(
            area=area, command=OpcodeType.REQUEST_PRESET.value, data=[0, 0, 0],
        )
        return packet

    @staticmethod
    def report_channel_level_packet(area, channel, target_level, actual_level):
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
    def report_area_preset_packet(area, preset):
        """Create a packet that reports the current preset in an area."""
        packet = DynetPacket()
        packet.to_msg(
            area=area, command=OpcodeType.REPORT_PRESET.value, data=[preset - 1, 0, 0],
        )
        return packet
