"""Fixtures for the Dynalite tests."""
import asyncio

from asynctest import Mock
import pytest

import dynalite_devices_lib.const as dyn_const
from dynalite_devices_lib.dynalite_devices import DynaliteDevices

pytestmark = pytest.mark.asyncio


class MockGateway:
    """Class to mock a TCP gateway."""

    def __init__(self):
        """Initialize the class."""
        self.reader = None
        self.writer = None
        self.server = None
        self.in_buffer = bytearray()
        self.dyn_dev = MockDynDev()

    async def run_server(self):
        """Run the actual server."""

        async def handle_connection(reader, writer):
            assert not self.reader and not self.writer
            dyn_const.LOGGER.error("XXX here")
            self.reader = reader
            self.writer = writer
            while not reader.at_eof():
                data = await reader.read(100)
                addr = writer.get_extra_info("peername")
                dyn_const.LOGGER.error(
                    "Received message from %s - %s", addr, [int(byte) for byte in data]
                )
                for byte in data:
                    self.in_buffer.append(byte)

        self.server = await asyncio.start_server(handle_connection, "127.0.0.1", 12345)
        addr = self.server.sockets[0].getsockname()
        dyn_const.LOGGER.error("Serving on %s", addr)
        async with self.server:
            await self.server.serve_forever()

    async def async_setup_server(self):
        """Start the server."""
        asyncio.get_event_loop().create_task(self.run_server())
        await asyncio.sleep(0.01)

    async def check_writes(self, packets):
        """Check that the set of writes was issued."""
        await asyncio.sleep(0.01)
        assert len(self.in_buffer) == len(packets) * 8
        received = [self.in_buffer[i * 8 : i * 8 + 8] for i in range(0, len(packets))]
        for packet in packets:
            assert packet.msg in received
        self.reset()

    async def check_single_write(self, packet):
        """Check that there was only a single write issued."""
        await self.check_writes([packet])

    async def receive(self, packet):
        """Fake a received packet."""
        self.writer.write(packet.msg)
        await self.writer.drain()
        await asyncio.sleep(0.01)

    def configure_dyn_dev(self, config):
        """Configure the DynaliteDevices."""
        self.dyn_dev.dyn_dev.configure(config)

    async def async_setup_dyn_dev(self, num_devices=1, message_delay_zero=True):
        """Set up the internal DynaliteDevices."""
        return await self.dyn_dev.async_setup(num_devices, message_delay_zero)

    def reset(self):
        """Reset the in buffer."""
        self.in_buffer = bytearray()


class MockDynDev:
    """Class for a mock DynaliteDevices object."""

    def __init__(self):
        """Initialize the Mock."""
        self.new_dev_func = Mock()
        self.update_dev_func = Mock()
        self.dyn_dev = DynaliteDevices(
            new_device_func=self.new_dev_func, update_device_func=self.update_dev_func
        )
        self.area = None

    async def async_setup(self, num_devices, message_delay_zero):
        """Set up and mock the writer."""
        if message_delay_zero:
            self.dyn_dev.dynalite.message_delay = 0
        await self.dyn_dev.async_setup()
        if num_devices == 0:
            self.new_dev_func.assert_not_called()
            return None
        self.new_dev_func.assert_called_once()
        assert len(self.new_dev_func.mock_calls[0][1][0]) == num_devices
        await asyncio.sleep(0.01)
        return self.new_dev_func.mock_calls[0][1][0]


@pytest.fixture()
async def mock_gateway(request):
    """Mock for a TCP gateway."""

    async def async_fin():
        """Shut the gateway down."""
        dyn_const.LOGGER.error("AAA - here")
        # gateway.writer.close() XXX
        gateway.server.close()
        await gateway.server.wait_closed()

    def fin():
        """Run shutdown async."""
        asyncio.get_event_loop().run_until_complete(async_fin())

    request.addfinalizer(fin)
    gateway = MockGateway()
    await gateway.async_setup_server()
    return gateway
