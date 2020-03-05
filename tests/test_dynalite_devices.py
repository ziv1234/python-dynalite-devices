"""Tests for DynaliteDevices."""

import dynalite_devices_lib.const as dyn_const
import dynalite_devices_lib.dynet as dyn_dynet


async def test_empty_dynalite_devices(mock_gw):
    """Test the dynalite devices library with no devices."""
    name = "NAME"
    mock_gw.dyn_dev.configure(
        {
            dyn_const.CONF_AREA: {
                "1": {dyn_const.CONF_NAME: name, dyn_const.CONF_NO_DEFAULT: True}
            }
        }
    )
    await mock_gw.async_setup(0)


async def test_dynalite_devices_channel(mock_gw):
    """Test the dynalite devices library."""
    name = "NAME"
    channel_name = "CHANNEL"
    mock_gw.dyn_dev.configure(
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
    await mock_gw.async_setup()
    await mock_gw.check_writes(
        [
            dyn_dynet.DynetPacket.request_channel_level_packet(1, 1),
            dyn_dynet.DynetPacket.request_area_preset_packet(1),
        ]
    )
