"""
Power Manager — Track consumption and manage load shedding.

Monitors power budget per subsystem and sheds loads when
battery SOC drops below configurable thresholds.
"""

import logging
from dataclasses import dataclass, field
from enum import IntEnum

logger = logging.getLogger("unisat.power")


class PowerPriority(IntEnum):
    """Subsystem power priority (higher = kept longer)."""
    OBC = 10
    COMM = 9
    ADCS = 7
    GNSS = 6
    HEATER = 5
    PAYLOAD = 4
    CAMERA = 3
    SBAND = 2


@dataclass
class SubsystemPower:
    """Power profile for a single subsystem."""
    name: str
    nominal_w: float
    peak_w: float
    priority: int
    enabled: bool = True


@dataclass
class PowerBudget:
    """Current power budget snapshot."""
    solar_generation_w: float = 0.0
    battery_soc_pct: float = 100.0
    total_consumption_w: float = 0.0
    net_power_w: float = 0.0
    subsystems: dict[str, SubsystemPower] = field(default_factory=dict)


class PowerManager:
    """Manages satellite power budget and load shedding."""

    SOC_LOW_THRESHOLD = 30.0
    SOC_CRITICAL_THRESHOLD = 15.0

    def __init__(self) -> None:
        self.budget = PowerBudget()
        self._init_subsystems()

    def _init_subsystems(self) -> None:
        """Initialize default subsystem power profiles."""
        defaults = [
            SubsystemPower("OBC", 0.5, 0.8, PowerPriority.OBC),
            SubsystemPower("COMM_UHF", 1.0, 1.5, PowerPriority.COMM),
            SubsystemPower("ADCS", 0.8, 1.2, PowerPriority.ADCS),
            SubsystemPower("GNSS", 0.3, 0.4, PowerPriority.GNSS),
            SubsystemPower("CAMERA", 2.0, 3.0, PowerPriority.CAMERA),
            SubsystemPower("PAYLOAD", 0.5, 0.8, PowerPriority.PAYLOAD),
            SubsystemPower("HEATER", 1.0, 2.0, PowerPriority.HEATER),
            SubsystemPower("COMM_SBAND", 2.0, 2.5, PowerPriority.SBAND),
        ]
        for sub in defaults:
            self.budget.subsystems[sub.name] = sub

    def update(self, solar_w: float, battery_soc: float) -> PowerBudget:
        """Update power budget with current measurements."""
        self.budget.solar_generation_w = solar_w
        self.budget.battery_soc_pct = battery_soc

        total = sum(
            s.nominal_w for s in self.budget.subsystems.values() if s.enabled
        )
        self.budget.total_consumption_w = total
        self.budget.net_power_w = solar_w - total

        if battery_soc < self.SOC_CRITICAL_THRESHOLD:
            self._emergency_shed()
        elif battery_soc < self.SOC_LOW_THRESHOLD:
            self._load_shed()

        return self.budget

    def _load_shed(self) -> None:
        """Disable lowest priority subsystems."""
        sorted_subs = sorted(
            self.budget.subsystems.values(),
            key=lambda s: s.priority
        )
        for sub in sorted_subs:
            if sub.enabled and sub.priority < PowerPriority.GNSS:
                sub.enabled = False
                logger.warning("Load shed: disabled %s (SOC low)", sub.name)

    def _emergency_shed(self) -> None:
        """Keep only OBC and COMM active."""
        for sub in self.budget.subsystems.values():
            if sub.priority < PowerPriority.COMM:
                if sub.enabled:
                    sub.enabled = False
                    logger.critical("Emergency shed: disabled %s", sub.name)

    def enable_subsystem(self, name: str) -> bool:
        """Re-enable a subsystem after load shedding."""
        sub = self.budget.subsystems.get(name)
        if sub is None:
            return False
        sub.enabled = True
        logger.info("Enabled subsystem: %s", name)
        return True

    def disable_subsystem(self, name: str) -> bool:
        """Manually disable a subsystem."""
        sub = self.budget.subsystems.get(name)
        if sub is None or name == "OBC":
            return False
        sub.enabled = False
        logger.info("Disabled subsystem: %s", name)
        return True

    def get_consumption(self) -> float:
        """Get total current power consumption in watts."""
        return sum(
            s.nominal_w for s in self.budget.subsystems.values() if s.enabled
        )
