"""Tests for Dynalite lights."""
import pytest

import dynalite_devices_lib.const as dyn_const
from dynalite_devices_lib.dynet import DynetPacket

from .common import packet_notification


@pytest.mark.asyncio
async def test_light(mock_gateway):
    """Test a Dynalite channel that is a light."""
    name = "NAME"
    channel_name = "CHANNEL"
    [device] = mock_gateway.configure_dyn_dev(
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
    assert await mock_gateway.async_setup_dyn_dev()
    await mock_gateway.check_single_update(None)
    assert device.category == "light"
    assert device.name == f"{name} {channel_name}"
    assert device.unique_id == "dynalite_area_1_channel_1"
    assert device.available
    assert device.area_name == name
    assert device.get_master_area == name
    await device.async_turn_on()
    await mock_gateway.check_single_write(
        DynetPacket.set_channel_level_packet(1, 1, 1.0, 0.5)
    )
    await mock_gateway.check_single_update(device)
    assert device.brightness == 255
    await device.async_turn_on(brightness=51)
    await mock_gateway.check_single_write(
        DynetPacket.set_channel_level_packet(1, 1, 0.2, 0.5)
    )
    await mock_gateway.check_single_update(device)
    assert device.brightness == 51
    await device.async_turn_off()
    await mock_gateway.check_single_write(
        DynetPacket.set_channel_level_packet(1, 1, 0, 0.5)
    )
    await mock_gateway.check_single_update(device)
    assert device.brightness == 0
    # Now send commands
    packet_to_send = DynetPacket.set_channel_level_packet(1, 1, 1.0, 0.5)
    await mock_gateway.receive(packet_to_send)
    await mock_gateway.check_single_update(device)
    await mock_gateway.check_notifications(
        [packet_notification(packet_to_send.raw_msg)]
    )
    assert device.brightness == 255
    assert device.is_on

    packet_to_send = DynetPacket.set_channel_level_packet(1, 1, 0.2, 0.5)
    await mock_gateway.receive(packet_to_send)
    await mock_gateway.check_single_update(device)
    await mock_gateway.check_notifications(
        [packet_notification(packet_to_send.raw_msg)]
    )
    assert device.brightness == 51
    assert device.is_on

    packet_to_send = DynetPacket.report_channel_level_packet(1, 1, 0, 0)
    await mock_gateway.receive(packet_to_send)
    await mock_gateway.check_single_update(device)
    await mock_gateway.check_notifications(
        [packet_notification(packet_to_send.raw_msg)]
    )
    assert device.brightness == 0
    assert not device.is_on


@pytest.mark.asyncio
async def test_light_to_preset(mock_gateway):
    """Test a Dynalite channel that is a light."""
    name = "NAME"
    channel_name = "CHANNEL"
    [device, preset_1, preset_2, preset_3] = mock_gateway.configure_dyn_dev(
        {
            dyn_const.CONF_ACTIVE: False,
            dyn_const.CONF_AREA: {
                "1": {
                    dyn_const.CONF_NAME: name,
                    dyn_const.CONF_CHANNEL: {
                        "1": {
                            dyn_const.CONF_NAME: channel_name,
                            dyn_const.CONF_FADE: 0.5,
                        }
                    },
                    dyn_const.CONF_PRESET: {"2": {dyn_const.CONF_LEVEL: 0.2}},
                }
            },
        },
        4,
    )
    assert await mock_gateway.async_setup_dyn_dev()
    await mock_gateway.check_single_update(None)
    assert device.category == "light"
    assert device.name == f"{name} {channel_name}"
    assert device.unique_id == "dynalite_area_1_channel_1"
    assert device.available
    assert device.area_name == name
    assert device.get_master_area == name
    # Now send commands
    packet_to_send = DynetPacket.fade_area_channel_preset_packet(1, 1, 2, 0.0)
    await mock_gateway.receive(packet_to_send)
    await mock_gateway.check_single_update(device)
    await mock_gateway.check_notifications(
        [packet_notification(packet_to_send.raw_msg)]
    )
    assert device.brightness == 51
    assert device.is_on
    # check default preset on
    packet_to_send = DynetPacket.fade_area_channel_preset_packet(1, 1, 1, 0.0)
    await mock_gateway.receive(packet_to_send)
    await mock_gateway.check_single_update(device)
    await mock_gateway.check_notifications(
        [packet_notification(packet_to_send.raw_msg)]
    )
    assert device.brightness == 255
    assert device.is_on
    # check default preset off
    packet_to_send = DynetPacket.fade_area_channel_preset_packet(1, 1, 4, 0.0)
    await mock_gateway.receive(packet_to_send)
    await mock_gateway.check_single_update(device)
    await mock_gateway.check_notifications(
        [packet_notification(packet_to_send.raw_msg)]
    )
    assert device.brightness == 0
    assert not device.is_on


@pytest.mark.asyncio
async def test_light_init(mock_gateway):
    """Test a Dynalite light getting initial value."""
    [device, _, _] = mock_gateway.configure_dyn_dev(
        {
            dyn_const.CONF_ACTIVE: False,
            dyn_const.CONF_AREA: {
                "1": {
                    dyn_const.CONF_CHANNEL: {"1": {}},
                }
            },
        },
        3,
    )
    assert await mock_gateway.async_setup_dyn_dev()
    await mock_gateway.check_single_update(None)
    assert device.available
    # Now send commands
    device.init_level(135)
    assert device.brightness == 135
    assert device.is_on
    device.init_level(0)
    assert device.brightness == 0
    assert not device.is_on
    with pytest.raises(ValueError):
        device.init_level(-1)
    with pytest.raises(ValueError):
        device.init_level(256)
