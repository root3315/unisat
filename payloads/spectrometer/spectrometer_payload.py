"""Spectrometer Payload — Optical spectrum analysis."""

import time
from dataclasses import dataclass


@dataclass
class SpectrumSample:
    """Single spectrum measurement."""
    timestamp: float
    wavelengths_nm: list[float]
    intensities: list[float]
    integration_time_ms: int


class SpectrometerPayload:
    """AS7265x-based 18-channel optical spectrometer."""

    WAVELENGTHS = [
        410, 435, 460, 485, 510, 535, 560, 585, 610,
        645, 680, 705, 730, 760, 810, 860, 900, 940,
    ]

    def __init__(self, integration_ms: int = 100) -> None:
        self.integration_ms = integration_ms
        self.samples: list[SpectrumSample] = []
        self.active = False

    def initialize(self) -> bool:
        self.active = True
        return True

    def collect_sample(self) -> SpectrumSample:
        import random
        intensities = [random.uniform(100, 4000) for _ in self.WAVELENGTHS]
        sample = SpectrumSample(
            time.time(), list(self.WAVELENGTHS),
            [round(v, 1) for v in intensities], self.integration_ms,
        )
        self.samples.append(sample)
        return sample

    def shutdown(self) -> None:
        self.active = False
