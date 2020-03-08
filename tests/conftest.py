"""Fixtures for the Dynalite tests."""
import asyncio

from asynctest import Mock, patch
import pytest

import dynalite_devices_lib.const as dyn_const
from dynalite_devices_lib.dynalite_devices import DynaliteDevices

pytestmark = pytest.mark.asyncio


class MockGateway:
    """Class to mock a TCP gateway."""

    def __init__(self, request, message_delay_zero):
        """Initialize the class."""
        request.addfinalizer(self.fin)
        self.reader = None
        self.writer = None
        self.server = None
        self.in_buffer = bytearray()
        self.new_dev_func = Mock()
        self.update_dev_func = Mock()
        if message_delay_zero:
            with patch("dynalite_devices_lib.dynalite.MESSAGE_DELAY", 0):
                self.dyn_dev = DynaliteDevices(
                    new_device_func=self.new_dev_func,
                    update_device_func=self.update_dev_func,
                )
        else:
            self.dyn_dev = DynaliteDevices(
                new_device_func=self.new_dev_func,
                update_device_func=self.update_dev_func,
            )

    async def run_server(self):
        """Run the actual server."""

        async def handle_connection(reader, writer):
            """Run a single session. Assumes only one for tests."""
            assert not self.reader and not self.writer
            self.reader = reader
            self.writer = writer
            while not reader.at_eof():
                data = await reader.read(100)
                addr = writer.get_extra_info("peername")
                dyn_const.LOGGER.debug(
                    "Received message from %s - %s", addr, [int(byte) for byte in data]
                )
                for byte in data:
                    self.in_buffer.append(byte)
            self.reader = self.writer = None

        self.server = await asyncio.start_server(handle_connection, "127.0.0.1", 12345)
        addr = self.server.sockets[0].getsockname()
        dyn_const.LOGGER.debug("Serving on %s", addr)
        async with self.server:
            await self.server.serve_forever()

    async def async_setup_server(self):
        """Start the server."""
        asyncio.get_event_loop().create_task(self.run_server())
        await asyncio.sleep(0.01)

    async def check_writes(self, packets):
        """Check that a set of packets was written."""
        await asyncio.sleep(0.01)
        assert len(self.in_buffer) == len(packets) * 8
        received = [self.in_buffer[i * 8 : i * 8 + 8] for i in range(0, len(packets))]
        for packet in packets:
            assert packet.msg in received
        self.reset()

    async def check_single_write(self, packet):
        """Check that there was only a single packet written."""
        await self.check_writes([packet])

    async def receive_message(self, message):
        """Fake a received message."""
        self.writer.write(message)
        await self.writer.drain()
        await asyncio.sleep(0.01)

    async def receive(self, packet):
        """Fake a received packet."""
        await self.receive_message(packet.msg)

    def configure_dyn_dev(self, config, num_devices=1):
        """Configure the DynaliteDevices."""
        self.new_dev_func.reset_mock()
        self.dyn_dev.configure(config)
        if num_devices == 0:
            self.new_dev_func.assert_not_called()
            return None
        self.new_dev_func.assert_called_once()
        assert len(self.new_dev_func.mock_calls[0][1][0]) == num_devices
        return self.new_dev_func.mock_calls[0][1][0]

    async def async_setup_dyn_dev(self):
        """Set up the internal DynaliteDevices."""
        return await self.dyn_dev.async_setup()

    def reset(self):
        """Reset the in buffer."""
        self.in_buffer = bytearray()

    def reset_connection(self):
        """Reset the current connection."""
        if self.writer:
            self.writer.close()

    async def shutdown(self):
        """Shut down the server."""
        self.reset_connection()
        self.server.close()
        await self.server.wait_closed()

    async def async_fin(self):
        """Shut the gateway down."""
        await self.shutdown()
        await self.dyn_dev.async_reset()

    def fin(self):
        """Run shutdown async."""
        asyncio.get_event_loop().run_until_complete(self.async_fin())


@pytest.fixture()
async def mock_gateway(request):
    """Mock for a TCP gateway. Removes throttling by Dynet."""
    gateway = MockGateway(request, True)
    await gateway.async_setup_server()
    return gateway


@pytest.fixture()
async def mock_gateway_with_delay(request):
    """Mock for a TCP gateway. Keeps throttling by Dynet."""
    gateway = MockGateway(request, False)
    await gateway.async_setup_server()
    return gateway
