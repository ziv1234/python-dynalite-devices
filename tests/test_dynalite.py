"""Tests for DynaliteDevices."""

import asyncio
from unittest.mock import patch

import pytest

import dynalite_devices_lib.const as dyn_const
from dynalite_devices_lib.dynet import DynetPacket
from dynalite_devices_lib.opcodes import SyncType

from .common import packet_notification


@pytest.mark.asyncio
async def test_dynalite_disconnection(mock_gateway):
    """Test a network disconnection."""
    devices = mock_gateway.configure_dyn_dev(
        {
            dyn_const.CONF_ACTIVE: False,
            dyn_const.CONF_AREA: {
                "1": {dyn_const.CONF_CHANNEL: {"1": {}, "2": {}}},
                "2": {dyn_const.CONF_TEMPLATE: dyn_const.CONF_ROOM},
                "3": {dyn_const.CONF_TEMPLATE: dyn_const.CONF_TIME_COVER},
            },
            dyn_const.CONF_PRESET: {"6": {}},
        },
        5,
    )
    assert await mock_gateway.async_setup_dyn_dev()
    await mock_gateway.check_single_update(None)
    for device in devices:
        assert device.available
    # Disconnect
    with patch("dynalite_devices_lib.dynalite.CONNECTION_RETRY_DELAY", 0.1):
        await mock_gateway.shutdown()
        await asyncio.sleep(0.05)
        await mock_gateway.check_single_update(None)
        for device in devices:
            assert not device.available
        await asyncio.sleep(0.2)
        await mock_gateway.async_setup_server()
        # Wait for reconnect
        await asyncio.sleep(0.2)
        await mock_gateway.check_single_update(None)
        for device in devices:
            assert device.available


@pytest.mark.asyncio
async def test_dynalite_connection_reset(mock_gateway):
    """Test a connection reset."""
    devices = mock_gateway.configure_dyn_dev(
        {
            dyn_const.CONF_ACTIVE: True,
            dyn_const.CONF_AREA: {
                "1": {dyn_const.CONF_CHANNEL: {"1": {}, "2": {}}},
                "2": {dyn_const.CONF_TEMPLATE: dyn_const.CONF_ROOM},
                "3": {dyn_const.CONF_TEMPLATE: dyn_const.CONF_TIME_COVER},
            },
            dyn_const.CONF_PRESET: {"6": {}},
        },
        5,
    )
    assert await mock_gateway.async_setup_dyn_dev()
    await mock_gateway.check_single_update(None)
    for device in devices:
        assert device.available
    # Disconnect
    with patch("dynalite_devices_lib.dynalite.CONNECTION_RETRY_DELAY", 0.1):
        # abort instead of close causes the connection to be reset
        writer = mock_gateway.writer
        writer.transport.abort()
        await mock_gateway.shutdown()
        await asyncio.sleep(0.05)
        await mock_gateway.check_single_update(None)
        for device in devices:
            assert not device.available
        await mock_gateway.async_setup_server()
        await asyncio.sleep(0.1)
        await mock_gateway.check_single_update(None)
        for device in devices:
            assert device.available


@pytest.mark.asyncio
async def test_dynalite_no_server(mock_gateway):
    """Test when no server is configured."""
    mock_gateway.configure_dyn_dev({dyn_const.CONF_PORT: 12333}, 0)
    assert not await mock_gateway.async_setup_dyn_dev()


@pytest.mark.asyncio
async def test_dynalite_shutdown_with_server_down(mock_gateway):
    """Test when shutting down while the server is down. Different flow in async_reset."""
    [device] = mock_gateway.configure_dyn_dev(
        {
            dyn_const.CONF_ACTIVE: False,
            dyn_const.CONF_AREA: {"1": {dyn_const.CONF_CHANNEL: {"1": {}}}},
            dyn_const.CONF_PRESET: {},
        },
    )
    assert await mock_gateway.async_setup_dyn_dev()
    await mock_gateway.check_single_update(None)
    assert device.available
    # Disconnect
    await mock_gateway.shutdown()
    await asyncio.sleep(0.1)
    await mock_gateway.check_single_update(None)
    assert not device.available


@pytest.mark.asyncio
async def test_dynalite_split_message(mock_gateway):
    """Test when a received message is split into two packets."""
    [device] = mock_gateway.configure_dyn_dev(
        {
            dyn_const.CONF_ACTIVE: False,
            dyn_const.CONF_AREA: {"1": {dyn_const.CONF_CHANNEL: {"1": {}}}},
            dyn_const.CONF_PRESET: {},
        },
    )
    assert await mock_gateway.async_setup_dyn_dev()
    await mock_gateway.check_single_update(None)
    assert not device.is_on
    packet = DynetPacket.set_channel_level_packet(1, 1, 1.0, 0.5)
    msg1 = packet.msg[0:5]
    msg2 = packet.msg[5:8]
    await mock_gateway.receive_message(msg1)
    await mock_gateway.receive_message(msg2)
    await mock_gateway.check_single_update(device)
    await mock_gateway.check_notifications([packet_notification(packet.raw_msg)])
    assert device.is_on


@pytest.mark.asyncio
async def test_dynalite_shift_message(mock_gateway):
    """Test when a received message arrives out of the normal 8bit pattern."""
    [device] = mock_gateway.configure_dyn_dev(
        {
            dyn_const.CONF_ACTIVE: False,
            dyn_const.CONF_AREA: {"1": {dyn_const.CONF_CHANNEL: {"1": {}}}},
            dyn_const.CONF_PRESET: {},
        },
    )
    assert await mock_gateway.async_setup_dyn_dev()
    await mock_gateway.check_single_update(None)
    assert not device.is_on
    packet = DynetPacket.set_channel_level_packet(1, 1, 1.0, 0.5)
    message = bytearray([3, 7, 12]) + packet.msg
    await mock_gateway.receive_message(message)
    await mock_gateway.check_single_update(device)
    await mock_gateway.check_notifications([packet_notification(packet.raw_msg)])
    assert device.is_on


@pytest.mark.asyncio
async def test_dynalite_debug_message(mock_gateway):
    """Test when a DEBUG message arrives."""
    [device] = mock_gateway.configure_dyn_dev(
        {
            dyn_const.CONF_ACTIVE: False,
            dyn_const.CONF_AREA: {"1": {dyn_const.CONF_CHANNEL: {"1": {}}}},
            dyn_const.CONF_PRESET: {},
        },
    )
    assert await mock_gateway.async_setup_dyn_dev()
    await mock_gateway.check_single_update(None)
    assert not device.is_on
    # putting a debug message + a device-on message half-way.
    # will verify that it will first read the debug message and then ignore other
    packet = DynetPacket.set_channel_level_packet(1, 1, 1.0, 0.5)
    int_message = [SyncType.DEBUG_MSG.value, 64, 65] + packet.raw_msg
    message = bytearray(int_message)
    await mock_gateway.receive_message(message)
    await mock_gateway.check_notifications([packet_notification(int_message[:8])])
    assert not device.is_on
    await mock_gateway.receive(packet)
    await mock_gateway.check_single_update(device)
    await mock_gateway.check_notifications([packet_notification(packet.raw_msg)])
    assert device.is_on


@pytest.mark.asyncio
async def test_dynalite_device_message(mock_gateway):
    """Test when a DEVICE message arrives."""
    [device] = mock_gateway.configure_dyn_dev(
        {
            dyn_const.CONF_ACTIVE: False,
            dyn_const.CONF_AREA: {"1": {dyn_const.CONF_CHANNEL: {"1": {}}}},
            dyn_const.CONF_PRESET: {},
        },
    )
    assert await mock_gateway.async_setup_dyn_dev()
    await mock_gateway.check_single_update(None)
    assert not device.is_on
    # putting a device message + a device-on message half-way.
    # will verify that it will first read the device message and then ignore other
    packet = DynetPacket.set_channel_level_packet(1, 1, 1.0, 0.5)
    int_message = [SyncType.DEVICE.value, 65, 66] + packet.raw_msg
    message = bytearray(int_message)
    await mock_gateway.receive_message(message)
    await mock_gateway.check_notifications([packet_notification(int_message[:8])])
    assert not device.is_on
    await mock_gateway.receive(packet)
    await mock_gateway.check_single_update(device)
    await mock_gateway.check_notifications([packet_notification(packet.raw_msg)])
    assert device.is_on


@pytest.mark.asyncio
async def test_dynalite_error_message(mock_gateway):
    """Test when a message arrives with the wrong checksum."""
    [device] = mock_gateway.configure_dyn_dev(
        {
            dyn_const.CONF_ACTIVE: False,
            dyn_const.CONF_AREA: {"1": {dyn_const.CONF_CHANNEL: {"1": {}}}},
            dyn_const.CONF_PRESET: {},
        },
    )
    assert await mock_gateway.async_setup_dyn_dev()
    await mock_gateway.check_single_update(None)
    assert not device.is_on
    packet = DynetPacket.set_channel_level_packet(1, 1, 1.0, 0.5)
    message = packet.msg
    message[7] += 1
    await mock_gateway.receive_message(message)
    assert not device.is_on
    packet = DynetPacket.set_channel_level_packet(1, 1, 1.0, 0.5)
    await mock_gateway.receive(packet)
    await mock_gateway.check_single_update(device)
    await mock_gateway.check_notifications([packet_notification(packet.raw_msg)])
    assert device.is_on


@pytest.mark.asyncio
async def test_dynalite_unhandled_message(mock_gateway):
    """Test when a message arrives that we know but don't handle."""
    [device] = mock_gateway.configure_dyn_dev(
        {
            dyn_const.CONF_ACTIVE: False,
            dyn_const.CONF_AREA: {"1": {dyn_const.CONF_CHANNEL: {"1": {}}}},
            dyn_const.CONF_PRESET: {},
        },
    )
    assert await mock_gateway.async_setup_dyn_dev()
    await mock_gateway.check_single_update(None)
    assert not device.is_on
    packet = DynetPacket(area=1, command=45, data=[0, 0, 0])
    await mock_gateway.receive(packet)
    await mock_gateway.check_notifications([packet_notification(packet.raw_msg)])
    assert not device.is_on
    packet = DynetPacket.set_channel_level_packet(1, 1, 1.0, 0.5)
    await mock_gateway.receive(packet)
    await mock_gateway.check_single_update(device)
    await mock_gateway.check_notifications([packet_notification(packet.raw_msg)])
    assert device.is_on


@pytest.mark.asyncio
async def test_dynalite_unknown_message(mock_gateway):
    """Test when a message arrives that we don't know."""
    [device] = mock_gateway.configure_dyn_dev(
        {
            dyn_const.CONF_ACTIVE: False,
            dyn_const.CONF_AREA: {"1": {dyn_const.CONF_CHANNEL: {"1": {}}}},
            dyn_const.CONF_PRESET: {},
        },
    )
    assert await mock_gateway.async_setup_dyn_dev()
    await mock_gateway.check_single_update(None)
    assert not device.is_on
    packet = DynetPacket(area=1, command=200, data=[0, 0, 0])
    await mock_gateway.receive(packet)
    await mock_gateway.check_notifications([packet_notification(packet.raw_msg)])
    assert not device.is_on
    packet = DynetPacket.set_channel_level_packet(1, 1, 1.0, 0.5)
    await mock_gateway.receive(packet)
    await mock_gateway.check_single_update(device)
    await mock_gateway.check_notifications([packet_notification(packet.raw_msg)])
    assert device.is_on


@pytest.mark.asyncio
async def test_dynalite_two_messages(mock_gateway):
    """Test when two messages arrive together."""
    devices = mock_gateway.configure_dyn_dev(
        {
            dyn_const.CONF_ACTIVE: False,
            dyn_const.CONF_AREA: {"1": {dyn_const.CONF_CHANNEL: {"1": {}, "2": {}}}},
            dyn_const.CONF_PRESET: {},
        },
        2,
    )
    assert await mock_gateway.async_setup_dyn_dev()
    await mock_gateway.check_single_update(None)
    for device in devices:
        assert not device.is_on
    packet1 = DynetPacket.set_channel_level_packet(1, 1, 1.0, 0.5)
    packet2 = DynetPacket.set_channel_level_packet(1, 2, 1.0, 0.5)
    await mock_gateway.receive_message(packet1.msg + packet2.msg)
    await mock_gateway.check_updates(devices)
    await mock_gateway.check_notifications(
        [packet_notification(packet1.raw_msg), packet_notification(packet2.raw_msg)]
    )
    for device in devices:
        assert device.is_on


@pytest.mark.asyncio
async def test_dynalite_write_message_throttle(mock_gateway_with_delay):
    """Test that when we send many messages, it throttles the messages."""
    mock_gateway_with_delay.configure_dyn_dev(
        {
            dyn_const.CONF_ACTIVE: True,
            dyn_const.CONF_AREA: {
                i: {dyn_const.CONF_CHANNEL: {1: {}}} for i in range(1, 26)
            },
            dyn_const.CONF_PRESET: {},
        },
        25,
    )
    assert await mock_gateway_with_delay.async_setup_dyn_dev()
    await mock_gateway_with_delay.check_single_update(None)
    await asyncio.sleep(1)  # should be roughly 5 messages
    assert 3 * 8 <= len(mock_gateway_with_delay.in_buffer) <= 7 * 8
