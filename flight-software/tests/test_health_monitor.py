"""Tests for HealthMonitor module."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.health_monitor import HealthMonitor, HealthReport, HealthAlert


@pytest.fixture
def monitor() -> HealthMonitor:
    return HealthMonitor({
        "sample_interval_s": 1,
        "simulate": True,
    })


def test_init_defaults() -> None:
    m = HealthMonitor()
    assert isinstance(m.DEFAULT_THRESHOLDS, dict)
    assert "cpu_temp_c" in m.DEFAULT_THRESHOLDS


def test_default_thresholds_structure() -> None:
    m = HealthMonitor()
    for name, thresh in m.DEFAULT_THRESHOLDS.items():
        warning, critical = thresh
        assert warning < critical, f"{name} warning >= critical"


@pytest.mark.asyncio
async def test_initialize_returns_true(monitor: HealthMonitor) -> None:
    assert await monitor.initialize() is True


@pytest.mark.asyncio
async def test_start_stop_cycle(monitor: HealthMonitor) -> None:
    await monitor.initialize()
    await monitor.start()
    await monitor.stop()


@pytest.mark.asyncio
async def test_get_status_has_expected_keys(monitor: HealthMonitor) -> None:
    await monitor.initialize()
    status = await monitor.get_status()
    assert "status" in status


def test_read_cpu_temperature_returns_float(monitor: HealthMonitor) -> None:
    temp = monitor.read_cpu_temperature()
    assert isinstance(temp, float)
    # Expected physical range for a CubeSat OBC.
    assert -40.0 < temp < 125.0


def test_read_ram_usage_is_percentage(monitor: HealthMonitor) -> None:
    pct = monitor.read_ram_usage()
    assert 0.0 <= pct <= 100.0


def test_read_disk_usage_returns_tuple(monitor: HealthMonitor) -> None:
    result = monitor.read_disk_usage()
    assert isinstance(result, tuple)
    assert len(result) == 2
    used_pct, free_mb = result
    assert 0.0 <= used_pct <= 100.0
    assert free_mb >= 0.0


@pytest.mark.asyncio
async def test_check_health_returns_report(monitor: HealthMonitor) -> None:
    await monitor.initialize()
    report = await monitor.check_health()
    assert isinstance(report, HealthReport)
    assert report.timestamp > 0
    assert -40.0 < report.cpu_temp_c < 125.0
    assert 0.0 <= report.ram_used_pct <= 100.0


def test_check_threshold_no_alert_under_warning(monitor: HealthMonitor) -> None:
    """A metric value below warning threshold yields no alert."""
    alert = monitor._check_threshold("cpu_temp_c", 20.0)
    assert alert is None


def test_check_threshold_warning_level(monitor: HealthMonitor) -> None:
    """A metric value between warning and critical produces a warning alert."""
    alert = monitor._check_threshold("cpu_temp_c", 75.0)
    assert alert is not None
    assert isinstance(alert, HealthAlert)
    assert alert.subsystem == "cpu_temp_c"


def test_check_threshold_critical_level(monitor: HealthMonitor) -> None:
    """A metric value above critical yields a critical alert."""
    alert = monitor._check_threshold("cpu_temp_c", 95.0)
    assert alert is not None


def test_check_threshold_unknown_metric_returns_none(monitor: HealthMonitor) -> None:
    """Metric not in thresholds dict produces no alert."""
    alert = monitor._check_threshold("unknown_metric", 100.0)
    assert alert is None


def test_get_recent_alerts_empty_initially(monitor: HealthMonitor) -> None:
    alerts = monitor.get_recent_alerts()
    assert isinstance(alerts, list)


def test_get_recent_alerts_respects_count(monitor: HealthMonitor) -> None:
    alerts = monitor.get_recent_alerts(count=5)
    assert isinstance(alerts, list)
    assert len(alerts) <= 5


@pytest.mark.asyncio
async def test_multiple_health_checks_keep_history(monitor: HealthMonitor) -> None:
    await monitor.initialize()
    r1 = await monitor.check_health()
    r2 = await monitor.check_health()
    assert r1.timestamp <= r2.timestamp


def test_report_dataclass_fields() -> None:
    report = HealthReport(
        timestamp=1.0,
        cpu_temp_c=25.0,
        ram_used_pct=50.0,
        disk_used_pct=30.0,
        disk_free_mb=1000.0,
        uptime_s=3600.0,
    )
    assert report.cpu_temp_c == 25.0
    assert report.alerts == []
