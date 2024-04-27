"""Tests for DynaliteDevices."""

import pytest

import dynalite_devices_lib.const as dyn_const
from dynalite_devices_lib.dynet import DynetPacket
from dynalite_devices_lib.opcodes import OpcodeType

from .common import packet_notification, preset_notification


def preset_select_func(area, preset):
    """Create preset selection packet."""
    return DynetPacket.select_area_preset_packet(area, preset, 0)


def linear_func(area, preset):
    """Create preset linear fade packet."""
    return DynetPacket(
        area=area, command=OpcodeType.LINEAR_PRESET.value, data=[preset - 1, 0, 0]
    )


def report_func(area, preset):
    """Create preset report packet."""
    return DynetPacket.report_area_preset_packet(area, preset)


def set_channel_func(area, channel):
    """Create channel set level packet."""
    return DynetPacket.set_channel_level_packet(area, channel, 1, 0)


def report_channel_func(area, channel):
    """Create channel report level packet."""
    return DynetPacket.report_channel_level_packet(area, channel, 1, 1)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "conf, packet_func",
    [
        (dyn_const.CONF_PRESET, preset_select_func),
        (dyn_const.CONF_PRESET, linear_func),
        (dyn_const.CONF_PRESET, report_func),
        (dyn_const.CONF_CHANNEL, set_channel_func),
        (dyn_const.CONF_CHANNEL, report_channel_func),
    ],
)
async def test_selections(mock_gateway, conf, packet_func):
    """Run preset / channel selection tests with various commands."""
    devices = mock_gateway.configure_dyn_dev(
        {
            dyn_const.CONF_ACTIVE: False,
            dyn_const.CONF_AREA: {"2": {conf: {i: {} for i in range(1, 9)}}},
            dyn_const.CONF_PRESET: {},
        },
        8,
    )
    for device in devices:
        assert not device.is_on
    assert await mock_gateway.async_setup_dyn_dev()
    await mock_gateway.check_single_update(None)
    for i in range(1, 9):
        packet = packet_func(2, i)
        await mock_gateway.receive(packet)
        exp_notifications = [packet_notification(packet.raw_msg)]
        if conf == dyn_const.CONF_CHANNEL:
            await mock_gateway.check_single_update(devices[i - 1])
            assert devices[i - 1].is_on
        else:  # CONF_PRESET
            await mock_gateway.check_updates(devices)
            for j in range(1, 9):
                assert devices[j - 1].is_on == (i == j)
            exp_notifications.append(preset_notification(2, i))
        await mock_gateway.check_notifications(exp_notifications)


@pytest.mark.asyncio
async def test_inbound_request_channel_level(mock_gateway):
    """Test when the network requests a channel level. Nothing to do, just be sure nothing bad happens..."""
    [device] = mock_gateway.configure_dyn_dev(
        {
            dyn_const.CONF_ACTIVE: False,
            dyn_const.CONF_AREA: {"3": {dyn_const.CONF_CHANNEL: {"5": {}}}},
            dyn_const.CONF_PRESET: {},
        },
        1,
    )
    assert not device.is_on
    assert await mock_gateway.async_setup_dyn_dev()
    await mock_gateway.check_single_update(None)
    packet = DynetPacket.request_channel_level_packet(3, 5)
    await mock_gateway.receive(packet)
    await mock_gateway.check_notifications([packet_notification(packet.raw_msg)])
    assert not device.is_on
