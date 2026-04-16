"""Tests for OrbitPredictor module."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.orbit_predictor import OrbitPredictor


def test_orbit_predictor_init():
    op = OrbitPredictor()
    assert op is not None


def test_predict_passes():
    op = OrbitPredictor()
    passes = op.predict_passes(41.3, 69.2)
    assert isinstance(passes, list)
