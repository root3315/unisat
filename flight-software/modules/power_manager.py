"""
Power Manager — Track consumption and manage load shedding.

Monitors power budget per subsystem and sheds loads when
battery SOC drops below configurable thresholds.
"""

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any

from modules import BaseModule, ModuleStatus


class PowerPriority(IntEnum):
    """Subsystem power priority (higher value = kept longer)."""

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
    """Power profile for a single subsystem.

    Attributes:
        name: Subsystem identifier.
        nominal_w: Nominal power draw in watts.
        peak_w: Peak power draw in watts.
        priority: Load-shedding priority (higher = kept longer).
        enabled: Whether the subsystem is currently powered.
    """

    name: str
    nominal_w: float
    peak_w: float
    priority: int
    enabled: bool = True


@dataclass
class PowerBudget:
    """Current power budget snapshot.

    Attributes:
        solar_generation_w: Current solar generation in watts.
        battery_soc_pct: Battery state of charge percentage.
        total_consumption_w: Total power consumption in watts.
        net_power_w: Net power (generation - consumption).
        subsystems: Per-subsystem power profiles.
    """

    solar_generation_w: float = 0.0
    battery_soc_pct: float = 100.0
    total_consumption_w: float = 0.0
    net_power_w: float = 0.0
    subsystems: dict[str, SubsystemPower] = field(default_factory=dict)


class PowerManager(BaseModule):
    """Manages satellite power budget and load shedding.

    Attributes:
        budget: Current power budget state.
        soc_low_threshold: SOC percentage to start load shedding.
        soc_critical_threshold: SOC percentage for emergency shedding.
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        """Initialize power manager.

        Args:
            config: Configuration with optional SOC thresholds and
                    subsystem power profiles.
        """
        super().__init__("power_manager", config)
        self.soc_low_threshold: float = self.config.get("soc_low", 30.0)
        self.soc_critical_threshold: float = self.config.get("soc_critical", 15.0)
        self.budget = PowerBudget()
        self._init_subsystems()

    def _init_subsystems(self) -> None:
        """Initialize subsystem power profiles from config or defaults."""
        custom = self.config.get("subsystems", {})
        if custom:
            for name, info in custom.items():
                self.budget.subsystems[name] = SubsystemPower(
                    name=name,
                    nominal_w=info.get("nominal_w", 0.5),
                    peak_w=info.get("peak_w", 0.8),
                    priority=info.get("priority", PowerPriority.PAYLOAD),
                )
            return

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

    async def initialize(self) -> bool:
        """Initialize the power manager.

        Returns:
            True on success.
        """
        self.logger.info(
            "Power manager initialized, %d subsystems, SOC thresholds: low=%.0f%% crit=%.0f%%",
            len(self.budget.subsystems),
            self.soc_low_threshold,
            self.soc_critical_threshold,
        )
        self.status = ModuleStatus.READY
        return True

    async def start(self) -> None:
        """Start the power manager."""
        self.status = ModuleStatus.RUNNING

    async def stop(self) -> None:
        """Stop the power manager."""
        self.status = ModuleStatus.STOPPED
        self.logger.info("Power manager stopped")

    async def get_status(self) -> dict[str, Any]:
        """Return power manager status.

        Returns:
            Dict with budget summary and subsystem states.
        """
        return {
            "status": self.status.name,
            "solar_w": self.budget.solar_generation_w,
            "battery_soc_pct": self.budget.battery_soc_pct,
            "consumption_w": self.budget.total_consumption_w,
            "net_power_w": self.budget.net_power_w,
            "enabled_subsystems": [
                s.name for s in self.budget.subsystems.values() if s.enabled
            ],
            "error_count": self._error_count,
        }

    def update(self, solar_w: float, battery_soc: float) -> PowerBudget:
        """Update power budget with current measurements.

        Args:
            solar_w: Current solar panel generation in watts.
            battery_soc: Battery state of charge percentage (0-100).

        Returns:
            Updated PowerBudget snapshot.
        """
        self.budget.solar_generation_w = solar_w
        self.budget.battery_soc_pct = battery_soc

        total = sum(
            s.nominal_w for s in self.budget.subsystems.values() if s.enabled
        )
        self.budget.total_consumption_w = total
        self.budget.net_power_w = solar_w - total

        if battery_soc < self.soc_critical_threshold:
            self._emergency_shed()
        elif battery_soc < self.soc_low_threshold:
            self._load_shed()

        return self.budget

    def _load_shed(self) -> None:
        """Disable lowest priority subsystems."""
        sorted_subs = sorted(
            self.budget.subsystems.values(),
            key=lambda s: s.priority,
        )
        for sub in sorted_subs:
            if sub.enabled and sub.priority < PowerPriority.GNSS:
                sub.enabled = False
                self.logger.warning("Load shed: disabled %s (SOC low)", sub.name)

    def _emergency_shed(self) -> None:
        """Keep only OBC and COMM active."""
        for sub in self.budget.subsystems.values():
            if sub.priority < PowerPriority.COMM:
                if sub.enabled:
                    sub.enabled = False
                    self.logger.critical("Emergency shed: disabled %s", sub.name)

    def enable_subsystem(self, name: str) -> bool:
        """Re-enable a subsystem after load shedding.

        Args:
            name: Subsystem name to enable.

        Returns:
            True if the subsystem was found and enabled.
        """
        sub = self.budget.subsystems.get(name)
        if sub is None:
            return False
        sub.enabled = True
        self.logger.info("Enabled subsystem: %s", name)
        return True

    def disable_subsystem(self, name: str) -> bool:
        """Manually disable a subsystem.

        Args:
            name: Subsystem name to disable.

        Returns:
            True if the subsystem was found and disabled.
        """
        sub = self.budget.subsystems.get(name)
        if sub is None or name == "OBC":
            return False
        sub.enabled = False
        self.logger.info("Disabled subsystem: %s", name)
        return True

    def get_consumption(self) -> float:
        """Get total current power consumption in watts.

        Returns:
            Sum of nominal power for all enabled subsystems.
        """
        return sum(
            s.nominal_w for s in self.budget.subsystems.values() if s.enabled
        )
