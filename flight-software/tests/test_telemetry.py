"""Tests for TelemetryManager."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.telemetry_manager import TelemetryManager


def test_telemetry_manager_init():
    tm = TelemetryManager()
    assert tm is not None


def test_build_housekeeping_packet():
    tm = TelemetryManager()
    health = {"cpu_temp_c": 35.0, "ram_usage_pct": 45.0, "disk_usage_pct": 12.0}
    packet = tm.build_housekeeping_packet(health)
    assert packet is not None
    assert len(packet) > 0
