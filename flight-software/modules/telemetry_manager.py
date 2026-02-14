"""Telemetry Manager for UniSat CubeSat.

Builds and parses CCSDS-compatible telemetry packets matching the C firmware
packet format. Handles sensor data packing, unpacking, and timestamping.
"""

from __future__ import annotations

import struct
import time
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any

from modules import BaseModule, ModuleStatus


class APID(IntEnum):
    """Application Process Identifiers for CCSDS packets."""

    HOUSEKEEPING = 0x01
    ADCS = 0x02
    EPS = 0x03
    CAMERA = 0x04
    PAYLOAD = 0x05
    GPS = 0x06
    THERMAL = 0x07
    COMMAND_ACK = 0x10
    EVENT = 0x20


CCSDS_HEADER_SIZE = 6
CCSDS_SEC_HEADER_SIZE = 4
SYNC_WORD = 0x1ACFFC1D
CCSDS_VERSION = 0
CCSDS_TYPE_TM = 0
CCSDS_SEC_HDR_FLAG = 1


@dataclass
class TelemetryFrame:
    """A single telemetry frame with CCSDS header and payload.

    Attributes:
        apid: Application process identifier.
        sequence_count: Packet sequence counter (14-bit, wraps at 16383).
        timestamp: Mission elapsed time in seconds.
        payload: Raw payload bytes.
    """

    apid: APID
    sequence_count: int
    timestamp: float
    payload: bytes
    raw: bytes = field(default=b"", repr=False)


class TelemetryManager(BaseModule):
    """Manages CCSDS telemetry packet construction and parsing.

    Attributes:
        epoch: Mission epoch as a Unix timestamp.
        sequence_counters: Per-APID sequence counters.
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        """Initialize the telemetry manager.

        Args:
            config: Configuration dict, may contain 'mission_epoch' ISO string.
        """
        super().__init__("telemetry", config)
        self.epoch: float = self.config.get("mission_epoch_unix", time.time())
        self.sequence_counters: dict[int, int] = {apid: 0 for apid in APID}

    async def initialize(self) -> bool:
        """Initialize telemetry subsystem.

        Returns:
            Always True; telemetry is a software-only module.
        """
        self.status = ModuleStatus.READY
        self.logger.info("Telemetry manager initialized, epoch=%.1f", self.epoch)
        return True

    async def start(self) -> None:
        """Start telemetry manager (sets status to RUNNING)."""
        self.status = ModuleStatus.RUNNING
        self.logger.info("Telemetry manager started")

    async def stop(self) -> None:
        """Stop telemetry manager."""
        self.status = ModuleStatus.STOPPED
        self.logger.info("Telemetry manager stopped")

    async def get_status(self) -> dict[str, Any]:
        """Return telemetry subsystem status.

        Returns:
            Dict with status, counters, and error count.
        """
        return {
            "status": self.status.name,
            "sequence_counters": dict(self.sequence_counters),
            "error_count": self._error_count,
        }

    def get_mission_time(self) -> float:
        """Compute mission elapsed time in seconds.

        Returns:
            Seconds since mission epoch.
        """
        return time.time() - self.epoch

    def _next_sequence(self, apid: APID) -> int:
        """Increment and return the next sequence count for a given APID.

        Args:
            apid: The application process identifier.

        Returns:
            Next 14-bit sequence count.
        """
        count = self.sequence_counters[apid]
        self.sequence_counters[apid] = (count + 1) & 0x3FFF
        return count

    def build_packet(self, apid: APID, payload: bytes) -> bytes:
        """Build a complete CCSDS telemetry packet.

        Packet layout (big-endian):
            [4B sync][6B primary header][4B secondary header][NB payload]

        Primary header (6 bytes):
            - version(3b) | type(1b) | sec_hdr(1b) | apid(11b)  -> 2 bytes
            - seq_flags(2b) | seq_count(14b)                     -> 2 bytes
            - data_length (payload + sec_header - 1)              -> 2 bytes

        Secondary header (4 bytes):
            - mission elapsed time as uint32

        Args:
            apid: Application process identifier.
            payload: Raw payload data bytes.

        Returns:
            Complete packet bytes including sync word.
        """
        seq_count = self._next_sequence(apid)
        met = int(self.get_mission_time()) & 0xFFFFFFFF

        word0 = (CCSDS_VERSION << 13) | (CCSDS_TYPE_TM << 12) | (CCSDS_SEC_HDR_FLAG << 11) | (apid & 0x7FF)
        word1 = (0x03 << 14) | (seq_count & 0x3FFF)
        data_length = CCSDS_SEC_HEADER_SIZE + len(payload) - 1

        header = struct.pack(">HHH", word0, word1, data_length)
        sec_header = struct.pack(">I", met)
        sync = struct.pack(">I", SYNC_WORD)

        return sync + header + sec_header + payload

    def parse_packet(self, raw: bytes) -> TelemetryFrame | None:
        """Parse a raw CCSDS packet into a TelemetryFrame.

        Args:
            raw: Raw bytes starting with the 4-byte sync word.

        Returns:
            Parsed TelemetryFrame or None if parsing fails.
        """
        min_size = 4 + CCSDS_HEADER_SIZE + CCSDS_SEC_HEADER_SIZE
        if len(raw) < min_size:
            self.record_error(f"Packet too short: {len(raw)} bytes")
            return None

        sync_val = struct.unpack(">I", raw[:4])[0]
        if sync_val != SYNC_WORD:
            self.record_error(f"Bad sync word: 0x{sync_val:08X}")
            return None

        word0, word1, data_length = struct.unpack(">HHH", raw[4:10])
        apid_val = word0 & 0x7FF
        seq_count = word1 & 0x3FFF
        met = struct.unpack(">I", raw[10:14])[0]
        payload = raw[14: 14 + data_length - CCSDS_SEC_HEADER_SIZE + 1]

        try:
            apid_enum = APID(apid_val)
        except ValueError:
            apid_enum = APID.HOUSEKEEPING

        return TelemetryFrame(
            apid=apid_enum,
            sequence_count=seq_count,
            timestamp=float(met),
            payload=payload,
            raw=raw,
        )

    def pack_housekeeping(self, battery_v: float, battery_soc: float, cpu_temp: float,
                          solar_current_ma: float, uptime_s: int) -> bytes:
        """Pack housekeeping sensor data into a telemetry payload.

        Args:
            battery_v: Battery voltage in volts.
            battery_soc: Battery state of charge (0.0-1.0).
            cpu_temp: CPU temperature in Celsius.
            solar_current_ma: Solar panel current in milliamps.
            uptime_s: System uptime in seconds.

        Returns:
            Packed bytes (20 bytes total).
        """
        return struct.pack(">ffffI", battery_v, battery_soc, cpu_temp, solar_current_ma, uptime_s)

    def unpack_housekeeping(self, data: bytes) -> dict[str, float | int]:
        """Unpack housekeeping payload bytes into a dictionary.

        Args:
            data: 20 bytes of packed housekeeping data.

        Returns:
            Dictionary with battery_v, battery_soc, cpu_temp, solar_current_ma, uptime_s.
        """
        bv, soc, temp, solar, uptime = struct.unpack(">ffffI", data[:20])
        return {
            "battery_v": round(bv, 3),
            "battery_soc": round(soc, 3),
            "cpu_temp": round(temp, 2),
            "solar_current_ma": round(solar, 1),
            "uptime_s": uptime,
        }
