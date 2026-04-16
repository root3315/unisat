"""Barometric Altimeter Module — Pressure-based altitude measurement.

Provides altitude, pressure, and temperature data from barometric sensors.
Essential for CanSat descent tracking, rocket apogee detection, HAB burst
detection, and drone altitude hold.

Supports BME280, BMP388, MS5611, and simulated data.
"""

from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass
from typing import Any

from modules import BaseModule, ModuleStatus


# ISA (International Standard Atmosphere) constants
SEA_LEVEL_PRESSURE_PA = 101325.0
TEMPERATURE_LAPSE_RATE = 0.0065  # K/m
SEA_LEVEL_TEMPERATURE_K = 288.15
GRAVITY = 9.80665
MOLAR_MASS_AIR = 0.0289644
GAS_CONSTANT = 8.31447


@dataclass
class BaroReading:
    """A single barometric measurement.

    Attributes:
        timestamp: Unix timestamp.
        pressure_pa: Atmospheric pressure in Pascals.
        temperature_c: Temperature in Celsius.
        altitude_m: Calculated altitude in meters (above sea level).
        vertical_speed_m_s: Estimated vertical speed in m/s.
    """

    timestamp: float
    pressure_pa: float
    temperature_c: float
    altitude_m: float
    vertical_speed_m_s: float = 0.0


def pressure_to_altitude(pressure_pa: float,
                          ref_pressure_pa: float = SEA_LEVEL_PRESSURE_PA) -> float:
    """Convert pressure to altitude using the barometric formula.

    Args:
        pressure_pa: Measured pressure in Pascals.
        ref_pressure_pa: Reference (sea level) pressure in Pascals.

    Returns:
        Altitude in meters above the reference level.
    """
    if pressure_pa <= 0:
        return 0.0
    ratio = pressure_pa / ref_pressure_pa
    exponent = (GAS_CONSTANT * TEMPERATURE_LAPSE_RATE) / (GRAVITY * MOLAR_MASS_AIR)
    return (SEA_LEVEL_TEMPERATURE_K / TEMPERATURE_LAPSE_RATE) * (1.0 - ratio ** exponent)


class BarometricAltimeter(BaseModule):
    """Barometric altimeter module with altitude and vertical speed.

    Configuration keys:
        sensor_type: Sensor model (default "BME280").
        sample_rate_hz: Sampling rate (default 25).
        ref_pressure_pa: Sea-level reference pressure (default 101325).
        ground_altitude_m: Launch site altitude MSL (default 0).
        simulate: Use simulated data (default True).
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__("barometer", config)
        self.sensor_type: str = self.config.get("sensor_type", "BME280")
        self.sample_rate_hz: int = self.config.get("sample_rate_hz", 25)
        self.ref_pressure_pa: float = self.config.get("ref_pressure_pa", SEA_LEVEL_PRESSURE_PA)
        self.ground_altitude_m: float = self.config.get("ground_altitude_m", 0.0)
        self._simulate: bool = self.config.get("simulate", True)
        self._readings: list[BaroReading] = []
        self._max_readings: int = 10000
        self._sample_count: int = 0
        self._max_altitude_m: float = 0.0
        self._sim_phase: str = "ground"
        self._sim_start: float = 0.0

    async def initialize(self) -> bool:
        self.logger.info(
            "Barometric altimeter initialized: %s (rate=%dHz, ref=%.0fPa)",
            self.sensor_type, self.sample_rate_hz, self.ref_pressure_pa,
        )
        self._sim_start = time.time()
        self.status = ModuleStatus.READY
        return True

    async def start(self) -> None:
        self.status = ModuleStatus.RUNNING

    async def stop(self) -> None:
        self.status = ModuleStatus.STOPPED
        self.logger.info(
            "Barometer stopped, %d samples, max alt: %.1fm",
            self._sample_count, self._max_altitude_m,
        )

    async def get_status(self) -> dict[str, Any]:
        return {
            "status": self.status.name,
            "sensor_type": self.sensor_type,
            "sample_count": self._sample_count,
            "max_altitude_m": round(self._max_altitude_m, 1),
            "error_count": self._error_count,
        }

    def read(self) -> BaroReading:
        """Read current barometric data.

        Returns:
            BaroReading with pressure, temperature, altitude, vertical speed.
        """
        if self._simulate:
            reading = self._simulate_reading()
        else:
            reading = self._read_hardware()

        # Track max altitude
        agl = reading.altitude_m - self.ground_altitude_m
        if agl > self._max_altitude_m:
            self._max_altitude_m = agl

        # Calculate vertical speed from last two readings
        if self._readings:
            prev = self._readings[-1]
            dt = reading.timestamp - prev.timestamp
            if dt > 0:
                reading.vertical_speed_m_s = (reading.altitude_m - prev.altitude_m) / dt

        self._readings.append(reading)
        if len(self._readings) > self._max_readings:
            self._readings = self._readings[-self._max_readings:]
        self._sample_count += 1
        return reading

    def _simulate_reading(self) -> BaroReading:
        """Generate simulated barometric data."""
        noise_pa = random.gauss(0, 5.0)
        base_pressure = self.ref_pressure_pa + noise_pa
        altitude = pressure_to_altitude(base_pressure, self.ref_pressure_pa)
        temp = 15.0 - altitude * TEMPERATURE_LAPSE_RATE + random.gauss(0, 0.2)

        return BaroReading(
            timestamp=time.time(),
            pressure_pa=base_pressure,
            temperature_c=round(temp, 2),
            altitude_m=round(altitude + self.ground_altitude_m, 2),
        )

    def _read_hardware(self) -> BaroReading:
        """Read from actual sensor hardware. Placeholder."""
        self.logger.warning("Hardware barometer not implemented, using simulated data")
        return self._simulate_reading()

    def get_altitude_agl(self) -> float:
        """Current altitude above ground level in meters."""
        if not self._readings:
            return 0.0
        return self._readings[-1].altitude_m - self.ground_altitude_m

    def get_max_altitude_agl(self) -> float:
        """Maximum recorded altitude AGL in meters."""
        return self._max_altitude_m

    def get_vertical_speed(self) -> float:
        """Current vertical speed in m/s (positive = ascending)."""
        if not self._readings:
            return 0.0
        return self._readings[-1].vertical_speed_m_s

    def detect_apogee(self, window: int = 10) -> bool:
        """Detect apogee by finding altitude peak.

        Checks if altitude has been consistently decreasing over the
        last ``window`` samples after previously increasing.

        Args:
            window: Number of samples to check.

        Returns:
            True if apogee is detected.
        """
        if len(self._readings) < window + 5:
            return False
        recent = [r.altitude_m for r in self._readings[-window:]]
        before = [r.altitude_m for r in self._readings[-(window + 5):-window]]
        return (
            all(recent[i] >= recent[i + 1] for i in range(len(recent) - 1))
            and max(before) > min(before)
            and max(before) > recent[-1]
        )

    def detect_burst(self, drop_threshold_m: float = 50.0) -> bool:
        """Detect balloon burst by rapid altitude drop.

        Args:
            drop_threshold_m: Minimum altitude drop to consider a burst.

        Returns:
            True if burst detected.
        """
        if len(self._readings) < 20:
            return False
        recent_alts = [r.altitude_m for r in self._readings[-20:]]
        peak = max(recent_alts[:10])
        current = recent_alts[-1]
        return (peak - current) > drop_threshold_m

    def get_recent_readings(self, count: int = 100) -> list[BaroReading]:
        """Return recent readings."""
        return self._readings[-count:]

    def set_sim_phase(self, phase: str) -> None:
        """Set simulation phase for realistic test data."""
        self._sim_phase = phase
