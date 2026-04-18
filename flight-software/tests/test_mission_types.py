"""Tests for mission type registry and profile building."""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.mission_types import (
    MissionType,
    PlatformCategory,
    MissionProfile,
    PhaseDefinition,
    get_mission_profile,
    register_mission_profile,
    list_mission_types,
    build_profile_from_config,
)


def test_list_mission_types():
    """All built-in types are listed."""
    types = list_mission_types()
    assert "cubesat_leo" in types
    assert "cansat_standard" in types
    assert "rocket_competition" in types
    assert "hab_standard" in types
    assert "drone_survey" in types


def test_get_cubesat_profile():
    profile = get_mission_profile("cubesat_leo")
    assert profile.platform == PlatformCategory.CUBESAT
    assert profile.initial_phase == "startup"
    assert len(profile.phases) >= 4
    assert "telemetry" in profile.core_modules


def test_get_cansat_profile():
    profile = get_mission_profile("cansat_standard")
    assert profile.platform == PlatformCategory.CANSAT
    assert profile.initial_phase == "pre_launch"
    assert profile.default_telemetry_hz == 10.0
    assert "imu" in profile.core_modules
    assert "barometer" in profile.core_modules
    assert "descent_rate_range_m_s" in profile.competition


def test_get_rocket_profile():
    profile = get_mission_profile("rocket_competition")
    assert profile.platform == PlatformCategory.SUBORBITAL_ROCKET
    assert profile.default_telemetry_hz == 20.0
    phase_names = [p.name for p in profile.phases]
    assert "boost" in phase_names
    assert "coast" in phase_names
    assert "apogee" in phase_names


def test_get_hab_profile():
    profile = get_mission_profile("hab_standard")
    assert profile.platform == PlatformCategory.HIGH_ALTITUDE_BALLOON
    phase_names = [p.name for p in profile.phases]
    assert "ascent" in phase_names
    assert "float" in phase_names
    assert "burst" in phase_names


def test_get_drone_profile():
    profile = get_mission_profile("drone_survey")
    assert profile.platform == PlatformCategory.DRONE
    phase_names = [p.name for p in profile.phases]
    assert "takeoff" in phase_names
    assert "mission_flight" in phase_names
    assert "return_to_home" in phase_names


def test_unknown_profile_raises():
    with pytest.raises(KeyError):
        get_mission_profile("nonexistent_mission")


def test_register_custom_profile():
    custom = MissionProfile(
        mission_type=MissionType.CUSTOM,
        platform=PlatformCategory.CUSTOM,
        phases=[PhaseDefinition(name="idle")],
        initial_phase="idle",
    )
    register_mission_profile(custom)
    retrieved = get_mission_profile(MissionType.CUSTOM)
    assert retrieved.initial_phase == "idle"


def test_build_profile_from_config_known_type():
    config = {
        "mission": {
            "mission_type": "cansat_standard",
            "telemetry_hz": 20.0,
        }
    }
    profile = build_profile_from_config(config)
    assert profile.platform == PlatformCategory.CANSAT
    assert profile.default_telemetry_hz == 20.0  # overridden


def test_build_profile_from_config_unknown_type():
    config = {
        "mission": {
            "mission_type": "martian_rover",
            "platform": "custom",
        }
    }
    profile = build_profile_from_config(config)
    assert profile.mission_type == MissionType.CUSTOM


def test_build_profile_with_custom_phases():
    config = {
        "mission": {
            "mission_type": "cansat_standard",
            "phases": [
                {"name": "idle", "transitions_to": ["active"]},
                {"name": "active", "transitions_to": ["idle"]},
            ],
            "initial_phase": "idle",
        }
    }
    profile = build_profile_from_config(config)
    assert len(profile.phases) == 2
    assert profile.initial_phase == "idle"


def test_phase_definition_defaults():
    p = PhaseDefinition(name="test_phase")
    assert p.display_name == "Test Phase"
    assert p.entry_event == "phase.test_phase.enter"
    assert p.exit_event == "phase.test_phase.exit"
    assert p.timeout_s == 0.0
    assert p.auto_next == ""


def test_phase_definition_custom_display():
    p = PhaseDefinition(name="boost", display_name="Boost Phase")
    assert p.display_name == "Boost Phase"


def test_cansat_competition_metadata():
    profile = get_mission_profile("cansat_standard")
    assert profile.competition["type"] == "cansat"
    assert profile.competition["max_mass_g"] == 500
    assert profile.competition["outer_diameter_mm"] == 68
    assert profile.competition["inner_diameter_mm"] == 64
    assert profile.competition["height_mm"] == 80
    assert profile.competition["min_telemetry_samples"] == 100
    assert profile.competition["max_landing_velocity_m_s"] == 12.0
