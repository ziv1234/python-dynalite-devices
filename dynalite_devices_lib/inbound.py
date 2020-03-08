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
    CONF_ACTION_REPORT,
    CONF_ACTION_STOP,
    CONF_ALL,
    CONF_AREA,
    CONF_CHANNEL,
    CONF_FADE,
    CONF_PRESET,
    CONF_TRGT_LEVEL,
    EVENT_CHANNEL,
    EVENT_PRESET,
)
from .event import DynetEvent


class DynetInbound:
    """Class to handle inboud Dynet packets."""

    def __init__(self):
        """Initialize the object."""
        pass

    @staticmethod
    def preset(packet):
        """Handle a preset that was selected."""
        if packet.command > 3:
            packet.preset = packet.command - 6
        else:
            packet.preset = packet.command
        packet.preset = (packet.preset + (packet.data[2] * 8)) + 1
        packet.fade = (packet.data[0] + (packet.data[1] * 256)) * 0.02
        return DynetEvent(
            event_type=EVENT_PRESET,
            message=(
                "Area %d Preset %d Fade %d seconds."
                % (packet.area, packet.preset, packet.fade)
            ),
            data={
                CONF_AREA: packet.area,
                CONF_PRESET: packet.preset,
                CONF_FADE: packet.fade,
            },
        )

    def preset_1(self, packet):
        """Handle preset 1 in banks of 8."""
        return self.preset(packet)

    def preset_2(self, packet):
        """Handle preset 2 in banks of 8."""
        return self.preset(packet)

    def preset_3(self, packet):
        """Handle preset 3 in banks of 8."""
        return self.preset(packet)

    def preset_4(self, packet):
        """Handle preset 4 in banks of 8."""
        return self.preset(packet)

    def preset_5(self, packet):
        """Handle preset 5 in banks of 8."""
        return self.preset(packet)

    def preset_6(self, packet):
        """Handle preset 6 in banks of 8."""
        return self.preset(packet)

    def preset_7(self, packet):
        """Handle preset 7 in banks of 8."""
        return self.preset(packet)

    def preset_8(self, packet):
        """Handle preset 8 in banks of 8."""
        return self.preset(packet)

    @staticmethod
    def report_preset(packet):
        """Report the current preset of an area."""
        packet.preset = packet.data[0] + 1
        return DynetEvent(
            event_type=EVENT_PRESET,
            message=("Current Area %d Preset is %d" % (packet.area, packet.preset)),
            data={CONF_AREA: packet.area, CONF_PRESET: packet.preset},
        )

    @staticmethod
    def linear_preset(packet):
        """Report that preset was selected with fade."""
        packet.preset = packet.data[0] + 1
        packet.fade = (packet.data[1] + (packet.data[2] * 256)) * 0.02
        return DynetEvent(
            event_type=EVENT_PRESET,
            message=(
                "Area %d Preset %d Fade %d seconds."
                % (packet.area, packet.preset, packet.fade)
            ),
            data={
                CONF_AREA: packet.area,
                CONF_PRESET: packet.preset,
                CONF_FADE: packet.fade,
            },
        )

    @staticmethod
    def report_channel_level(packet):
        """Report the new level of a channel."""
        channel = packet.data[0] + 1
        target_level = packet.data[1]
        actual_level = packet.data[2]
        return DynetEvent(
            event_type=EVENT_CHANNEL,
            message=(
                "Area %d Channel %d Target Level %d Actual Level %d.",
                packet.area,
                channel,
                target_level,
                actual_level,
            ),
            data={
                CONF_AREA: packet.area,
                CONF_CHANNEL: channel,
                CONF_ACTION: CONF_ACTION_REPORT,
                CONF_TRGT_LEVEL: target_level,
                CONF_ACT_LEVEL: actual_level,
            },
        )

    @staticmethod
    def set_channel_x_to_level_with_fade(packet, channel_offset):
        """Report that a channel was set to a specific level."""
        channel = ((packet.data[1] + 1) % 256) * 4 + channel_offset
        target_level = packet.data[0]
        return DynetEvent(
            event_type=EVENT_CHANNEL,
            message=(
                "Area %d Channel %d Target Level %d",
                packet.area,
                channel,
                target_level,
            ),
            data={
                CONF_AREA: packet.area,
                CONF_CHANNEL: channel,
                CONF_ACTION: CONF_ACTION_CMD,
                CONF_TRGT_LEVEL: target_level,
            },
        )

    def set_channel_1_to_level_with_fade(self, packet):
        """Report that channel 1 was set to a specific level."""
        return self.set_channel_x_to_level_with_fade(packet, 1)

    def set_channel_2_to_level_with_fade(self, packet):
        """Report that channel 2 was set to a specific level."""
        return self.set_channel_x_to_level_with_fade(packet, 2)

    def set_channel_3_to_level_with_fade(self, packet):
        """Report that channel 3 was set to a specific level."""
        return self.set_channel_x_to_level_with_fade(packet, 3)

    def set_channel_4_to_level_with_fade(self, packet):
        """Report that channel 4 was set to a specific level."""
        return self.set_channel_x_to_level_with_fade(packet, 4)

    @staticmethod
    def request_channel_level(packet):
        """Do nothing."""
        pass

    @staticmethod
    def stop_fading(packet):
        """Report that fading stopped for a channel or area."""
        channel = packet.data[0] + 1
        if channel == 256:  # all channels in area
            channel = CONF_ALL
        return DynetEvent(
            event_type=EVENT_CHANNEL,
            message=("Area %d Channel %s" % (packet.area, channel)),
            data={
                CONF_AREA: packet.area,
                CONF_CHANNEL: channel,
                CONF_ACTION: CONF_ACTION_STOP,
            },
        )
