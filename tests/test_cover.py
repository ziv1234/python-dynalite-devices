"""Tests for Dynalite coverss."""

import asyncio

import dynalite_devices_lib.const as dyn_const
from dynalite_devices_lib.dynet import DynetPacket


async def test_cover_no_tilt(mock_gw):
    """Test the dynalite devices library."""
    name = "NAME"
    mock_gw.dyn_dev.configure(
        {
            dyn_const.CONF_ACTIVE: False,
            dyn_const.CONF_POLL_TIMER: 0.1,
            dyn_const.CONF_AREA: {
                "1": {
                    dyn_const.CONF_NAME: name,
                    dyn_const.CONF_TEMPLATE: dyn_const.CONF_TIME_COVER,
                    dyn_const.CONF_DURATION: 2,
                    dyn_const.CONF_OPEN_PRESET: 1,
                    dyn_const.CONF_CLOSE_PRESET: 2,
                    dyn_const.CONF_STOP_PRESET: 3,
                    dyn_const.CONF_CHANNEL_COVER: 4,
                    dyn_const.CONF_CHANNEL: {"4": {}},
                    dyn_const.CONF_PRESET: {"1": {}, "2": {}, "3": {}},
                }
            },
        }
    )
    [
        channel_device,
        open_device,
        close_device,
        stop_device,
        cover_device,
    ] = await mock_gw.async_setup(5)
    assert channel_device.category == "light"
    assert open_device.category == "switch"
    assert close_device.category == "switch"
    assert stop_device.category == "switch"
    assert cover_device.category == "cover"
    assert cover_device.name == name
    assert cover_device.unique_id == "dynalite_area_1_time_cover"
    assert cover_device.available
    assert cover_device.area_name == name
    assert cover_device.get_master_area == name
    assert not cover_device.has_tilt
    assert cover_device.device_class == dyn_const.DEFAULT_COVER_CLASS
    # It is closed. Let's open
    assert cover_device.is_closed
    await cover_device.async_open_cover()
    await mock_gw.check_single_write(DynetPacket.select_area_preset_packet(1, 1, 0))
    assert open_device.is_on
    assert not close_device.is_on
    assert not stop_device.is_on
    await asyncio.sleep(1)
    assert cover_device.is_opening
    assert 40 < cover_device.current_cover_position < 60
    await asyncio.sleep(1.5)
    assert (
        not cover_device.is_closed
        and not cover_device.is_opening
        and not cover_device.is_closing
    )
    assert cover_device.current_cover_position == 100
    # It is open. Now let's close
    await cover_device.async_close_cover()
    await mock_gw.check_single_write(DynetPacket.select_area_preset_packet(1, 2, 0))
    assert close_device.is_on
    assert not open_device.is_on
    assert not stop_device.is_on
    await asyncio.sleep(1)
    assert cover_device.is_closing
    assert 40 < cover_device.current_cover_position < 60
    # Stop halfway
    await cover_device.async_stop_cover()
    await mock_gw.check_single_write(DynetPacket.select_area_preset_packet(1, 3, 0))
    assert stop_device.is_on
    assert not open_device.is_on
    assert not close_device.is_on
    assert (
        not cover_device.is_closed
        and not cover_device.is_opening
        and not cover_device.is_closing
    )
    # And continue to full close
    await cover_device.async_close_cover()
    await mock_gw.check_single_write(DynetPacket.select_area_preset_packet(1, 2, 0))
    await asyncio.sleep(1.5)
    assert cover_device.is_closed
    assert cover_device.current_cover_position == 0
    # Now open it half-way
    await cover_device.async_set_cover_position(position=50)
    await asyncio.sleep(0.1)
    assert (
        not cover_device.is_closed
        and not cover_device.is_opening
        and not cover_device.is_closing
    )
    assert 40 < cover_device.current_cover_position < 60
    await cover_device.async_set_cover_position(position=25)
    await asyncio.sleep(0.1)
    assert (
        not cover_device.is_closed
        and not cover_device.is_opening
        and not cover_device.is_closing
    )
    assert 15 < cover_device.current_cover_position < 35
    await cover_device.async_open_cover()
    mock_gw.mock_writer.reset_mock()
    await cover_device.async_set_cover_position(
        position=cover_device.current_cover_position
    )
    await mock_gw.check_single_write(DynetPacket.select_area_preset_packet(1, 3, 0))
    assert (
        not cover_device.is_closed
        and not cover_device.is_opening
        and not cover_device.is_closing
    )
    # Now send commands
    await mock_gw.receive(DynetPacket.report_area_preset_packet(1, 1))
    assert cover_device.is_opening
    await mock_gw.receive(DynetPacket.report_area_preset_packet(1, 2))
    assert cover_device.is_closing
    await mock_gw.receive(DynetPacket.report_area_preset_packet(1, 3))
    assert not cover_device.is_closing and not cover_device.is_opening
    await mock_gw.receive(DynetPacket.report_area_preset_packet(1, 1))
    await asyncio.sleep(0.5)
    await mock_gw.receive(DynetPacket.report_channel_level_packet(1, 4, 0, 1))
    assert cover_device.is_closing
    await asyncio.sleep(0.5)
    await mock_gw.receive(DynetPacket.report_channel_level_packet(1, 4, 1, 0))
    assert cover_device.is_opening
    await mock_gw.receive(DynetPacket.stop_channel_fade_packet(1, 4))
    assert not cover_device.is_opening
    assert not cover_device.is_closing


async def test_cover_with_tilt(mock_gw):
    """Test the dynalite devices library."""
    name = "NAME"
    mock_gw.dyn_dev.configure(
        {
            dyn_const.CONF_ACTIVE: False,
            dyn_const.CONF_POLL_TIMER: 0.1,
            dyn_const.CONF_AREA: {
                "1": {
                    dyn_const.CONF_NAME: name,
                    dyn_const.CONF_TEMPLATE: dyn_const.CONF_TIME_COVER,
                    dyn_const.CONF_DEVICE_CLASS: "blind",
                    dyn_const.CONF_DURATION: 2,
                    dyn_const.CONF_TILT_TIME: 1,
                    dyn_const.CONF_OPEN_PRESET: 1,
                    dyn_const.CONF_CLOSE_PRESET: 2,
                    dyn_const.CONF_STOP_PRESET: 3,
                    dyn_const.CONF_CHANNEL_COVER: 4,
                }
            },
        }
    )
    [cover_device] = await mock_gw.async_setup()
    assert cover_device.category == "cover"
    assert cover_device.device_class == "blind"
    assert cover_device.has_tilt
    # It is closed. Let's open
    assert cover_device.is_closed
    assert cover_device.current_cover_tilt_position == 0
    asyncio.get_event_loop().create_task(cover_device.async_open_cover_tilt())
    await mock_gw.check_single_write(DynetPacket.select_area_preset_packet(1, 1, 0))
    await asyncio.sleep(0.5)
    assert cover_device.is_opening
    assert 40 < cover_device.current_cover_tilt_position < 60
    await asyncio.sleep(1.5)
    assert cover_device.current_cover_tilt_position == 100
    assert 40 < cover_device.current_cover_position < 60
    assert (
        not cover_device.is_closed
        and not cover_device.is_opening
        and not cover_device.is_closing
    )
    mock_gw.mock_writer.reset_mock()
    asyncio.get_event_loop().create_task(cover_device.async_open_cover_tilt())
    await mock_gw.check_writes([])
    # It is open. Now let's close
    mock_gw.mock_writer.reset_mock()
    asyncio.get_event_loop().create_task(cover_device.async_close_cover_tilt())
    await mock_gw.check_single_write(DynetPacket.select_area_preset_packet(1, 2, 0))
    await asyncio.sleep(0.5)
    assert cover_device.is_closing
    assert 40 < cover_device.current_cover_tilt_position < 60
    # Stop halfway
    await cover_device.async_stop_cover_tilt()
    await mock_gw.check_single_write(DynetPacket.select_area_preset_packet(1, 3, 0))
    assert 40 < cover_device.current_cover_tilt_position < 60
    assert (
        not cover_device.is_closed
        and not cover_device.is_opening
        and not cover_device.is_closing
    )
    # And continue to full close
    await cover_device.async_close_cover()
    await mock_gw.check_single_write(DynetPacket.select_area_preset_packet(1, 2, 0))
    await asyncio.sleep(1)
    assert cover_device.is_closed
    assert cover_device.current_cover_tilt_position == 0
    mock_gw.mock_writer.reset_mock()
    asyncio.get_event_loop().create_task(cover_device.async_close_cover_tilt())
    await mock_gw.check_writes([])
    # Now open it half-way
    await cover_device.async_set_cover_tilt_position(tilt_position=50)
    await asyncio.sleep(3)
    assert (
        not cover_device.is_closed
        and not cover_device.is_opening
        and not cover_device.is_closing
    )
    assert 40 < cover_device.current_cover_tilt_position < 60
