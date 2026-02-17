"""Radiation Monitor Payload — SBM-20 Geiger counter."""

import time
import random
from dataclasses import dataclass


@dataclass
class RadiationData:
    """Single radiation measurement."""
    timestamp: float
    cps: int
    cpm: int
    dose_rate_usv_h: float
    total_dose_usv: float


class RadiationMonitor:
    """SBM-20 Geiger counter payload controller."""

    CONVERSION_FACTOR = 0.0057  # uSv/h per CPM for SBM-20

    def __init__(self) -> None:
        self.total_dose_usv = 0.0
        self.samples: list[RadiationData] = []
        self.active = False

    def initialize(self) -> bool:
        """Initialize SBM-20 counter and high-voltage supply."""
        self.active = True
        return True

    def collect_sample(self) -> RadiationData:
        """Read current radiation level."""
        # In real hardware: read pulse counter from GPIO interrupt
        cps = random.randint(0, 5)  # Background ~2-3 CPS
        cpm = cps * 60
        dose_rate = cpm * self.CONVERSION_FACTOR
        self.total_dose_usv += dose_rate / 3600.0

        sample = RadiationData(
            timestamp=time.time(), cps=cps, cpm=cpm,
            dose_rate_usv_h=round(dose_rate, 4),
            total_dose_usv=round(self.total_dose_usv, 6),
        )
        self.samples.append(sample)
        return sample

    def get_average_cpm(self, window_s: int = 60) -> float:
        """Get average CPM over time window."""
        now = time.time()
        recent = [s for s in self.samples if now - s.timestamp < window_s]
        if not recent:
            return 0.0
        return sum(s.cpm for s in recent) / len(recent)

    def shutdown(self) -> None:
        """Disable high-voltage supply."""
        self.active = False
