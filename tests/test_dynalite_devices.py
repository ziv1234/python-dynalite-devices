"""Tests for DynaliteDevices."""
import asyncio

from asynctest import call
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
    await mock_gw.async_setup()
    assert mock_gw.new_dev_func.mock_calls == []


async def test_dynalite_devices_channel(mock_gw):
    """Test the dynalite devices library."""
    name = "NAME"
    channel_name = "CHANNEL"
    mock_gw.dyn_dev.configure(
        {
            dyn_const.CONF_ACTIVE: dyn_const.CONF_ACTIVE_ON,
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
    mock_gw.new_dev_func.assert_called_once()
    dyn_const.LOGGER.error("XXX %s", mock_gw.new_dev_func.mock_calls)
    await asyncio.sleep(0.1)
    assert (
        call.write(dyn_dynet.DynetPacket.request_channel_level_packet(1, 1).msg)
        in mock_gw.mock_writer.mock_calls
    )
