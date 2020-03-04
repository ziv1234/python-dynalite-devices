"""Tests for DynaliteDevices."""
import asyncio

from asynctest import call
import dynalite_devices_lib.const as dyn_const
import dynalite_devices_lib.dynet as dyn_dynet


async def test_switch(mock_gw):
    """Test the dynalite devices library."""
    name = "NAME"
    preset_name = "PRESET"
    mock_gw.dyn_dev.configure(
        {
            dyn_const.CONF_ACTIVE: False,
            dyn_const.CONF_AREA: {
                "1": {
                    dyn_const.CONF_NAME: name,
                    dyn_const.CONF_NO_DEFAULT: True,
                    dyn_const.CONF_PRESET: {
                        "1": {
                            dyn_const.CONF_NAME: preset_name,
                            dyn_const.CONF_FADE: 0.5,
                        },
                        "4": {
                            dyn_const.CONF_NAME: preset_name,
                            dyn_const.CONF_FADE: 0.7,
                        },
                    },
                }
            },
        }
    )
    await mock_gw.async_setup()
    mock_gw.new_dev_func.assert_called_once()
    assert len(mock_gw.new_dev_func.mock_calls[0][1][0]) == 1
    device = mock_gw.new_dev_func.mock_calls[0][1][0][0]
    assert device.category == "switch"
    await device.async_turn_on()
    await asyncio.sleep(0.1)
    mock_gw.mock_writer.write.assert_called_once()
    assert (
        call.write(dyn_dynet.DynetPacket.set_channel_level_packet(1, 1, 1.0, 0.5).msg)
        in mock_gw.mock_writer.mock_calls
    )
    assert device.brightness == 255
    mock_gw.mock_writer.reset_mock()
    await device.async_turn_on(brightness=51)
    await asyncio.sleep(0.1)
    mock_gw.mock_writer.write.assert_called_once()
    assert (
        call.write(dyn_dynet.DynetPacket.set_channel_level_packet(1, 1, 0.2, 0.5).msg)
        in mock_gw.mock_writer.mock_calls
    )
    assert device.brightness == 51
    mock_gw.mock_writer.reset_mock()
    await device.async_turn_off()
    await asyncio.sleep(0.1)
    mock_gw.mock_writer.write.assert_called_once()
    assert (
        call.write(dyn_dynet.DynetPacket.set_channel_level_packet(1, 1, 0, 0.5).msg)
        in mock_gw.mock_writer.mock_calls
    )
    assert device.brightness == 0
