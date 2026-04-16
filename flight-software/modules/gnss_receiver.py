"""GNSS Receiver Module — GPS/GNSS position and time data.

Provides latitude, longitude, altitude, speed, and satellite count
from GNSS receivers (u-blox MAX-M10S, NEO-M8N, etc.).
Supports simulated data for ground testing.
"""

from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass
from typing import Any

from modules import BaseModule, ModuleStatus


@dataclass
class GNSSFix:
    """A single GNSS position fix.

    Attributes:
        timestamp: Unix timestamp.
        latitude: Latitude in degrees (-90 to 90).
        longitude: Longitude in degrees (-180 to 180).
        altitude_m: Altitude above sea level in meters.
        speed_m_s: Ground speed in m/s.
        heading_deg: Heading in degrees (0-360).
        satellites: Number of satellites in view.
        hdop: Horizontal dilution of precision.
        fix_quality: Fix quality (0=no fix, 1=GPS, 2=DGPS).
    """

    timestamp: float
    latitude: float
    longitude: float
    altitude_m: float
    speed_m_s: float = 0.0
    heading_deg: float = 0.0
    satellites: int = 0
    hdop: float = 99.0
    fix_quality: int = 0


class GNSSReceiver(BaseModule):
    """GNSS receiver module.

    Configuration keys:
        receiver: Receiver model (default "u-blox_MAX-M10S").
        update_rate_hz: Position update rate (default 1).
        simulate: Use simulated data (default True).
        base_lat: Simulated base latitude (default 41.2995).
        base_lon: Simulated base longitude (default 69.2401).
        base_alt_m: Simulated base altitude (default 455).
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__("gnss", config)
        self.receiver: str = self.config.get("receiver", "u-blox_MAX-M10S")
        self.update_rate_hz: int = self.config.get("update_rate_hz", 1)
        self._simulate: bool = self.config.get("simulate", True)
        self._base_lat: float = self.config.get("base_lat", 41.2995)
        self._base_lon: float = self.config.get("base_lon", 69.2401)
        self._base_alt: float = self.config.get("base_alt_m", 455.0)
        self._fixes: list[GNSSFix] = []
        self._sample_count: int = 0

    async def initialize(self) -> bool:
        self.logger.info("GNSS initialized: %s (%dHz, sim=%s)",
                         self.receiver, self.update_rate_hz, self._simulate)
        self.status = ModuleStatus.READY
        return True

    async def start(self) -> None:
        self.status = ModuleStatus.RUNNING

    async def stop(self) -> None:
        self.status = ModuleStatus.STOPPED
        self.logger.info("GNSS stopped, %d fixes recorded", self._sample_count)

    async def get_status(self) -> dict[str, Any]:
        last = self._fixes[-1] if self._fixes else None
        return {
            "status": self.status.name,
            "receiver": self.receiver,
            "fix_count": self._sample_count,
            "satellites": last.satellites if last else 0,
            "fix_quality": last.fix_quality if last else 0,
            "error_count": self._error_count,
        }

    def read(self) -> GNSSFix:
        """Read current GNSS position."""
        if self._simulate:
            fix = self._simulate_fix()
        else:
            fix = self._read_hardware()

        self._fixes.append(fix)
        if len(self._fixes) > 5000:
            self._fixes = self._fixes[-5000:]
        self._sample_count += 1
        return fix

    def _simulate_fix(self) -> GNSSFix:
        """Generate simulated GNSS data with GPS-like noise."""
        noise_deg = 0.00001  # ~1m
        return GNSSFix(
            timestamp=time.time(),
            latitude=self._base_lat + random.gauss(0, noise_deg),
            longitude=self._base_lon + random.gauss(0, noise_deg),
            altitude_m=self._base_alt + random.gauss(0, 2.0),
            speed_m_s=random.gauss(0, 0.1),
            heading_deg=random.uniform(0, 360),
            satellites=random.randint(6, 12),
            hdop=random.uniform(0.8, 2.5),
            fix_quality=1,
        )

    def _read_hardware(self) -> GNSSFix:
        """Read from actual GNSS hardware. Placeholder."""
        self.logger.warning("Hardware GNSS not implemented, using simulated data")
        return self._simulate_fix()

    def get_last_fix(self) -> GNSSFix | None:
        """Return most recent fix."""
        return self._fixes[-1] if self._fixes else None

    def get_distance_from_base(self) -> float:
        """Distance in meters from the base/launch position."""
        if not self._fixes:
            return 0.0
        last = self._fixes[-1]
        dlat = math.radians(last.latitude - self._base_lat)
        dlon = math.radians(last.longitude - self._base_lon)
        a = (math.sin(dlat / 2) ** 2 +
             math.cos(math.radians(self._base_lat)) *
             math.cos(math.radians(last.latitude)) *
             math.sin(dlon / 2) ** 2)
        return 6371000 * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
