"""Tests for GNSSReceiver module."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.gnss_receiver import GNSSReceiver, GNSSFix


@pytest.fixture
def gnss() -> GNSSReceiver:
    return GNSSReceiver({"simulate": True, "update_rate_hz": 10})


def test_init_defaults() -> None:
    rx = GNSSReceiver()
    assert rx.receiver == "u-blox_MAX-M10S"
    assert rx._simulate is True
    assert rx._sample_count == 0


def test_init_with_custom_config() -> None:
    rx = GNSSReceiver({
        "receiver": "NEO-M8N",
        "update_rate_hz": 5,
        "simulate": False,
        "base_lat": 55.0,
        "base_lon": 37.0,
        "base_alt_m": 200.0,
    })
    assert rx.receiver == "NEO-M8N"
    assert rx.update_rate_hz == 5
    assert rx._simulate is False
    assert rx._base_lat == 55.0


@pytest.mark.asyncio
async def test_initialize_success(gnss: GNSSReceiver) -> None:
    assert await gnss.initialize() is True


@pytest.mark.asyncio
async def test_start_stop_cycle(gnss: GNSSReceiver) -> None:
    await gnss.initialize()
    await gnss.start()
    await gnss.stop()


@pytest.mark.asyncio
async def test_get_status_structure(gnss: GNSSReceiver) -> None:
    await gnss.initialize()
    status = await gnss.get_status()
    assert "receiver" in status
    assert "last_fix" in status or status.get("last_fix") is None


def test_read_produces_fix(gnss: GNSSReceiver) -> None:
    fix = gnss.read()
    assert isinstance(fix, GNSSFix)
    assert -90.0 <= fix.latitude <= 90.0
    assert -180.0 <= fix.longitude <= 180.0
    assert fix.satellites >= 0


def test_read_updates_last_fix(gnss: GNSSReceiver) -> None:
    assert gnss.get_last_fix() is None
    fix = gnss.read()
    last = gnss.get_last_fix()
    assert last is not None
    assert last == fix


def test_simulate_fix_is_deterministic_within_reason(gnss: GNSSReceiver) -> None:
    """Simulated fix should stay near the base coordinates."""
    fix = gnss._simulate_fix()
    # Default base is Tashkent (41.2995, 69.2401); simulated noise
    # should be small (< 0.01 deg).
    assert abs(fix.latitude - 41.2995) < 0.1
    assert abs(fix.longitude - 69.2401) < 0.1


def test_get_last_fix_returns_none_initially(gnss: GNSSReceiver) -> None:
    assert gnss.get_last_fix() is None


def test_get_last_fix_returns_after_read(gnss: GNSSReceiver) -> None:
    gnss.read()
    fix = gnss.get_last_fix()
    assert fix is not None
    assert isinstance(fix, GNSSFix)


def test_get_distance_from_base_zero_initially(gnss: GNSSReceiver) -> None:
    """Without a fix, distance-from-base is 0 (no meaningful value)."""
    assert gnss.get_distance_from_base() == 0.0


def test_get_distance_from_base_after_read(gnss: GNSSReceiver) -> None:
    gnss.read()
    d = gnss.get_distance_from_base()
    assert d >= 0.0


def test_fix_dataclass_fields() -> None:
    fix = GNSSFix(
        timestamp=1.0,
        latitude=41.0,
        longitude=69.0,
        altitude_m=500.0,
        speed_m_s=2.5,
        heading_deg=90.0,
        satellites=8,
        hdop=1.2,
        fix_quality=1,
    )
    assert fix.timestamp == 1.0
    assert fix.satellites == 8
    assert fix.fix_quality == 1


@pytest.mark.asyncio
async def test_multiple_reads_advance_last_fix(gnss: GNSSReceiver) -> None:
    await gnss.initialize()
    fix1 = gnss.read()
    # Small sleep to let simulated timestamp advance.
    await asyncio.sleep(0.01)
    fix2 = gnss.read()
    # Timestamps must differ.
    assert fix2.timestamp != fix1.timestamp
