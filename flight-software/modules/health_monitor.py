"""Health Monitor for UniSat CubeSat.

Monitors CPU temperature, RAM usage, disk space, and other system metrics.
Generates threshold-based alerts and periodic health reports.
"""

from __future__ import annotations

import os
import platform
import shutil
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Any

from modules import BaseModule, ModuleStatus


class AlertLevel(Enum):
    """Severity level for health alerts."""

    INFO = auto()
    WARNING = auto()
    CRITICAL = auto()


@dataclass
class HealthAlert:
    """A health monitoring alert.

    Attributes:
        level: Severity of the alert.
        subsystem: Which subsystem generated the alert.
        message: Human-readable description.
        value: The metric value that triggered the alert.
        threshold: The threshold that was exceeded.
        timestamp: When the alert was generated.
    """

    level: AlertLevel
    subsystem: str
    message: str
    value: float
    threshold: float
    timestamp: float = field(default_factory=time.time)


@dataclass
class HealthReport:
    """Periodic health status report.

    Attributes:
        timestamp: Report generation time.
        cpu_temp_c: CPU temperature in Celsius.
        ram_used_pct: RAM usage percentage.
        disk_used_pct: Disk usage percentage.
        disk_free_mb: Free disk space in MB.
        uptime_s: System uptime in seconds.
        alerts: List of active alerts.
    """

    timestamp: float
    cpu_temp_c: float
    ram_used_pct: float
    disk_used_pct: float
    disk_free_mb: float
    uptime_s: float
    alerts: list[HealthAlert] = field(default_factory=list)


class HealthMonitor(BaseModule):
    """Monitors system health metrics and generates alerts.

    Attributes:
        thresholds: Dict of metric name to (warning, critical) threshold pairs.
        alerts: History of generated alerts.
        reports: History of generated reports.
    """

    DEFAULT_THRESHOLDS: dict[str, tuple[float, float]] = {
        "cpu_temp_c": (70.0, 85.0),
        "ram_used_pct": (80.0, 95.0),
        "disk_used_pct": (85.0, 95.0),
    }

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        """Initialize the health monitor.

        Args:
            config: Configuration with optional 'thresholds' overrides and 'disk_path'.
        """
        super().__init__("health_monitor", config)
        self.thresholds = dict(self.DEFAULT_THRESHOLDS)
        custom = self.config.get("thresholds", {})
        for key, val in custom.items():
            if isinstance(val, (list, tuple)) and len(val) == 2:
                self.thresholds[key] = (float(val[0]), float(val[1]))
        self.disk_path: str = self.config.get("disk_path", "/")
        self.alerts: list[HealthAlert] = []
        self.reports: list[HealthReport] = []
        self._start_time: float = time.time()
        self._max_alerts: int = 1000
        self._max_reports: int = 500

    async def initialize(self) -> bool:
        """Initialize the health monitor.

        Returns:
            Always True.
        """
        self._start_time = time.time()
        self.status = ModuleStatus.READY
        self.logger.info("Health monitor initialized with thresholds: %s", self.thresholds)
        return True

    async def start(self) -> None:
        """Start the health monitor."""
        self.status = ModuleStatus.RUNNING

    async def stop(self) -> None:
        """Stop the health monitor."""
        self.status = ModuleStatus.STOPPED
        self.logger.info("Health monitor stopped, %d alerts generated", len(self.alerts))

    async def get_status(self) -> dict[str, Any]:
        """Return health monitor status.

        Returns:
            Dict with alert count and latest metrics.
        """
        return {
            "status": self.status.name,
            "total_alerts": len(self.alerts),
            "total_reports": len(self.reports),
            "uptime_s": round(time.time() - self._start_time, 1),
            "error_count": self._error_count,
        }

    def read_cpu_temperature(self) -> float:
        """Read the CPU temperature.

        On Linux, reads from /sys/class/thermal. On other platforms,
        returns a simulated value based on uptime variation.

        Returns:
            CPU temperature in Celsius.
        """
        thermal_path = Path("/sys/class/thermal/thermal_zone0/temp")
        if thermal_path.exists():
            raw = thermal_path.read_text().strip()
            return float(raw) / 1000.0
        uptime = time.time() - self._start_time
        base_temp = 35.0 + (uptime % 600) / 60.0
        return round(base_temp, 1)

    def read_ram_usage(self) -> float:
        """Read RAM usage percentage.

        On Linux, parses /proc/meminfo. On other platforms, uses os-level
        estimation.

        Returns:
            RAM usage as a percentage (0-100).
        """
        meminfo_path = Path("/proc/meminfo")
        if meminfo_path.exists():
            lines = meminfo_path.read_text().splitlines()
            mem: dict[str, int] = {}
            for line in lines:
                parts = line.split()
                if len(parts) >= 2:
                    key = parts[0].rstrip(":")
                    mem[key] = int(parts[1])
            total = mem.get("MemTotal", 1)
            available = mem.get("MemAvailable", mem.get("MemFree", 0))
            return round((1 - available / total) * 100, 1)
        import ctypes
        try:
            if platform.system() == "Windows":
                kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]

                class MEMORYSTATUSEX(ctypes.Structure):
                    _fields_ = [
                        ("dwLength", ctypes.c_ulong),
                        ("dwMemoryLoad", ctypes.c_ulong),
                        ("ullTotalPhys", ctypes.c_ulonglong),
                        ("ullAvailPhys", ctypes.c_ulonglong),
                        ("ullTotalPageFile", ctypes.c_ulonglong),
                        ("ullAvailPageFile", ctypes.c_ulonglong),
                        ("ullTotalVirtual", ctypes.c_ulonglong),
                        ("ullAvailVirtual", ctypes.c_ulonglong),
                        ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                    ]

                mem_status = MEMORYSTATUSEX()
                mem_status.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
                kernel32.GlobalMemoryStatusEx(ctypes.byref(mem_status))
                return float(mem_status.dwMemoryLoad)
        except Exception:
            pass
        return 45.0

    def read_disk_usage(self) -> tuple[float, float]:
        """Read disk usage for the configured path.

        Returns:
            Tuple of (usage_percentage, free_mb).
        """
        try:
            usage = shutil.disk_usage(self.disk_path)
            pct = (usage.used / usage.total) * 100
            free_mb = usage.free / (1024 * 1024)
            return round(pct, 1), round(free_mb, 1)
        except OSError:
            return 0.0, 0.0

    def _check_threshold(self, metric: str, value: float) -> HealthAlert | None:
        """Check a metric value against its warning/critical thresholds.

        Args:
            metric: Metric name matching a key in self.thresholds.
            value: Current metric value.

        Returns:
            HealthAlert if a threshold was exceeded, None otherwise.
        """
        thresholds = self.thresholds.get(metric)
        if not thresholds:
            return None
        warn, crit = thresholds
        if value >= crit:
            return HealthAlert(
                level=AlertLevel.CRITICAL, subsystem=metric,
                message=f"{metric} critical: {value:.1f} >= {crit:.1f}",
                value=value, threshold=crit,
            )
        if value >= warn:
            return HealthAlert(
                level=AlertLevel.WARNING, subsystem=metric,
                message=f"{metric} warning: {value:.1f} >= {warn:.1f}",
                value=value, threshold=warn,
            )
        return None

    async def check_health(self) -> HealthReport:
        """Run a full health check and generate a report.

        Returns:
            HealthReport with current metrics and any triggered alerts.
        """
        cpu_temp = self.read_cpu_temperature()
        ram_pct = self.read_ram_usage()
        disk_pct, disk_free = self.read_disk_usage()
        uptime = time.time() - self._start_time
        new_alerts: list[HealthAlert] = []
        for metric, value in [("cpu_temp_c", cpu_temp), ("ram_used_pct", ram_pct),
                              ("disk_used_pct", disk_pct)]:
            alert = self._check_threshold(metric, value)
            if alert:
                new_alerts.append(alert)
                self.logger.warning("Alert: %s", alert.message)
        self.alerts.extend(new_alerts)
        if len(self.alerts) > self._max_alerts:
            self.alerts = self.alerts[-self._max_alerts:]
        report = HealthReport(
            timestamp=time.time(), cpu_temp_c=cpu_temp, ram_used_pct=ram_pct,
            disk_used_pct=disk_pct, disk_free_mb=disk_free,
            uptime_s=round(uptime, 1), alerts=new_alerts,
        )
        self.reports.append(report)
        if len(self.reports) > self._max_reports:
            self.reports = self.reports[-self._max_reports:]
        return report

    def get_recent_alerts(self, count: int = 10) -> list[HealthAlert]:
        """Return the most recent alerts.

        Args:
            count: Number of alerts to return.

        Returns:
            List of recent HealthAlert objects, newest first.
        """
        return list(reversed(self.alerts[-count:]))
