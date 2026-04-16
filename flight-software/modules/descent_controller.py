"""Descent Controller Module — Parachute deployment and descent management.

Manages parachute deployment based on altitude/acceleration triggers,
monitors descent rate, and validates competition requirements.
Essential for CanSat competitions and rocket recovery systems.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any

from modules import BaseModule, ModuleStatus

logger = logging.getLogger("unisat.descent")


class DescentPhase(Enum):
    """Descent controller phases."""

    IDLE = auto()
    ARMED = auto()
    DEPLOY_READY = auto()
    DEPLOYED = auto()
    DESCENDING = auto()
    LANDED = auto()


@dataclass
class DescentConfig:
    """Configuration for descent controller.

    Attributes:
        deploy_altitude_m: Altitude AGL to deploy parachute.
        deploy_accel_threshold_g: Low-g threshold for deployment.
        target_descent_rate_m_s: Target descent rate.
        min_descent_rate_m_s: Minimum acceptable descent rate.
        max_descent_rate_m_s: Maximum acceptable descent rate.
        landing_speed_threshold_m_s: Max acceptable landing speed.
        deploy_delay_s: Delay after trigger before deployment.
        min_telemetry_samples: Minimum samples for competition validity.
    """

    deploy_altitude_m: float = 500.0
    deploy_accel_threshold_g: float = 0.5
    target_descent_rate_m_s: float = 8.0
    min_descent_rate_m_s: float = 6.0
    max_descent_rate_m_s: float = 11.0
    landing_speed_threshold_m_s: float = 12.0
    deploy_delay_s: float = 1.0
    min_telemetry_samples: int = 100


@dataclass
class DescentTelemetry:
    """Descent phase telemetry snapshot."""

    timestamp: float
    phase: DescentPhase
    altitude_agl_m: float
    descent_rate_m_s: float
    time_since_deploy_s: float = 0.0
    parachute_deployed: bool = False
    samples_collected: int = 0


@dataclass
class CompetitionResult:
    """Competition validation results."""

    valid: bool
    descent_rate_avg_m_s: float = 0.0
    descent_rate_min_m_s: float = 0.0
    descent_rate_max_m_s: float = 0.0
    landing_velocity_m_s: float = 0.0
    telemetry_count: int = 0
    flight_duration_s: float = 0.0
    max_altitude_m: float = 0.0
    issues: list[str] = field(default_factory=list)


class DescentController(BaseModule):
    """Manages parachute deployment and descent monitoring.

    Configuration keys:
        deploy_altitude_m: Deployment altitude AGL (default 500).
        target_descent_rate_m_s: Target descent rate (default 8.0).
        min_descent_rate_m_s: Min acceptable rate (default 6.0).
        max_descent_rate_m_s: Max acceptable rate (default 11.0).
        landing_speed_threshold_m_s: Max landing speed (default 12.0).
        deploy_delay_s: Delay after trigger (default 1.0).
        min_telemetry_samples: Min samples for validity (default 100).
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__("descent_controller", config)
        self.descent_config = DescentConfig(
            deploy_altitude_m=self.config.get("deploy_altitude_m", 500.0),
            deploy_accel_threshold_g=self.config.get("deploy_accel_threshold_g", 0.5),
            target_descent_rate_m_s=self.config.get("target_descent_rate_m_s", 8.0),
            min_descent_rate_m_s=self.config.get("min_descent_rate_m_s", 6.0),
            max_descent_rate_m_s=self.config.get("max_descent_rate_m_s", 11.0),
            landing_speed_threshold_m_s=self.config.get("landing_speed_threshold_m_s", 12.0),
            deploy_delay_s=self.config.get("deploy_delay_s", 1.0),
            min_telemetry_samples=self.config.get("min_telemetry_samples", 100),
        )
        self.phase = DescentPhase.IDLE
        self._deploy_time: float = 0.0
        self._telemetry: list[DescentTelemetry] = []
        self._descent_rates: list[float] = []
        self._max_altitude_m: float = 0.0

    async def initialize(self) -> bool:
        self.logger.info(
            "Descent controller initialized: deploy@%.0fm, target=%.1fm/s",
            self.descent_config.deploy_altitude_m,
            self.descent_config.target_descent_rate_m_s,
        )
        self.status = ModuleStatus.READY
        return True

    async def start(self) -> None:
        self.status = ModuleStatus.RUNNING

    async def stop(self) -> None:
        self.status = ModuleStatus.STOPPED

    async def get_status(self) -> dict[str, Any]:
        return {
            "status": self.status.name,
            "phase": self.phase.name,
            "parachute_deployed": self.phase in (
                DescentPhase.DEPLOYED, DescentPhase.DESCENDING, DescentPhase.LANDED
            ),
            "telemetry_samples": len(self._telemetry),
            "max_altitude_m": self._max_altitude_m,
            "error_count": self._error_count,
        }

    def arm(self) -> bool:
        """Arm the descent controller for deployment."""
        if self.phase not in (DescentPhase.IDLE, DescentPhase.ARMED):
            self.logger.warning("Cannot arm in phase %s", self.phase.name)
            return False
        self.phase = DescentPhase.ARMED
        self.logger.info("Descent controller ARMED")
        return True

    def update(self, altitude_agl_m: float, descent_rate_m_s: float,
               accel_g: float = 1.0) -> DescentTelemetry:
        """Update descent state with current sensor data.

        Args:
            altitude_agl_m: Current altitude above ground level.
            descent_rate_m_s: Current descent rate (positive = descending).
            accel_g: Current acceleration magnitude in g.

        Returns:
            DescentTelemetry snapshot.
        """
        if altitude_agl_m > self._max_altitude_m:
            self._max_altitude_m = altitude_agl_m

        # State transitions
        if self.phase == DescentPhase.ARMED:
            if accel_g < self.descent_config.deploy_accel_threshold_g:
                self.phase = DescentPhase.DEPLOY_READY
                self.logger.info("Low-g detected, deployment ready")

        elif self.phase == DescentPhase.DEPLOY_READY:
            if altitude_agl_m <= self.descent_config.deploy_altitude_m:
                self._deploy_parachute()

        elif self.phase == DescentPhase.DEPLOYED:
            time_since = time.time() - self._deploy_time
            if time_since > self.descent_config.deploy_delay_s:
                self.phase = DescentPhase.DESCENDING
                self.logger.info("Descent phase active")

        elif self.phase == DescentPhase.DESCENDING:
            self._descent_rates.append(abs(descent_rate_m_s))
            if altitude_agl_m < 2.0 and abs(descent_rate_m_s) < 0.5:
                self.phase = DescentPhase.LANDED
                self.logger.info("Landing detected at %.1fm", altitude_agl_m)

        tlm = DescentTelemetry(
            timestamp=time.time(),
            phase=self.phase,
            altitude_agl_m=altitude_agl_m,
            descent_rate_m_s=descent_rate_m_s,
            time_since_deploy_s=(time.time() - self._deploy_time) if self._deploy_time else 0.0,
            parachute_deployed=self.phase in (
                DescentPhase.DEPLOYED, DescentPhase.DESCENDING, DescentPhase.LANDED
            ),
            samples_collected=len(self._telemetry),
        )
        self._telemetry.append(tlm)
        return tlm

    def _deploy_parachute(self) -> None:
        """Trigger parachute deployment."""
        self.phase = DescentPhase.DEPLOYED
        self._deploy_time = time.time()
        self.logger.info("PARACHUTE DEPLOYED at %.1fm AGL", self._max_altitude_m)

    def validate_competition(self) -> CompetitionResult:
        """Validate descent against competition requirements.

        Returns:
            CompetitionResult with pass/fail and metrics.
        """
        issues: list[str] = []
        cfg = self.descent_config

        # Calculate descent rate stats
        rates = self._descent_rates
        avg_rate = sum(rates) / len(rates) if rates else 0.0
        min_rate = min(rates) if rates else 0.0
        max_rate = max(rates) if rates else 0.0

        # Landing velocity (last few rates)
        landing_v = sum(rates[-5:]) / len(rates[-5:]) if len(rates) >= 5 else avg_rate

        # Flight duration
        if self._telemetry:
            duration = self._telemetry[-1].timestamp - self._telemetry[0].timestamp
        else:
            duration = 0.0

        # Validation checks
        if avg_rate < cfg.min_descent_rate_m_s:
            issues.append(
                f"Descent rate too slow: {avg_rate:.1f} m/s < {cfg.min_descent_rate_m_s} m/s"
            )
        if avg_rate > cfg.max_descent_rate_m_s:
            issues.append(
                f"Descent rate too fast: {avg_rate:.1f} m/s > {cfg.max_descent_rate_m_s} m/s"
            )
        if landing_v > cfg.landing_speed_threshold_m_s:
            issues.append(
                f"Landing too hard: {landing_v:.1f} m/s > {cfg.landing_speed_threshold_m_s} m/s"
            )
        if len(self._telemetry) < cfg.min_telemetry_samples:
            issues.append(
                f"Insufficient telemetry: {len(self._telemetry)} < {cfg.min_telemetry_samples}"
            )

        return CompetitionResult(
            valid=len(issues) == 0,
            descent_rate_avg_m_s=round(avg_rate, 2),
            descent_rate_min_m_s=round(min_rate, 2),
            descent_rate_max_m_s=round(max_rate, 2),
            landing_velocity_m_s=round(landing_v, 2),
            telemetry_count=len(self._telemetry),
            flight_duration_s=round(duration, 1),
            max_altitude_m=round(self._max_altitude_m, 1),
            issues=issues,
        )

    def get_telemetry_history(self) -> list[DescentTelemetry]:
        """Return full descent telemetry history."""
        return list(self._telemetry)
