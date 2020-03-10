"""Tests for DynaliteDevices."""

import pytest

import dynalite_devices_lib.const as dyn_const
from dynalite_devices_lib.dynet import DynetPacket
from dynalite_devices_lib.opcodes import OpcodeType


def preset_select_func(area, preset):
    """Create preset selection packet."""
    return DynetPacket.select_area_preset_packet(area, preset, 0)


def linear_func(area, preset):
    """Create preset linear fade packet."""
    packet = DynetPacket()
    packet.to_msg(area, OpcodeType.LINEAR_PRESET.value, [preset - 1, 0, 0])
    return packet


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
    for i in range(1, 9):
        await mock_gateway.receive(packet_func(2, i))
        if conf == dyn_const.CONF_CHANNEL:
            assert devices[i - 1].is_on
        else:  # CONF_PRESET
            for j in range(1, 9):
                assert devices[j - 1].is_on == (i == j)


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
    await mock_gateway.receive(DynetPacket.request_channel_level_packet(3, 5))
    assert not device.is_on
