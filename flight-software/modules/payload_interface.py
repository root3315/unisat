"""
Payload Interface — Abstract base class for swappable payload modules.

All payload types (radiation monitor, camera, IoT relay, etc.) implement
this interface. Configuration is loaded from per-payload config.json files
or passed as a dict from the module registry.
"""

import time
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from modules import BaseModule, ModuleStatus

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


class PayloadInterface(BaseModule, ABC):
    """Abstract interface for all UniSat payload modules.

    Inherits from BaseModule for lifecycle management and from ABC
    for the payload-specific abstract methods.
    """

    def __init__(self, payload_type: str, config: dict[str, Any] | None = None) -> None:
        """Initialize payload module.

        Args:
            payload_type: Human-readable payload type identifier.
            config: Configuration dict from module registry or file.
        """
        super().__init__(payload_type, config)
        self.payload_status = PayloadStatus(
            payload_type=payload_type,
            config=config or {},
        )
        self._sequence = 0

    @abstractmethod
    def collect_sample(self) -> PayloadSample | None:
        """Collect one measurement. Returns None on failure."""

    @abstractmethod
    def shutdown(self) -> None:
        """Safely power down the payload."""

    async def initialize(self) -> bool:
        """Initialize payload hardware.

        Returns:
            True if initialization succeeded.
        """
        self.status = ModuleStatus.READY
        return True

    async def start(self) -> None:
        """Start the payload for data collection."""
        self.payload_status.active = True
        self.status = ModuleStatus.RUNNING
        self.logger.info("Payload %s activated", self.payload_status.payload_type)

    async def stop(self) -> None:
        """Deactivate the payload."""
        self.shutdown()
        self.payload_status.active = False
        self.status = ModuleStatus.STOPPED
        self.logger.info("Payload %s deactivated", self.payload_status.payload_type)

    async def get_status(self) -> dict[str, Any]:
        """Return current payload status.

        Returns:
            Dict with payload operational status.
        """
        return {
            "status": self.status.name,
            "payload_type": self.payload_status.payload_type,
            "active": self.payload_status.active,
            "samples_collected": self.payload_status.samples_collected,
            "errors": self.payload_status.errors,
            "error_count": self._error_count,
        }

    def collect(self) -> PayloadSample | None:
        """Collect a sample with bookkeeping."""
        if not self.payload_status.active:
            logger.warning("Payload not active, cannot collect")
            return None

        sample = self.collect_sample()
        if sample is not None:
            self._sequence += 1
            sample.sequence_num = self._sequence
            self.payload_status.samples_collected += 1
            self.payload_status.last_sample_time = time.time()
        else:
            self.payload_status.errors += 1

        return sample


class RadiationPayload(PayloadInterface):
    """SBM-20 Geiger counter radiation monitor."""

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        """Initialize radiation monitor.

        Args:
            config: Configuration dict with optional sensor parameters.
        """
        super().__init__("radiation_monitor", config)
        self._total_dose_usv = 0.0

    async def initialize(self) -> bool:
        """Initialize SBM-20 sensor.

        Returns:
            True on success.
        """
        self.logger.info("SBM-20 radiation monitor initialized")
        self.status = ModuleStatus.READY
        return True

    def collect_sample(self) -> PayloadSample:
        """Collect radiation measurement."""
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
        """Power down SBM-20."""
        self.logger.info(
            "SBM-20 powered down, total dose: %.4f uSv",
            self._total_dose_usv,
        )


class NullPayload(PayloadInterface):
    """No-op payload for testing."""

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        """Initialize null payload.

        Args:
            config: Ignored configuration dict.
        """
        super().__init__("null", config)

    def collect_sample(self) -> PayloadSample:
        """Return a dummy sample."""
        return PayloadSample(
            timestamp=time.time(),
            payload_type="null",
            data={"status": "ok"},
        )

    def shutdown(self) -> None:
        """No-op shutdown."""
