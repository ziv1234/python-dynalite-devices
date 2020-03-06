"""Tests for DynaliteDevices."""

import pytest

import dynalite_devices_lib.const as dyn_const
from dynalite_devices_lib.dynet import DynetPacket

pytestmark = pytest.mark.asyncio


async def test_empty_dynalite_devices(mock_gateway):
    """Test the dynalite devices library with no devices."""
    mock_gateway.configure_dyn_dev(
        {
            dyn_const.CONF_ACTIVE: False,
            dyn_const.CONF_AREA: {"1": {dyn_const.CONF_NO_DEFAULT: True}},
        },
        0,
    )
    await mock_gateway.async_setup_dyn_dev()
    await mock_gateway.check_writes([])


async def test_dynalite_devices_active_on(mock_gateway):
    """Test the dynalite devices library."""
    mock_gateway.configure_dyn_dev(
        {
            dyn_const.CONF_ACTIVE: True,
            dyn_const.CONF_AREA: {"1": {dyn_const.CONF_CHANNEL: {"1": {}, "2": {}}}},
            dyn_const.CONF_PRESET: {"1": {}},
        },
        3,
    )
    await mock_gateway.async_setup_dyn_dev()
    await mock_gateway.check_writes(
        [
            DynetPacket.request_channel_level_packet(1, 1),
            DynetPacket.request_channel_level_packet(1, 2),
            DynetPacket.request_area_preset_packet(1),
        ]
    )
    await mock_gateway.receive(DynetPacket.report_area_preset_packet(1, 1))
    await mock_gateway.check_writes(
        [
            DynetPacket.request_channel_level_packet(1, 1),
            DynetPacket.request_channel_level_packet(1, 2),
        ]
    )


async def test_dynalite_devices_active_off(mock_gateway):
    """Test the dynalite devices library."""
    mock_gateway.configure_dyn_dev(
        {
            dyn_const.CONF_ACTIVE: False,
            dyn_const.CONF_AREA: {"1": {dyn_const.CONF_CHANNEL: {"1": {}, "2": {}}}},
            dyn_const.CONF_PRESET: {"1": {}},
        },
        3,
    )
    await mock_gateway.async_setup_dyn_dev()
    await mock_gateway.check_writes([])
    await mock_gateway.receive(DynetPacket.report_area_preset_packet(1, 1))
    await mock_gateway.check_writes([])


async def test_dynalite_devices_active_init(mock_gateway):
    """Test the dynalite devices library."""
    mock_gateway.configure_dyn_dev(
        {
            dyn_const.CONF_ACTIVE: dyn_const.CONF_ACTIVE_INIT,
            dyn_const.CONF_AREA: {"1": {dyn_const.CONF_CHANNEL: {"1": {}, "2": {}}}},
            dyn_const.CONF_PRESET: {"1": {}},
        },
        3,
    )
    await mock_gateway.async_setup_dyn_dev()
    await mock_gateway.check_writes(
        [
            DynetPacket.request_channel_level_packet(1, 1),
            DynetPacket.request_channel_level_packet(1, 2),
            DynetPacket.request_area_preset_packet(1),
        ]
    )
    await mock_gateway.receive(DynetPacket.report_area_preset_packet(1, 1))
    await mock_gateway.check_writes([])


async def test_dynalite_devices_reconfig(mock_gateway):
    """Test the dynalite devices library."""
    config = {
        dyn_const.CONF_ACTIVE: False,
        dyn_const.CONF_AREA: {
            "1": {dyn_const.CONF_CHANNEL: {"1": {}, "2": {}}},
            "2": {dyn_const.CONF_TEMPLATE: dyn_const.CONF_ROOM},
            "4": {dyn_const.CONF_TEMPLATE: dyn_const.CONF_TIME_COVER},
        },
        dyn_const.CONF_PRESET: {"1": {}},
    }
    mock_gateway.configure_dyn_dev(config, 5)
    await mock_gateway.async_setup_dyn_dev()
    mock_gateway.configure_dyn_dev(config, 0)
