"""Tests for DynaliteDevices."""

import asyncio

import pytest

import dynalite_devices_lib.const as dyn_const

pytestmark = pytest.mark.asyncio


async def test_dynalite_disconnection(mock_gateway):
    """Test the dynalite devices library."""
    devices = mock_gateway.configure_dyn_dev(
        {
            dyn_const.CONF_ACTIVE: False,
            dyn_const.CONF_AREA: {
                "1": {dyn_const.CONF_CHANNEL: {"1": {}, "2": {}}},
                "2": {dyn_const.CONF_TEMPLATE: dyn_const.CONF_ROOM},
                "3": {dyn_const.CONF_TEMPLATE: dyn_const.CONF_TIME_COVER},
            },
            dyn_const.CONF_PRESET: {"6": {}},
        },
        5,
    )
    assert await mock_gateway.async_setup_dyn_dev()
    for device in devices:
        assert device.available
    # Disconnect
    mock_gateway.reset_connection()
    await asyncio.sleep(0.5)
    for device in devices:
        assert not device.available
    # Wait for reconnect
    await asyncio.sleep(1)
    for device in devices:
        assert device.available


async def test_dynalite_no_server(mock_gateway):
    """Test the dynalite devices library."""
    mock_gateway.configure_dyn_dev({dyn_const.CONF_PORT: 12333}, 0)
    assert not await mock_gateway.async_setup_dyn_dev()
