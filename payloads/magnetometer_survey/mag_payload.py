"""Magnetometer Survey Payload — High-resolution magnetic field mapping."""

import time
import math
from dataclasses import dataclass


@dataclass
class MagSample:
    """Magnetometer measurement with position."""
    timestamp: float
    bx_nt: float
    by_nt: float
    bz_nt: float
    magnitude_nt: float
    latitude: float
    longitude: float


class MagnetometerSurvey:
    """High-rate magnetometer for geomagnetic field mapping."""

    def __init__(self, sample_rate_hz: float = 10.0) -> None:
        self.sample_rate_hz = sample_rate_hz
        self.samples: list[MagSample] = []
        self.active = False

    def initialize(self) -> bool:
        self.active = True
        return True

    def collect_sample(self, lat: float = 0.0, lon: float = 0.0) -> MagSample:
        # Simplified IGRF model approximation
        bx = 25000 * math.cos(math.radians(lat))
        by = 2000 * math.sin(math.radians(lon))
        bz = 40000 * math.sin(math.radians(lat))
        magnitude = math.sqrt(bx**2 + by**2 + bz**2)

        sample = MagSample(time.time(), round(bx, 1), round(by, 1),
                           round(bz, 1), round(magnitude, 1), lat, lon)
        self.samples.append(sample)
        return sample

    def shutdown(self) -> None:
        self.active = False
