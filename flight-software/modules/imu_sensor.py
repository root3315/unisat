"""IMU Sensor Module — Inertial Measurement Unit interface.

Provides accelerometer, gyroscope, and optional magnetometer data.
Essential for CanSat descent detection, rocket boost/coast detection,
drone stabilization, and CubeSat ADCS.

Supports MPU9250, BMI160, ICM-20948, LSM6DSO, and simulated data.
"""

from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass
from typing import Any

from modules import BaseModule, ModuleStatus


@dataclass
class IMUReading:
    """A single IMU measurement.

    Attributes:
        timestamp: Unix timestamp.
        accel_x_g: X acceleration in g.
        accel_y_g: Y acceleration in g.
        accel_z_g: Z acceleration in g.
        gyro_x_dps: X angular rate in degrees/sec.
        gyro_y_dps: Y angular rate in degrees/sec.
        gyro_z_dps: Z angular rate in degrees/sec.
        mag_x_ut: X magnetic field in microtesla (optional).
        mag_y_ut: Y magnetic field in microtesla (optional).
        mag_z_ut: Z magnetic field in microtesla (optional).
        temperature_c: Sensor temperature in Celsius.
    """

    timestamp: float
    accel_x_g: float
    accel_y_g: float
    accel_z_g: float
    gyro_x_dps: float
    gyro_y_dps: float
    gyro_z_dps: float
    mag_x_ut: float = 0.0
    mag_y_ut: float = 0.0
    mag_z_ut: float = 0.0
    temperature_c: float = 25.0

    @property
    def accel_magnitude_g(self) -> float:
        """Total acceleration magnitude in g."""
        return math.sqrt(
            self.accel_x_g ** 2 + self.accel_y_g ** 2 + self.accel_z_g ** 2
        )

    @property
    def gyro_magnitude_dps(self) -> float:
        """Total angular rate magnitude in deg/s."""
        return math.sqrt(
            self.gyro_x_dps ** 2 + self.gyro_y_dps ** 2 + self.gyro_z_dps ** 2
        )


class IMUSensor(BaseModule):
    """IMU sensor module with support for multiple sensor types.

    Configuration keys:
        sensor_type: Sensor model (default "MPU9250").
        sample_rate_hz: Sampling rate (default 100).
        accel_range_g: Accelerometer full scale (default 16).
        gyro_range_dps: Gyroscope full scale (default 2000).
        has_magnetometer: Whether sensor includes mag (default True).
        simulate: Use simulated data (default True).
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__("imu", config)
        self.sensor_type: str = self.config.get("sensor_type", "MPU9250")
        self.sample_rate_hz: int = self.config.get("sample_rate_hz", 100)
        self.accel_range_g: int = self.config.get("accel_range_g", 16)
        self.gyro_range_dps: int = self.config.get("gyro_range_dps", 2000)
        self.has_magnetometer: bool = self.config.get("has_magnetometer", True)
        self._simulate: bool = self.config.get("simulate", True)
        self._readings: list[IMUReading] = []
        self._max_readings: int = 10000
        self._sample_count: int = 0

    async def initialize(self) -> bool:
        """Initialize the IMU sensor."""
        self.logger.info(
            "IMU initialized: %s (accel=%dg, gyro=%ddps, mag=%s, sim=%s)",
            self.sensor_type, self.accel_range_g, self.gyro_range_dps,
            self.has_magnetometer, self._simulate,
        )
        self.status = ModuleStatus.READY
        return True

    async def start(self) -> None:
        self.status = ModuleStatus.RUNNING

    async def stop(self) -> None:
        self.status = ModuleStatus.STOPPED
        self.logger.info("IMU stopped, %d samples collected", self._sample_count)

    async def get_status(self) -> dict[str, Any]:
        return {
            "status": self.status.name,
            "sensor_type": self.sensor_type,
            "sample_count": self._sample_count,
            "sample_rate_hz": self.sample_rate_hz,
            "error_count": self._error_count,
        }

    def read(self) -> IMUReading:
        """Read current IMU data.

        Returns:
            IMUReading with current sensor values.
        """
        if self._simulate:
            reading = self._simulate_reading()
        else:
            reading = self._read_hardware()

        self._readings.append(reading)
        if len(self._readings) > self._max_readings:
            self._readings = self._readings[-self._max_readings:]
        self._sample_count += 1
        return reading

    def _simulate_reading(self) -> IMUReading:
        """Generate simulated IMU data with realistic noise."""
        noise_a = 0.02
        noise_g = 0.5
        return IMUReading(
            timestamp=time.time(),
            accel_x_g=random.gauss(0.0, noise_a),
            accel_y_g=random.gauss(0.0, noise_a),
            accel_z_g=random.gauss(-1.0, noise_a),  # gravity
            gyro_x_dps=random.gauss(0.0, noise_g),
            gyro_y_dps=random.gauss(0.0, noise_g),
            gyro_z_dps=random.gauss(0.0, noise_g),
            mag_x_ut=random.gauss(25.0, 1.0) if self.has_magnetometer else 0.0,
            mag_y_ut=random.gauss(5.0, 1.0) if self.has_magnetometer else 0.0,
            mag_z_ut=random.gauss(-45.0, 1.0) if self.has_magnetometer else 0.0,
            temperature_c=random.gauss(25.0, 0.5),
        )

    def _read_hardware(self) -> IMUReading:
        """Read from actual hardware via I2C/SPI.

        Placeholder — hardware-specific implementation depends on the
        sensor type and bus configuration.
        """
        self.logger.warning("Hardware IMU not implemented, returning simulated data")
        return self._simulate_reading()

    def detect_launch(self, threshold_g: float = 3.0) -> bool:
        """Detect launch by checking if acceleration exceeds threshold.

        Args:
            threshold_g: Acceleration threshold in g.

        Returns:
            True if current acceleration exceeds threshold.
        """
        if not self._readings:
            return False
        latest = self._readings[-1]
        return latest.accel_magnitude_g > threshold_g

    def detect_freefall(self, threshold_g: float = 0.3) -> bool:
        """Detect freefall (near-zero acceleration).

        Args:
            threshold_g: Low-g threshold.

        Returns:
            True if acceleration is below threshold.
        """
        if not self._readings:
            return False
        latest = self._readings[-1]
        return latest.accel_magnitude_g < threshold_g

    def detect_landing(self, window: int = 50, threshold_g: float = 0.1) -> bool:
        """Detect landing by checking for stable acceleration near 1g.

        Args:
            window: Number of recent samples to check.
            threshold_g: Max deviation from 1g.

        Returns:
            True if acceleration has been stable near 1g.
        """
        if len(self._readings) < window:
            return False
        recent = self._readings[-window:]
        magnitudes = [r.accel_magnitude_g for r in recent]
        avg = sum(magnitudes) / len(magnitudes)
        return abs(avg - 1.0) < threshold_g

    def get_recent_readings(self, count: int = 100) -> list[IMUReading]:
        """Return recent readings for analysis."""
        return self._readings[-count:]
