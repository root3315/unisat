"""Communication Manager for UniSat CubeSat.

Handles UART serial communication with the OBC, CCSDS packet framing,
HMAC-SHA256 command authentication, and connection health monitoring.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import struct
import time
from collections import deque
from typing import Any

import serial

from modules import BaseModule, ModuleStatus
from modules.telemetry_manager import SYNC_WORD, TelemetryFrame, TelemetryManager


class CommunicationManager(BaseModule):
    """Manages UART serial communication and command authentication.

    Attributes:
        port: Serial port device path.
        baud_rate: UART baud rate.
        hmac_key: Shared secret for HMAC-SHA256 command auth.
        telemetry: Reference to the telemetry manager for packet building.
        tx_queue: Outbound packet queue.
        rx_queue: Inbound packet queue.
    """

    def __init__(self, config: dict[str, Any] | None = None,
                 telemetry: TelemetryManager | None = None) -> None:
        """Initialize the communication manager.

        Args:
            config: Configuration with 'port', 'baud_rate', 'hmac_key'.
            telemetry: TelemetryManager instance for packet construction.
        """
        super().__init__("communication", config)
        self.port: str = self.config.get("port", "/dev/ttyS0")
        self.baud_rate: int = self.config.get("baud_rate", 9600)
        self.hmac_key: bytes = self.config.get("hmac_key", "unisat_default_key").encode()
        self.telemetry = telemetry
        self._serial: serial.Serial | None = None
        self.tx_queue: deque[bytes] = deque(maxlen=256)
        self.rx_queue: deque[bytes] = deque(maxlen=256)
        self._last_rx_time: float = time.time()
        self._bytes_sent: int = 0
        self._bytes_received: int = 0
        self._connected: bool = False

    async def initialize(self) -> bool:
        """Open the serial port and verify connectivity.

        Returns:
            True if the serial port was opened successfully.
        """
        try:
            self._serial = serial.Serial(
                port=self.port,
                baudrate=self.baud_rate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=0.1,
                write_timeout=1.0,
            )
            self._connected = True
            self._last_rx_time = time.time()
            self.status = ModuleStatus.READY
            self.logger.info("Serial port %s opened at %d baud", self.port, self.baud_rate)
            return True
        except serial.SerialException as exc:
            self.record_error(f"Failed to open serial port: {exc}")
            self._connected = False
            self.status = ModuleStatus.ERROR
            return False

    async def start(self) -> None:
        """Start the communication loops."""
        self.status = ModuleStatus.RUNNING
        self.logger.info("Communication manager started")

    async def stop(self) -> None:
        """Close the serial port and stop communication."""
        if self._serial and self._serial.is_open:
            self._serial.close()
        self._connected = False
        self.status = ModuleStatus.STOPPED
        self.logger.info("Communication manager stopped")

    async def get_status(self) -> dict[str, Any]:
        """Return communication subsystem status.

        Returns:
            Dict with connection state, byte counters, and last RX time.
        """
        return {
            "status": self.status.name,
            "connected": self._connected,
            "bytes_sent": self._bytes_sent,
            "bytes_received": self._bytes_received,
            "last_rx_age_s": round(time.time() - self._last_rx_time, 1),
            "tx_queue_depth": len(self.tx_queue),
            "rx_queue_depth": len(self.rx_queue),
            "error_count": self._error_count,
        }

    def sign_command(self, command_bytes: bytes) -> bytes:
        """Compute HMAC-SHA256 signature for a command.

        Args:
            command_bytes: The raw command payload to sign.

        Returns:
            32-byte HMAC digest.
        """
        return hmac.new(self.hmac_key, command_bytes, hashlib.sha256).digest()

    def verify_command(self, command_bytes: bytes, signature: bytes) -> bool:
        """Verify the HMAC-SHA256 signature of a received command.

        Args:
            command_bytes: The raw command payload.
            signature: The 32-byte HMAC digest to verify against.

        Returns:
            True if the signature is valid.
        """
        expected = self.sign_command(command_bytes)
        return hmac.compare_digest(expected, signature)

    async def send_packet(self, packet: bytes) -> bool:
        """Send a raw packet over UART.

        Args:
            packet: Complete CCSDS packet bytes to transmit.

        Returns:
            True if the packet was sent successfully.
        """
        if not self._serial or not self._serial.is_open:
            self.tx_queue.append(packet)
            self.record_error("Serial port not open, packet queued")
            return False
        try:
            written = self._serial.write(packet)
            self._bytes_sent += written
            self.logger.debug("TX %d bytes", written)
            return True
        except serial.SerialException as exc:
            self.record_error(f"TX failed: {exc}")
            self.tx_queue.append(packet)
            self._connected = False
            return False

    async def receive_packet(self) -> bytes | None:
        """Read a single CCSDS packet from the serial port.

        Searches for the sync word, reads the header to determine packet
        length, then reads the full packet.

        Returns:
            Complete packet bytes including sync word, or None if no data.
        """
        if not self._serial or not self._serial.is_open:
            return None
        try:
            available = self._serial.in_waiting
            if available < 14:
                return None
            buf = self._serial.read(available)
            self._bytes_received += len(buf)
            sync_bytes = struct.pack(">I", SYNC_WORD)
            idx = buf.find(sync_bytes)
            if idx < 0:
                return None
            buf = buf[idx:]
            if len(buf) < 14:
                return None
            _, _, data_length = struct.unpack(">HHH", buf[4:10])
            total_len = 10 + data_length + 1
            if len(buf) < total_len:
                return None
            packet = buf[:total_len]
            self._last_rx_time = time.time()
            self.rx_queue.append(packet)
            self.logger.debug("RX %d bytes", len(packet))
            # Explicit bytes() cast — pyserial's read() returns Any at
            # the stub level; narrow here so mypy's strict mode stops
            # complaining about a returned Any.
            return bytes(packet)
        except serial.SerialException as exc:
            self.record_error(f"RX failed: {exc}")
            self._connected = False
            return None

    async def send_authenticated_command(self, command_id: int, payload: bytes) -> bool:
        """Build and send an authenticated command packet.

        The packet format:
            [2B command_id][NB payload][32B HMAC-SHA256]

        Args:
            command_id: 16-bit command identifier.
            payload: Command payload bytes.

        Returns:
            True if the packet was sent successfully.
        """
        cmd_bytes = struct.pack(">H", command_id) + payload
        signature = self.sign_command(cmd_bytes)
        full_packet = cmd_bytes + signature
        return await self.send_packet(full_packet)

    async def flush_tx_queue(self) -> int:
        """Attempt to send all queued packets.

        Returns:
            Number of packets successfully sent.
        """
        sent = 0
        while self.tx_queue:
            packet = self.tx_queue.popleft()
            if await self.send_packet(packet):
                sent += 1
            else:
                break
        return sent

    def seconds_since_last_rx(self) -> float:
        """Return the elapsed time since the last received packet.

        Returns:
            Seconds since last successful reception.
        """
        return time.time() - self._last_rx_time

    def is_connected(self) -> bool:
        """Check whether the serial link appears healthy.

        Returns:
            True if connected and data was received within the last 120 seconds.
        """
        return self._connected and self.seconds_since_last_rx() < 120.0
