"""Tests for TelemetryManager."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.telemetry_manager import TelemetryManager


def test_telemetry_manager_init():
    tm = TelemetryManager()
    assert tm is not None


def test_build_packet():
    tm = TelemetryManager()
    packet = tm.build_packet(0x001, b"\x01\x02\x03")
    assert packet is not None
    assert len(packet) > 0
