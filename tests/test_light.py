"""Tests for Dynalite lights."""
import pytest

import dynalite_devices_lib.const as dyn_const
import dynalite_devices_lib.dynet as dyn_dynet

pytestmark = pytest.mark.asyncio


async def test_light(mock_gateway):
    """Test the dynalite devices library."""
    name = "NAME"
    channel_name = "CHANNEL"
    mock_gateway.configure_dyn_dev(
        {
            dyn_const.CONF_ACTIVE: False,
            dyn_const.CONF_AREA: {
                "1": {
                    dyn_const.CONF_NAME: name,
                    dyn_const.CONF_NO_DEFAULT: True,
                    dyn_const.CONF_CHANNEL: {
                        "1": {
                            dyn_const.CONF_NAME: channel_name,
                            dyn_const.CONF_FADE: 0.5,
                        }
                    },
                }
            },
        }
    )
    [device] = await mock_gateway.async_setup_dyn_dev()
    assert device.category == "light"
    assert device.name == f"{name} {channel_name}"
    assert device.unique_id == "dynalite_area_1_channel_1"
    assert device.available
    assert device.area_name == name
    assert device.get_master_area == name
    await device.async_turn_on()
    await mock_gateway.check_single_write(
        dyn_dynet.DynetPacket.set_channel_level_packet(1, 1, 1.0, 0.5)
    )
    assert device.brightness == 255
    await device.async_turn_on(brightness=51)
    await mock_gateway.check_single_write(
        dyn_dynet.DynetPacket.set_channel_level_packet(1, 1, 0.2, 0.5)
    )
    assert device.brightness == 51
    await device.async_turn_off()
    await mock_gateway.check_single_write(
        dyn_dynet.DynetPacket.set_channel_level_packet(1, 1, 0, 0.5)
    )
    assert device.brightness == 0
    # Now send commands
    await mock_gateway.receive(
        dyn_dynet.DynetPacket.set_channel_level_packet(1, 1, 1.0, 0.5)
    )
    assert device.brightness == 255
    assert device.is_on
    await mock_gateway.receive(
        dyn_dynet.DynetPacket.set_channel_level_packet(1, 1, 0.2, 0.5)
    )
    assert device.brightness == 51
    assert device.is_on
    await mock_gateway.receive(
        dyn_dynet.DynetPacket.report_channel_level_packet(1, 1, 0, 0)
    )
    assert device.brightness == 0
    assert not device.is_on
