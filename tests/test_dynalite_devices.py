"""Tests for DynaliteDevices."""

import dynalite_devices_lib.const as dyn_const
import dynalite_devices_lib.dynet as dyn_dynet
import pytest

pytestmark = pytest.mark.asyncio


async def test_empty_dynalite_devices(mock_gateway):
    """Test the dynalite devices library with no devices."""
    name = "NAME"
    mock_gateway.configure_dyn_dev(
        {
            dyn_const.CONF_AREA: {
                "1": {dyn_const.CONF_NAME: name, dyn_const.CONF_NO_DEFAULT: True}
            }
        }
    )
    await mock_gateway.async_setup_dyn_dev(0)


async def test_dynalite_devices_channel(mock_gateway):
    """Test the dynalite devices library."""
    name = "NAME"
    channel_name = "CHANNEL"
    mock_gateway.configure_dyn_dev(
        {
            dyn_const.CONF_ACTIVE: True,
            dyn_const.CONF_AREA: {
                "1": {
                    dyn_const.CONF_NAME: name,
                    dyn_const.CONF_NO_DEFAULT: True,
                    dyn_const.CONF_CHANNEL: {"1": {dyn_const.CONF_NAME: channel_name}},
                }
            },
        }
    )
    await mock_gateway.async_setup_dyn_dev()
    await mock_gateway.check_writes(
        [
            dyn_dynet.DynetPacket.request_channel_level_packet(1, 1),
            dyn_dynet.DynetPacket.request_area_preset_packet(1),
        ]
    )
