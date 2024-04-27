"""Tests for Dynalite switches."""
import asyncio

import pytest

import dynalite_devices_lib.const as dyn_const
from dynalite_devices_lib.dynet import DynetPacket

from .common import packet_notification, preset_notification


@pytest.mark.asyncio
async def test_preset_switch(mock_gateway):
    """Test a Dynalite preset."""
    name = "NAME"
    preset_name = "PRESET"
    [device1, device4] = mock_gateway.configure_dyn_dev(
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
        },
        2,
    )
    assert await mock_gateway.async_setup_dyn_dev()
    await mock_gateway.check_single_update(None)
    assert device1.category == "switch"
    assert device4.category == "switch"
    assert device1.name == f"{name} {preset_name}"
    assert device4.name == f"{name} Preset 4"
    assert device1.unique_id == "dynalite_area_1_preset_1"
    await device1.async_turn_on()
    await mock_gateway.check_single_write(
        DynetPacket.select_area_preset_packet(1, 1, 0.5)
    )
    await mock_gateway.check_updates([device1, device4])
    await mock_gateway.check_notifications([preset_notification(1, 1)])
    assert device1.is_on
    assert not device4.is_on
    await device4.async_turn_on()
    await asyncio.sleep(0.1)
    await mock_gateway.check_single_write(
        DynetPacket.select_area_preset_packet(1, 4, 0.7)
    )
    await mock_gateway.check_updates([device1, device4])
    await mock_gateway.check_notifications([preset_notification(1, 4)])
    assert device4.is_on
    assert not device1.is_on
    await device4.async_turn_off()
    await asyncio.sleep(0.1)
    await mock_gateway.check_writes([])
    assert not device4.is_on
    assert not device1.is_on
    packet_to_send = DynetPacket.select_area_preset_packet(1, 1, 0.2)
    await mock_gateway.receive(packet_to_send)
    await mock_gateway.check_updates([device1, device4])
    await mock_gateway.check_notifications(
        [packet_notification(packet_to_send.raw_msg), preset_notification(1, 1)]
    )
    assert not device4.is_on
    assert device1.is_on
    packet_to_send = DynetPacket.report_area_preset_packet(1, 4)
    await mock_gateway.receive(packet_to_send)
    await mock_gateway.check_updates([device1, device4])
    await mock_gateway.check_notifications(
        [packet_notification(packet_to_send.raw_msg), preset_notification(1, 4)]
    )
    assert device4.is_on
    assert not device1.is_on
    device1.init_level(2)
    assert device1.is_on
    device1.init_level(0)
    assert not device1.is_on


@pytest.mark.asyncio
async def test_channel_switch(mock_gateway):
    """Test a Dynalite channel that is a switch."""
    name = "NAME"
    [device] = mock_gateway.configure_dyn_dev(
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
    assert await mock_gateway.async_setup_dyn_dev()
    await mock_gateway.check_single_update(None)
    assert device.category == "switch"
    assert device.name == f"{name} Channel 1"
    assert device.unique_id == "dynalite_area_1_channel_1"
    assert device.available
    assert device.area_name == name
    assert device.get_master_area == name
    await device.async_turn_on()
    await mock_gateway.check_single_update(device)
    await mock_gateway.check_single_write(
        DynetPacket.set_channel_level_packet(1, 1, 1.0, 0.5)
    )
    assert device.is_on
    await device.async_turn_off()
    await mock_gateway.check_single_update(device)
    await mock_gateway.check_single_write(
        DynetPacket.set_channel_level_packet(1, 1, 0.0, 0.5)
    )
    assert not device.is_on
    device.init_level(2)
    assert device.is_on
    device.init_level(0)
    assert not device.is_on
    with pytest.raises(ValueError):
        device.init_level(-1)


@pytest.mark.asyncio
async def test_room_switch(mock_gateway):
    """Test a room switch with two presets."""
    name = "NAME"
    [on_device, off_device, room_device] = mock_gateway.configure_dyn_dev(
        {
            dyn_const.CONF_ACTIVE: False,
            dyn_const.CONF_AREA: {
                "1": {
                    dyn_const.CONF_NAME: name,
                    dyn_const.CONF_TEMPLATE: dyn_const.CONF_ROOM,
                    dyn_const.CONF_PRESET: {"1": {}, "4": {}},
                }
            },
        },
        3,
    )
    assert await mock_gateway.async_setup_dyn_dev()
    await mock_gateway.check_single_update(None)
    for device in [on_device, off_device, room_device]:
        assert device.category == "switch"
    assert room_device.name == name
    assert device.unique_id == "dynalite_area_1_room_switch"
    assert device.available
    await room_device.async_turn_on()
    await mock_gateway.check_updates([on_device, off_device, room_device])
    await mock_gateway.check_notifications([preset_notification(1, 1)])
    await mock_gateway.check_single_write(
        DynetPacket.select_area_preset_packet(1, 1, 0)
    )
    assert room_device.is_on
    assert on_device.is_on
    assert not off_device.is_on
    await room_device.async_turn_off()
    await mock_gateway.check_updates([on_device, off_device, room_device], True)
    await mock_gateway.check_notifications([preset_notification(1, 4)])
    await mock_gateway.check_single_write(
        DynetPacket.select_area_preset_packet(1, 4, 0)
    )
    assert not room_device.is_on
    assert not on_device.is_on
    assert off_device.is_on
    await on_device.async_turn_on()
    await mock_gateway.check_updates([on_device, off_device, room_device], True)
    await mock_gateway.check_notifications([preset_notification(1, 1)])
    await mock_gateway.check_single_write(
        DynetPacket.select_area_preset_packet(1, 1, 0)
    )
    assert room_device.is_on
    assert on_device.is_on
    assert not off_device.is_on
    await off_device.async_turn_on()
    await mock_gateway.check_updates([on_device, off_device, room_device], True)
    await mock_gateway.check_notifications([preset_notification(1, 4)])
    await mock_gateway.check_single_write(
        DynetPacket.select_area_preset_packet(1, 4, 0)
    )
    assert not room_device.is_on
    assert not on_device.is_on
    assert off_device.is_on
    room_device.init_level(2)
    assert room_device.is_on
    assert on_device.is_on
    assert not off_device.is_on
    room_device.init_level(0)
    assert not room_device.is_on
    assert not on_device.is_on
    assert off_device.is_on


@pytest.mark.asyncio
async def test_trigger_switch(mock_gateway):
    """Test a switch that is a single trigger."""
    name = "NAME"
    [trigger_device] = mock_gateway.configure_dyn_dev(
        {
            dyn_const.CONF_ACTIVE: False,
            dyn_const.CONF_AREA: {
                "1": {
                    dyn_const.CONF_NAME: name,
                    dyn_const.CONF_TEMPLATE: dyn_const.CONF_TRIGGER,
                }
            },
        },
        1,
    )
    assert await mock_gateway.async_setup_dyn_dev()
    await mock_gateway.check_single_update(None)
    assert trigger_device.category == "switch"
    assert trigger_device.name == name
    assert trigger_device.unique_id == "dynalite_area_1_preset_1"
    assert trigger_device.available
    await trigger_device.async_turn_on()
    await mock_gateway.check_single_write(
        DynetPacket.select_area_preset_packet(1, 1, 0)
    )
    await mock_gateway.check_single_update(trigger_device)
    await mock_gateway.check_notifications([preset_notification(1, 1)])
    assert trigger_device.is_on
    packet_to_send = DynetPacket.report_area_preset_packet(1, 4)
    await mock_gateway.receive(packet_to_send)
    await mock_gateway.check_single_update(trigger_device)
    await mock_gateway.check_notifications(
        [packet_notification(packet_to_send.raw_msg), preset_notification(1, 4)]
    )
    assert not trigger_device.is_on
