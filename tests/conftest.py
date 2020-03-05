"""Fixtures for the Dynalite tests."""
import asyncio

from asynctest import Mock, call, patch
import dynalite_devices_lib.const as dyn_const
from dynalite_devices_lib.dynalite_devices import DynaliteDevices
import dynalite_devices_lib.event as dyn_event
import pytest


class MockDynDev:
    """Class for a mock DynaliteDevices object."""

    def __init__(self):
        """Initialize the Mock."""
        self.mock_writer = Mock()
        self.new_dev_func = Mock()
        self.update_dev_func = Mock()
        self.dyn_dev = DynaliteDevices(
            new_device_func=self.new_dev_func, update_device_func=self.update_dev_func
        )
        self.area = None

    async def async_setup(self, num_devices=1):
        """Set up and mock the writer."""

        async def mock_connect_internal():
            """Replace connect method."""
            my_dynalite = self.dyn_dev.dynalite
            my_dynalite.message_delay = 0
            my_dynalite.writer = self.mock_writer
            my_dynalite.broadcast(
                dyn_event.DynetEvent(event_type=dyn_const.EVENT_CONNECTED, data={})
            )
            my_dynalite.write()

        with patch.object(
            self.dyn_dev.dynalite, "connect_internal", mock_connect_internal
        ):
            await self.dyn_dev.async_setup()
            if num_devices > 0:
                self.new_dev_func.assert_called_once()
                assert len(self.new_dev_func.mock_calls[0][1][0]) == num_devices
                await asyncio.sleep(0.1)
                return self.new_dev_func.mock_calls[0][1][0]
            self.new_dev_func.assert_not_called()
            return None

    async def check_writes(self, packets):
        """Check that the set of writes was issued."""
        await asyncio.sleep(0.1)
        assert self.mock_writer.write.call_count == len(packets)
        for packet in packets:
            assert call.write(packet.msg) in self.mock_writer.mock_calls
        self.mock_writer.reset_mock()

    async def check_single_write(self, packet):
        """Check that there was only a single write issued."""
        await self.check_writes([packet])


@pytest.fixture
def mock_gw():
    """Mock a DynaliteDevices gateway."""
    return MockDynDev()
