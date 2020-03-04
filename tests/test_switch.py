"""Tests for DynaliteDevices."""
import asyncio

from asynctest import call
import dynalite_devices_lib.const as dyn_const
import dynalite_devices_lib.dynet as dyn_dynet


async def test_preset_switch(mock_gw):
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
                        "4": {dyn_const.CONF_FADE: 0.7},
                    },
                }
            },
        }
    )
    await mock_gw.async_setup()
    mock_gw.new_dev_func.assert_called_once()
    assert len(mock_gw.new_dev_func.mock_calls[0][1][0]) == 2
    device1 = mock_gw.new_dev_func.mock_calls[0][1][0][0]
    device4 = mock_gw.new_dev_func.mock_calls[0][1][0][1]
    assert device1.category == "switch"
    assert device4.category == "switch"
    assert device1.name == f"{name} {preset_name}"
    assert device4.name == f"{name} Preset 4"
    assert device1.unique_id == "dynalite_area_1_preset_1"
    await device1.async_turn_on()
    await asyncio.sleep(0.1)
    mock_gw.mock_writer.write.assert_called_once()
    assert (
        call.write(dyn_dynet.DynetPacket.select_area_preset_packet(1, 1, 0.5).msg)
        in mock_gw.mock_writer.mock_calls
    )
    assert device1.is_on
    assert not device4.is_on
    mock_gw.mock_writer.reset_mock()
    await device4.async_turn_on()
    await asyncio.sleep(0.1)
    mock_gw.mock_writer.write.assert_called_once()
    assert (
        call.write(dyn_dynet.DynetPacket.select_area_preset_packet(1, 4, 0.7).msg)
        in mock_gw.mock_writer.mock_calls
    )
    assert device4.is_on
    assert not device1.is_on
    mock_gw.mock_writer.reset_mock()
    await device4.async_turn_off()
    await asyncio.sleep(0.1)
    mock_gw.mock_writer.write.assert_not_called()
    assert not device4.is_on
    assert not device1.is_on


async def test_channel_switch(mock_gw):
    """Test the dynalite devices library."""
    name = "NAME"
    mock_gw.dyn_dev.configure(
        {
            dyn_const.CONF_ACTIVE: False,
            dyn_const.CONF_AREA: {
                "1": {
                    dyn_const.CONF_NAME: name,
                    dyn_const.CONF_NO_DEFAULT: True,
                    dyn_const.CONF_CHANNEL: {
                        "1": {
                            dyn_const.CONF_FADE: 0.5,
                            dyn_const.CONF_CHANNEL_TYPE: "switch",
                        }
                    },
                }
            },
        }
    )
    await mock_gw.async_setup()
    await asyncio.sleep(0.1)
    mock_gw.new_dev_func.assert_called_once()
    assert len(mock_gw.new_dev_func.mock_calls[0][1][0]) == 1
    device = mock_gw.new_dev_func.mock_calls[0][1][0][0]
    assert device.category == "switch"
    assert device.name == f"{name} Channel 1"
    assert device.unique_id == "dynalite_area_1_channel_1"
    assert device.available
    assert device.area_name == name
    assert device.get_master_area == name
    await device.async_turn_on()
    await asyncio.sleep(0.1)
    mock_gw.mock_writer.write.assert_called_once()
    assert (
        call.write(dyn_dynet.DynetPacket.set_channel_level_packet(1, 1, 1.0, 0.5).msg)
        in mock_gw.mock_writer.mock_calls
    )
    assert device.is_on
    mock_gw.mock_writer.reset_mock()
    await device.async_turn_off()
    await asyncio.sleep(0.1)
    mock_gw.mock_writer.write.assert_called_once()
    assert (
        call.write(dyn_dynet.DynetPacket.set_channel_level_packet(1, 1, 0, 0.5).msg)
        in mock_gw.mock_writer.mock_calls
    )
    assert not device.is_on
