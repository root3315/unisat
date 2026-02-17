"""Tests for OrbitPredictor module."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.orbit_predictor import OrbitPredictor


def test_orbit_predictor_init():
    op = OrbitPredictor()
    assert op is not None


def test_get_position():
    op = OrbitPredictor()
    pos = op.get_current_position()
    assert "latitude" in pos
    assert "longitude" in pos
    assert -90 <= pos["latitude"] <= 90
    assert -180 <= pos["longitude"] <= 180
