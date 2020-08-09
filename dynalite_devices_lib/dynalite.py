"""
Manage a Dynalite connection.

@ Author      : Troy Kelly
@ Date        : 3 Dec 2018
@ Description : Philips Dynalite Library - Unofficial interface for Philips Dynalite over RS485

@ Notes:        Requires a RS485 to IP gateway (Do not use the Dynalite one - use something cheaper)
"""

import asyncio
import time
from typing import Awaitable, Callable, List, Optional

from .const import (
    CONF_ACTION,
    CONF_ACTION_CMD,
    CONF_AREA,
    CONF_CHANNEL,
    CONF_PRESET,
    CONF_TRGT_LEVEL,
    CONNECTION_RETRY_DELAY,
    EVENT_CHANNEL,
    EVENT_CONNECTED,
    EVENT_DISCONNECTED,
    EVENT_PACKET,
    EVENT_PRESET,
    LOGGER,
    MESSAGE_DELAY,
)
from .dynet import DynetPacket, PacketError
from .event import DynetEvent
from .inbound import DynetInbound
from .opcodes import SyncType


class Dynalite:
    """Class to represent the interaction with Dynalite."""

    def __init__(self, broadcast_func: Callable[[DynetEvent], None]) -> None:
        """Initialize the class."""
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._broadcast_func = broadcast_func
        self._in_buffer: List[int] = []
        self._out_buffer: List[DynetPacket] = []
        self._last_sent = 0.0
        self._message_delay = MESSAGE_DELAY  # public for testing
        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None
        self._resetting = False
        self._reader_future: Optional[Awaitable[None]] = None

    async def connect_internal(self, host: str, port: int) -> bool:
        """Create the actual connection to Dynet."""
        try:
            self._reader, self._writer = await asyncio.open_connection(host, port)
            return True
        except (ValueError, OSError, asyncio.TimeoutError) as err:
            LOGGER.warning("Could not connect to Dynet (%s)", err)
            return False

    async def connect(self, host: str, port: int) -> bool:
        """Connect to Dynet."""
        LOGGER.debug("Connecting to Dynet on %s:%s", host, port)
        self._loop = asyncio.get_running_loop()
        self._resetting = False
        result = await self.connect_internal(host, port)
        if result and not self._resetting:
            self._reader_future = self._loop.create_task(self.reader_loop(host, port))
            self.broadcast(DynetEvent(event_type=EVENT_CONNECTED))
        return result

    async def reader_loop(self, host: str, port: int) -> None:
        """Loop to read from the stream reader and reconnect if necessary."""
        while True:
            self.write()  # write if there is something in the buffers
            try:
                assert self._reader
                data = await self._reader.read(100)
                if len(data) > 0:
                    self.receive(data)
                    continue
            except ConnectionResetError:
                pass
            # we got disconnected or EOF
            if self._resetting:
                self._reader = None
                return  # stop loop
            self._reader = None
            self._writer = None
            self.broadcast(DynetEvent(event_type=EVENT_DISCONNECTED))
            await asyncio.sleep(CONNECTION_RETRY_DELAY)  # Don't overload the network
            while not await self.connect_internal(host, port):
                if self._resetting:
                    self._reader = None
                    return  # stop loop
                # Don't overload the network
                await asyncio.sleep(CONNECTION_RETRY_DELAY)
            self.broadcast(DynetEvent(event_type=EVENT_CONNECTED))

    def broadcast(self, event: DynetEvent) -> None:
        """Broadcast an event to all listeners - queue."""
        assert self._loop
        self._loop.call_soon(self._broadcast_func, event)

    def set_channel_level(
        self, area: int, channel: int, level: float, fade: float
    ) -> None:
        """Set the level of a channel."""
        packet = DynetPacket.set_channel_level_packet(area, channel, level, fade)
        self.write(packet)
        broadcast_data = {
            CONF_AREA: area,
            CONF_CHANNEL: channel,
            CONF_TRGT_LEVEL: int(255 - 254.0 * level),
            CONF_ACTION: CONF_ACTION_CMD,
        }
        self.broadcast(DynetEvent(event_type=EVENT_CHANNEL, data=broadcast_data))

    def select_preset(self, area: int, preset: int, fade: float) -> None:
        """Select a preset in an area."""
        packet = DynetPacket.select_area_preset_packet(area, preset, fade)
        self.write(packet)
        broadcast_data = {
            CONF_AREA: area,
            CONF_PRESET: preset,
        }
        self.broadcast(DynetEvent(event_type=EVENT_PRESET, data=broadcast_data))

    def request_channel_level(self, area: int, channel: int) -> None:
        """Request a level for a specific channel."""
        packet = DynetPacket.request_channel_level_packet(area, channel)
        self.write(packet)

    def request_area_preset(self, area: int, query_channel: int) -> None:
        """Request current preset of an area."""
        packet = DynetPacket.request_area_preset_packet(area, query_channel)
        self.write(packet)

    def next_packet(self) -> Optional[DynetPacket]:
        """Get a valid packet from in_buffer."""
        packet = None
        while len(self._in_buffer) >= 8 and packet is None:
            first_byte = self._in_buffer[0]
            if SyncType.has_value(first_byte):
                if first_byte == SyncType.DEBUG_MSG.value:
                    bytemsg = "".join(chr(c) for c in self._in_buffer[1:7])
                    LOGGER.debug("Dynet DEBUG message %s", bytemsg)
                    self.broadcast(
                        DynetEvent(
                            event_type=EVENT_PACKET,
                            data={EVENT_PACKET: self._in_buffer[:8]},
                        )
                    )
                    self._in_buffer = self._in_buffer[8:]
                    continue
                if first_byte == SyncType.DEVICE.value:
                    LOGGER.debug(
                        "Not handling Dynet DEVICE message %s", self._in_buffer[:8]
                    )
                    self.broadcast(
                        DynetEvent(
                            event_type=EVENT_PACKET,
                            data={EVENT_PACKET: self._in_buffer[:8]},
                        )
                    )
                    self._in_buffer = self._in_buffer[8:]
                    continue
                assert first_byte == SyncType.LOGICAL.value
                try:
                    packet = DynetPacket(msg=self._in_buffer[:8])
                except PacketError as err:
                    LOGGER.warning(err)
                    packet = None
            if packet is None:
                hex_string = ":".join("{:02x}".format(c) for c in self._in_buffer[:8])
                LOGGER.debug(
                    "Unable to process packet %s - moving one byte forward", hex_string
                )
                del self._in_buffer[0]
                continue
            self.broadcast(
                DynetEvent(
                    event_type=EVENT_PACKET, data={EVENT_PACKET: self._in_buffer[:8]}
                )
            )
            self._in_buffer = self._in_buffer[8:]
        return packet

    @staticmethod
    def event_from_packet(packet: DynetPacket) -> Optional[DynetEvent]:
        """Create an event from a valid packet."""
        if packet.opcode_type is not None:
            inbound_handler = DynetInbound()
            if hasattr(inbound_handler, packet.opcode_type.lower()):
                event = getattr(inbound_handler, packet.opcode_type.lower())(packet)
                return event
            LOGGER.debug("Unhandled Dynet Inbound (%s): %s", packet.opcode_type, packet)
        else:
            LOGGER.debug("Unhandled Dynet Inbound: %s", packet)
        return None

    def receive(self, data: Optional[bytes] = None) -> None:
        """Handle data that was received."""
        if data is not None:
            for byte in data:
                self._in_buffer.append(int(byte))
        if len(self._in_buffer) < 8:
            LOGGER.debug(
                "Received %d bytes, not enough to process: %s",
                len(self._in_buffer),
                self._in_buffer,
            )
        packet = self.next_packet()
        if not packet:
            return
        LOGGER.debug("Have packet: %s", packet)
        event = self.event_from_packet(packet)
        if event:
            self.broadcast(event)
        # If there is still buffer to process - start again
        if len(self._in_buffer) >= 8:
            assert self._loop
            self._loop.call_soon(self.receive)

    def write(self, new_packet: Optional[DynetPacket] = None) -> None:
        """Write a packet or trigger write loop."""
        if new_packet is not None:
            self._out_buffer.append(new_packet)
        if self._writer is None:
            LOGGER.debug("write before transport is ready. queuing")
            return
        if self._message_delay > 0:  # in testing it is set to 0
            if self._last_sent == 0.0:
                self._last_sent = time.time()
            current_time = time.time()
            elapsed = current_time - self._last_sent
            delay = self._message_delay - elapsed
            if delay > 0:
                assert self._loop
                self._loop.call_later(delay, self.write)
                return
        if len(self._out_buffer) == 0:
            return
        packet = self._out_buffer[0]
        msg = packet.msg
        self._writer.write(msg)
        LOGGER.debug("Dynet Sent: %s", [int(byte) for byte in msg])
        self._last_sent = time.time()
        del self._out_buffer[0]
        if len(self._out_buffer) > 0:
            assert self._loop
            self._loop.call_later(self._message_delay, self.write)

    async def async_reset(self) -> None:
        """Close sockets and timers."""
        self._resetting = True
        # Wait for reader to also close
        if self._reader_future:
            await self._reader_future
