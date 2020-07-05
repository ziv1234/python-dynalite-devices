"""
Class that handles inbound requests on the Dynet network and fires events.

@ Author      : Troy Kelly
@ Date        : 23 Sept 2018
@ Description : Philips Dynalite Library - Unofficial interface for Philips Dynalite over RS485

@ Notes:        Requires a RS485 to IP gateway (Do not use the Dynalite one - use something cheaper)
"""

from .const import (
    CONF_ACT_LEVEL,
    CONF_ACTION,
    CONF_ACTION_CMD,
    CONF_ACTION_PRESET,
    CONF_ACTION_REPORT,
    CONF_ACTION_STOP,
    CONF_AREA,
    CONF_CHANNEL,
    CONF_FADE,
    CONF_PRESET,
    CONF_TRGT_LEVEL,
    EVENT_CHANNEL,
    EVENT_PRESET,
)
from .dynet import DynetPacket
from .event import DynetEvent


class DynetInbound:
    """Class to handle inboud Dynet packets."""

    def __init__(self) -> None:
        """Initialize the object."""
        pass

    @staticmethod
    def preset(packet: DynetPacket) -> DynetEvent:
        """Handle a preset that was selected."""
        if packet.command > 3:
            preset = packet.command - 6
        else:
            preset = packet.command
        preset = (preset + (packet.data[2] * 8)) + 1
        fade = (packet.data[0] + (packet.data[1] * 256)) * 0.02
        return DynetEvent(
            event_type=EVENT_PRESET,
            data={CONF_AREA: packet.area, CONF_PRESET: preset, CONF_FADE: fade},
        )

    def preset_1(self, packet: DynetPacket) -> DynetEvent:
        """Handle preset 1 in banks of 8."""
        return self.preset(packet)

    def preset_2(self, packet: DynetPacket) -> DynetEvent:
        """Handle preset 2 in banks of 8."""
        return self.preset(packet)

    def preset_3(self, packet: DynetPacket) -> DynetEvent:
        """Handle preset 3 in banks of 8."""
        return self.preset(packet)

    def preset_4(self, packet: DynetPacket) -> DynetEvent:
        """Handle preset 4 in banks of 8."""
        return self.preset(packet)

    def preset_5(self, packet: DynetPacket) -> DynetEvent:
        """Handle preset 5 in banks of 8."""
        return self.preset(packet)

    def preset_6(self, packet: DynetPacket) -> DynetEvent:
        """Handle preset 6 in banks of 8."""
        return self.preset(packet)

    def preset_7(self, packet: DynetPacket) -> DynetEvent:
        """Handle preset 7 in banks of 8."""
        return self.preset(packet)

    def preset_8(self, packet: DynetPacket) -> DynetEvent:
        """Handle preset 8 in banks of 8."""
        return self.preset(packet)

    @staticmethod
    def report_preset(packet: DynetPacket) -> DynetEvent:
        """Report the current preset of an area."""
        preset = packet.data[0] + 1
        return DynetEvent(
            event_type=EVENT_PRESET, data={CONF_AREA: packet.area, CONF_PRESET: preset},
        )

    @staticmethod
    def linear_preset(packet: DynetPacket) -> DynetEvent:
        """Report that preset was selected with fade."""
        preset = packet.data[0] + 1
        fade = (packet.data[1] + (packet.data[2] * 256)) * 0.02
        return DynetEvent(
            event_type=EVENT_PRESET,
            data={CONF_AREA: packet.area, CONF_PRESET: preset, CONF_FADE: fade},
        )

    @staticmethod
    def report_channel_level(packet: DynetPacket) -> DynetEvent:
        """Report the new level of a channel."""
        channel = packet.data[0] + 1
        target_level = packet.data[1]
        actual_level = packet.data[2]
        return DynetEvent(
            event_type=EVENT_CHANNEL,
            data={
                CONF_AREA: packet.area,
                CONF_CHANNEL: channel,
                CONF_ACTION: CONF_ACTION_REPORT,
                CONF_TRGT_LEVEL: target_level,
                CONF_ACT_LEVEL: actual_level,
            },
        )

    @staticmethod
    def set_channel_x_to_level_with_fade(
        packet: DynetPacket, channel_offset: int
    ) -> DynetEvent:
        """Report that a channel was set to a specific level."""
        channel = ((packet.data[1] + 1) % 256) * 4 + channel_offset
        target_level = packet.data[0]
        return DynetEvent(
            event_type=EVENT_CHANNEL,
            data={
                CONF_AREA: packet.area,
                CONF_CHANNEL: channel,
                CONF_ACTION: CONF_ACTION_CMD,
                CONF_TRGT_LEVEL: target_level,
            },
        )

    def set_channel_1_to_level_with_fade(self, packet: DynetPacket) -> DynetEvent:
        """Report that channel 1 was set to a specific level."""
        return self.set_channel_x_to_level_with_fade(packet, 1)

    def set_channel_2_to_level_with_fade(self, packet: DynetPacket) -> DynetEvent:
        """Report that channel 2 was set to a specific level."""
        return self.set_channel_x_to_level_with_fade(packet, 2)

    def set_channel_3_to_level_with_fade(self, packet: DynetPacket) -> DynetEvent:
        """Report that channel 3 was set to a specific level."""
        return self.set_channel_x_to_level_with_fade(packet, 3)

    def set_channel_4_to_level_with_fade(self, packet: DynetPacket) -> DynetEvent:
        """Report that channel 4 was set to a specific level."""
        return self.set_channel_x_to_level_with_fade(packet, 4)

    @staticmethod
    def request_channel_level(packet: DynetPacket) -> None:
        """Do nothing."""
        pass

    @staticmethod
    def stop_fading(packet: DynetPacket) -> DynetEvent:
        """Report that fading stopped for a channel or area."""
        data = {CONF_AREA: packet.area, CONF_ACTION: CONF_ACTION_STOP}
        channel = packet.data[0] + 1
        if channel != 256:  # all channels in area
            data[CONF_CHANNEL] = channel
        return DynetEvent(event_type=EVENT_CHANNEL, data=data)

    @staticmethod
    def fade_channel_area_to_preset(packet: DynetPacket) -> DynetEvent:
        """Report that fading stopped for a channel or area XXX."""
        fade = packet.data[2] * 0.02
        data = {
            CONF_AREA: packet.area,
            CONF_ACTION: CONF_ACTION_PRESET,
            CONF_PRESET: packet.data[1] + 1,
            CONF_FADE: fade,
        }
        channel = packet.data[0] + 1
        if channel != 256:  # all channels in area
            data[CONF_CHANNEL] = channel
        return DynetEvent(event_type=EVENT_CHANNEL, data=data)
