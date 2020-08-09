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

    def __init__(
        self,
        msg: List[int] = None,
        area: int = -1,
        command: int = -1,
        data: List[int] = None,
    ) -> None:
        """Initialize the packet."""
        # Either msg is defined or area/command/data, but not both
        if msg is None:
            # Can only have one of the two init options
            assert area != -1 and command != -1 and data
            self.area = area
            self.command = command
            self.data = data
            self._msg: List[int] = [
                SyncType.LOGICAL.value,
                area,
                data[0],
                command,
                data[1],
                data[2],
                255,  # join
            ]
            self._msg.append(self.calc_sum(self._msg))
        else:
            # Can only have one of the two init options
            assert area == -1 and command == -1 and not data
            if len(msg) != 8:
                raise PacketError(f"Wrong message size of {len(msg)} - should be 8")
            self._msg = msg
            sync = msg[0]
            assert sync == SyncType.LOGICAL.value
            self.area = msg[1]
            self.command = msg[3]
            self.data = [msg[2], msg[4], msg[5]]
            chk = msg[7]
            if chk != self.calc_sum(msg):
                raise PacketError(
                    f"Message with the wrong checksum - {[int(byte) for byte in msg]}"
                )

    @property
    def opcode_type(self) -> Optional[str]:
        """Return the alphabetic representation of the opcode if known or None."""
        if OpcodeType.has_value(self.command):
            return OpcodeType(self.command).name
        return None

    @property
    def raw_msg(self) -> List[int]:
        """Return the raw message as a list of integers."""
        return self._msg

    @property
    def msg(self) -> bytearray:
        """Get the byte array for the message to send."""
        return bytearray(self._msg)

    @staticmethod
    def calc_sum(msg: List[int]) -> int:
        """Calculate the checksum."""
        msg = msg[:7]
        return -(sum(msg) % 256) & 0xFF

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
        return DynetPacket(
            area=area, command=opcode, data=[target_level, channel_bank, fade_time]
        )

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
        return DynetPacket(area=area, command=opcode, data=[fade_low, fade_high, bank])

    @staticmethod
    def request_channel_level_packet(area: int, channel: int) -> "DynetPacket":
        """Create a packet to request the level of a specific channel."""
        return DynetPacket(
            area=area,
            command=OpcodeType.REQUEST_CHANNEL_LEVEL.value,
            data=[channel - 1, 0, 0],
        )

    @staticmethod
    def stop_channel_fade_packet(area: int, channel: int) -> "DynetPacket":
        """Create a packet to stop fade of a channel."""
        return DynetPacket(
            area=area, command=OpcodeType.STOP_FADING.value, data=[channel - 1, 0, 0]
        )

    @staticmethod
    def request_area_preset_packet(area: int, query_channel: int) -> "DynetPacket":
        """Create a packet to request the current preset in an area."""
        return DynetPacket(
            area=area,
            command=OpcodeType.REQUEST_PRESET.value,
            data=[0, query_channel - 1, 0],
        )

    @staticmethod
    def report_channel_level_packet(
        area: int, channel: int, target_level: float, actual_level: float
    ) -> "DynetPacket":
        """Create a packet that reports the level of a channel."""
        assert 0.0 <= target_level <= 1.0
        assert 0.0 <= actual_level <= 1.0
        return DynetPacket(
            area=area,
            command=OpcodeType.REPORT_CHANNEL_LEVEL.value,
            data=[
                channel - 1,
                int(255 - 254 * target_level),
                int(255 - 254 * actual_level),
            ],
        )

    @staticmethod
    def report_area_preset_packet(area: int, preset: int) -> "DynetPacket":
        """Create a packet that reports the current preset in an area."""
        return DynetPacket(
            area=area, command=OpcodeType.REPORT_PRESET.value, data=[preset - 1, 0, 0]
        )

    @staticmethod
    def fade_area_channel_preset_packet(
        area: int, channel: int, preset: int, fade: float
    ) -> "DynetPacket":
        """Create a packet that reports the current preset in an area."""
        fade_time = int(fade / 0.02)
        if (fade_time) > 0xFF:
            fade_time = 0xFF
        return DynetPacket(
            area=area,
            command=OpcodeType.FADE_CHANNEL_AREA_TO_PRESET.value,
            data=[channel - 1, preset - 1, fade_time],
        )
