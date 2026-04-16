"""Tests for the DataLogger module."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.data_logger import DataLogger


def test_data_logger_init():
    dl = DataLogger()
    assert dl is not None
