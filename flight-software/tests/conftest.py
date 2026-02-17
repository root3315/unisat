"""Test configuration and shared fixtures for flight software tests."""

import sys
from pathlib import Path

import pytest

# Add flight-software to path
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def sample_config() -> dict:
    """Minimal mission config for testing."""
    return {
        "mission": {"name": "UniSat-Test", "version": "0.1.0"},
        "orbit": {"altitude_km": 550, "inclination_deg": 97.6, "type": "SSO"},
        "subsystems": {
            "obc": {"enabled": True},
            "eps": {"enabled": True, "solar_panels": 6, "panel_efficiency": 0.295},
            "comm": {"enabled": True},
            "adcs": {"enabled": True},
            "gnss": {"enabled": True},
            "camera": {"enabled": False},
            "payload": {"enabled": True, "type": "radiation_monitor"},
        },
    }
