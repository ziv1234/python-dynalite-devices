"""Tests for DynaliteDevices."""

import pytest

import dynalite_devices_lib.const as dyn_const
from dynalite_devices_lib.dynet import DynetPacket


@pytest.mark.asyncio
async def test_empty_dynalite_devices(mock_gateway):
    """Test the dynalite devices library with no devices."""
    mock_gateway.configure_dyn_dev(
        {
            dyn_const.CONF_ACTIVE: False,
            dyn_const.CONF_AREA: {"1": {dyn_const.CONF_NO_DEFAULT: True}},
        },
        0,
    )
    assert await mock_gateway.async_setup_dyn_dev()
    await mock_gateway.check_writes([])


@pytest.mark.asyncio
@pytest.mark.parametrize("active", [False, dyn_const.CONF_ACTIVE_INIT, True])
async def test_dynalite_devices_active(mock_gateway, active):
    """Test with active set to ON."""
    mock_gateway.configure_dyn_dev(
        {
            dyn_const.CONF_ACTIVE: active,
            dyn_const.CONF_AREA: {"1": {dyn_const.CONF_CHANNEL: {"1": {}, "2": {}}}},
            dyn_const.CONF_PRESET: {"1": {}},
        },
        3,
    )
    assert await mock_gateway.async_setup_dyn_dev()
    if active is not False:
        await mock_gateway.check_writes(
            [
                DynetPacket.request_channel_level_packet(1, 1),
                DynetPacket.request_channel_level_packet(1, 2),
                DynetPacket.request_area_preset_packet(1),
            ]
        )
    else:
        await mock_gateway.check_writes([])
    await mock_gateway.receive(DynetPacket.report_area_preset_packet(1, 1))
    if active is True:
        await mock_gateway.check_writes(
            [
                DynetPacket.request_channel_level_packet(1, 1),
                DynetPacket.request_channel_level_packet(1, 2),
            ]
        )
    else:
        await mock_gateway.check_writes([])


@pytest.mark.asyncio
async def test_dynalite_devices_reconfig(mock_gateway):
    """Test reconfiguration and that no devices are registered again."""
    config = {
        dyn_const.CONF_ACTIVE: False,
        dyn_const.CONF_AREA: {
            "1": {dyn_const.CONF_CHANNEL: {"1": {}, "2": {}}},
            "2": {dyn_const.CONF_TEMPLATE: dyn_const.CONF_ROOM},
            "4": {dyn_const.CONF_TEMPLATE: dyn_const.CONF_TIME_COVER},
        },
        dyn_const.CONF_PRESET: {"1": {}},
    }
    mock_gateway.configure_dyn_dev(config, 5)
    assert await mock_gateway.async_setup_dyn_dev()
    mock_gateway.configure_dyn_dev(config, 0)


@pytest.mark.asyncio
async def test_dynalite_devices_auto_discover_on(mock_gateway):
    """Test autodiscover ON."""
    config = {
        dyn_const.CONF_ACTIVE: False,
        dyn_const.CONF_AUTO_DISCOVER: True,
        dyn_const.CONF_AREA: {},
    }
    mock_gateway.configure_dyn_dev(config, 0)
    assert await mock_gateway.async_setup_dyn_dev()
    func = mock_gateway.new_dev_func
    func.reset_mock()
    await mock_gateway.receive(DynetPacket.report_area_preset_packet(1, 1))
    func.assert_called_once()
    devices = func.mock_calls[0][1][0]
    assert len(devices) == 1
    assert devices[0].unique_id == "dynalite_area_1_preset_1"
    func.reset_mock()
    await mock_gateway.receive(DynetPacket.set_channel_level_packet(2, 3, 0, 0))
    func.assert_called_once()
    devices = func.mock_calls[0][1][0]
    assert len(devices) == 1
    assert devices[0].unique_id == "dynalite_area_2_channel_3"


@pytest.mark.asyncio
async def test_dynalite_devices_auto_discover_off(mock_gateway):
    """Test autodiscover OFF."""
    config = {
        dyn_const.CONF_ACTIVE: False,
        dyn_const.CONF_AUTO_DISCOVER: False,
        dyn_const.CONF_AREA: {},
    }
    mock_gateway.configure_dyn_dev(config, 0)
    assert await mock_gateway.async_setup_dyn_dev()
    func = mock_gateway.new_dev_func
    func.reset_mock()
    await mock_gateway.receive(DynetPacket.report_area_preset_packet(1, 1))
    func.assert_not_called()
    await mock_gateway.receive(DynetPacket.set_channel_level_packet(2, 3, 0, 0))
    func.assert_not_called()


@pytest.mark.asyncio
async def test_dynalite_devices_auto_discover_template(mock_gateway):
    """Test auto discover ON when running into a template that shouldn't show the device."""
    config = {
        dyn_const.CONF_ACTIVE: False,
        dyn_const.CONF_AUTO_DISCOVER: True,
        dyn_const.CONF_AREA: {
            1: {dyn_const.CONF_TEMPLATE: dyn_const.CONF_ROOM},
            2: {dyn_const.CONF_TEMPLATE: dyn_const.CONF_TIME_COVER},
        },
    }
    mock_gateway.configure_dyn_dev(config, 2)
    assert await mock_gateway.async_setup_dyn_dev()
    func = mock_gateway.new_dev_func
    func.reset_mock()
    await mock_gateway.receive(DynetPacket.report_area_preset_packet(1, 2))
    func.assert_not_called()
    await mock_gateway.receive(DynetPacket.set_channel_level_packet(2, 3, 0, 0))
    func.assert_not_called()


@pytest.mark.asyncio
async def test_dynalite_devices_unknown_channel_type(mock_gateway):
    """Test when config has a wrong channel type."""
    mock_gateway.configure_dyn_dev(
        {
            dyn_const.CONF_ACTIVE: False,
            dyn_const.CONF_AREA: {
                "1": {
                    dyn_const.CONF_NO_DEFAULT: True,
                    dyn_const.CONF_CHANNEL: {"1": {dyn_const.CONF_CHANNEL_TYPE: "aaa"}},
                }
            },
        },
        0,
    )
    assert await mock_gateway.async_setup_dyn_dev()
    await mock_gateway.check_writes([])


@pytest.mark.asyncio
async def test_dynalite_devices_area_override(mock_gateway):
    """Test that area overrides work."""
    name = "aaa"
    override_name = "bbb"
    [device] = mock_gateway.configure_dyn_dev(
        {
            dyn_const.CONF_ACTIVE: False,
            dyn_const.CONF_AREA: {
                "1": {
                    dyn_const.CONF_NAME: name,
                    dyn_const.CONF_AREA_OVERRIDE: override_name,
                    dyn_const.CONF_NO_DEFAULT: True,
                    dyn_const.CONF_CHANNEL: {"1": {}},
                }
            },
        },
        1,
    )
    assert device.area_name == name
    assert device.get_master_area == override_name


@pytest.mark.asyncio
async def test_dynalite_devices_preset_collision(mock_gateway):
    """Test that a preset defined both in the defaults and in the area ."""
    name = "aaa"
    default_name = "bbb"
    devices = mock_gateway.configure_dyn_dev(
        {
            dyn_const.CONF_ACTIVE: False,
            dyn_const.CONF_AREA: {
                "1": {
                    dyn_const.CONF_PRESET: {"1": {dyn_const.CONF_NAME: name}},
                },
                "2": {},
            },
            dyn_const.CONF_PRESET: {
                "1": {dyn_const.CONF_NAME: default_name},
                "2": {},
            },
        },
        4,
    )
    assert devices[0].name == "Area 1 " + name
    assert devices[2].name == "Area 2 " + default_name


@pytest.mark.asyncio
async def test_dynalite_devices_reconfig_with_missing(mock_gateway):
    """Test reconfiguration with fewer devices and see that they are not available."""
    [device] = mock_gateway.configure_dyn_dev(
        {
            dyn_const.CONF_ACTIVE: False,
            dyn_const.CONF_AREA: {"1": {dyn_const.CONF_CHANNEL: {"1": {}}}},
            dyn_const.CONF_PRESET: {},
        },
        1,
    )
    assert await mock_gateway.async_setup_dyn_dev()
    assert device.available
    assert device.name == "Area 1 Channel 1"
    assert device.unique_id == "dynalite_area_1_channel_1"
    assert device.area_name == "Area 1"
    assert device.get_master_area == "Area 1"
    mock_gateway.configure_dyn_dev(
        {
            dyn_const.CONF_ACTIVE: False,
            dyn_const.CONF_AREA: {},
            dyn_const.CONF_PRESET: {},
        },
        0,
    )
    assert not device.available


@pytest.mark.asyncio
async def test_dynalite_devices_default_fade(mock_gateway):
    """Test that default fade works correctly."""
    [channel_device, preset_device] = mock_gateway.configure_dyn_dev(
        {
            dyn_const.CONF_ACTIVE: False,
            dyn_const.CONF_DEFAULT: {dyn_const.CONF_FADE: 0.5},
            dyn_const.CONF_AREA: {"1": {dyn_const.CONF_CHANNEL: {"1": {}}}},
            dyn_const.CONF_PRESET: {"1": {}},
        },
        2,
    )
    assert await mock_gateway.async_setup_dyn_dev()
    await mock_gateway.check_writes([])
    await channel_device.async_turn_on()
    await mock_gateway.check_single_write(
        DynetPacket.set_channel_level_packet(1, 1, 1.0, 0.5)
    )
    await preset_device.async_turn_on()
    await mock_gateway.check_single_write(
        DynetPacket.select_area_preset_packet(1, 1, 0.5)
    )
