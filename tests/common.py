"""Common functions for Dynalite tests."""

import dynalite_devices_lib.const as dyn_const
from dynalite_devices_lib.dynalite_devices import DynaliteNotification


def packet_notification(packet):
    """Create a notification for a Dynalite packet."""
    return DynaliteNotification(
        dyn_const.NOTIFICATION_PACKET, {dyn_const.NOTIFICATION_PACKET: packet},
    )


def preset_notification(area, preset):
    """Create a notification for a preset that is selected."""
    return DynaliteNotification(
        dyn_const.NOTIFICATION_PRESET,
        {dyn_const.CONF_AREA: area, dyn_const.CONF_PRESET: preset},
    )
