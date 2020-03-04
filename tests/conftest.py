"""Fixtures for the Dynalite tests."""
from asynctest import Mock, patch
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

    async def async_setup(self):
        """Set up and mock the writer."""

        async def mock_connect_internal():
            """Replace connect method."""
            my_dynalite = self.dyn_dev.dynalite
            my_dynalite.message_delay = 0
            dyn_const.LOGGER.error("XXX - AAA %s", my_dynalite.writer)
            my_dynalite.writer = self.mock_writer
            dyn_const.LOGGER.error("XXX - AAA %s", my_dynalite.writer)
            my_dynalite.broadcast(
                dyn_event.DynetEvent(event_type=dyn_const.EVENT_CONNECTED, data={})
            )
            my_dynalite.write()

        with patch.object(
            self.dyn_dev.dynalite, "connect_internal", mock_connect_internal
        ):
            await self.dyn_dev.async_setup()


@pytest.fixture
def mock_gw():
    """Mock a DynaliteDevices gateway."""
    return MockDynDev()
