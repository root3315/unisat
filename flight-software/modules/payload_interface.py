"""
Payload Interface — Abstract base class for swappable payload modules.

All payload types (radiation monitor, camera, IoT relay, etc.) implement
this interface. Configuration is loaded from per-payload config.json files.
"""

import json
import time
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("unisat.payload")


@dataclass
class PayloadSample:
    """Single measurement from a payload."""
    timestamp: float
    payload_type: str
    data: dict[str, Any]
    sequence_num: int = 0


@dataclass
class PayloadStatus:
    """Current payload operational status."""
    active: bool = False
    payload_type: str = ""
    samples_collected: int = 0
    last_sample_time: float = 0.0
    health_pct: float = 100.0
    errors: int = 0
    config: dict[str, Any] = field(default_factory=dict)


class PayloadInterface(ABC):
    """Abstract interface for all UniSat payload modules."""

    def __init__(self, payload_type: str, config_path: str | None = None) -> None:
        self.status = PayloadStatus(payload_type=payload_type)
        self._sequence = 0
        if config_path:
            self.status.config = self._load_config(config_path)

    @staticmethod
    def _load_config(path: str) -> dict[str, Any]:
        """Load payload configuration from JSON file."""
        config_file = Path(path)
        if config_file.exists():
            with open(config_file, "r", encoding="utf-8") as f:
                return json.load(f)
        logger.warning("Config not found: %s, using defaults", path)
        return {}

    @abstractmethod
    def initialize(self) -> bool:
        """Initialize payload hardware. Returns True on success."""

    @abstractmethod
    def collect_sample(self) -> PayloadSample | None:
        """Collect one measurement. Returns None on failure."""

    @abstractmethod
    def shutdown(self) -> None:
        """Safely power down the payload."""

    def start(self) -> bool:
        """Activate the payload for data collection."""
        if self.status.active:
            return True
        ok = self.initialize()
        if ok:
            self.status.active = True
            logger.info("Payload %s activated", self.status.payload_type)
        else:
            self.status.errors += 1
            logger.error("Failed to activate %s", self.status.payload_type)
        return ok

    def stop(self) -> None:
        """Deactivate the payload."""
        self.shutdown()
        self.status.active = False
        logger.info("Payload %s deactivated", self.status.payload_type)

    def collect(self) -> PayloadSample | None:
        """Collect a sample with bookkeeping."""
        if not self.status.active:
            logger.warning("Payload not active, cannot collect")
            return None

        sample = self.collect_sample()
        if sample is not None:
            self._sequence += 1
            sample.sequence_num = self._sequence
            self.status.samples_collected += 1
            self.status.last_sample_time = time.time()
        else:
            self.status.errors += 1

        return sample

    def get_status(self) -> PayloadStatus:
        """Return current payload status."""
        return self.status


class RadiationPayload(PayloadInterface):
    """SBM-20 Geiger counter radiation monitor."""

    def __init__(self, config_path: str | None = None) -> None:
        super().__init__("radiation_monitor", config_path)
        self._total_dose_usv = 0.0

    def initialize(self) -> bool:
        logger.info("SBM-20 radiation monitor initialized")
        return True

    def collect_sample(self) -> PayloadSample:
        import random
        cps = random.randint(0, 5)
        cpm = cps * 60
        dose_rate = cpm * 0.0057  # uSv/h per CPM for SBM-20
        self._total_dose_usv += dose_rate / 3600.0

        return PayloadSample(
            timestamp=time.time(),
            payload_type="radiation_monitor",
            data={
                "cps": cps,
                "cpm": cpm,
                "dose_rate_usv_h": round(dose_rate, 4),
                "total_dose_usv": round(self._total_dose_usv, 6),
            },
        )

    def shutdown(self) -> None:
        logger.info("SBM-20 powered down, total dose: %.4f uSv",
                     self._total_dose_usv)


class NullPayload(PayloadInterface):
    """No-op payload for testing."""

    def __init__(self) -> None:
        super().__init__("null")

    def initialize(self) -> bool:
        return True

    def collect_sample(self) -> PayloadSample:
        return PayloadSample(
            timestamp=time.time(),
            payload_type="null",
            data={"status": "ok"},
        )

    def shutdown(self) -> None:
        pass
