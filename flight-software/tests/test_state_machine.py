"""Tests for the configurable StateMachine."""

import asyncio
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.state_machine import StateMachine
from core.mission_types import (
    MissionProfile, MissionType, PlatformCategory, PhaseDefinition,
    get_mission_profile,
)


def _simple_profile() -> MissionProfile:
    """Create a minimal test profile."""
    return MissionProfile(
        mission_type=MissionType.CUSTOM,
        platform=PlatformCategory.CUSTOM,
        phases=[
            PhaseDefinition(name="startup", transitions_to=["nominal", "safe"]),
            PhaseDefinition(name="nominal", transitions_to=["science", "safe"]),
            PhaseDefinition(name="science", transitions_to=["nominal", "safe"]),
            PhaseDefinition(name="safe", transitions_to=["nominal"]),
        ],
        initial_phase="startup",
    )


def _timeout_profile() -> MissionProfile:
    """Profile with timeout transitions."""
    return MissionProfile(
        mission_type=MissionType.CUSTOM,
        platform=PlatformCategory.CUSTOM,
        phases=[
            PhaseDefinition(name="a", transitions_to=["b"], timeout_s=0.1, auto_next="b"),
            PhaseDefinition(name="b", transitions_to=["a"]),
        ],
        initial_phase="a",
    )


def test_initial_phase():
    sm = StateMachine(_simple_profile())
    assert sm.phase_name == "startup"


@pytest.mark.asyncio
async def test_valid_transition():
    sm = StateMachine(_simple_profile())
    ok = await sm.transition_to("nominal", reason="test")
    assert ok
    assert sm.phase_name == "nominal"


@pytest.mark.asyncio
async def test_invalid_transition():
    sm = StateMachine(_simple_profile())
    ok = await sm.transition_to("science")  # startup can't go to science
    assert not ok
    assert sm.phase_name == "startup"


@pytest.mark.asyncio
async def test_unknown_phase():
    sm = StateMachine(_simple_profile())
    ok = await sm.transition_to("nonexistent")
    assert not ok


@pytest.mark.asyncio
async def test_self_transition():
    sm = StateMachine(_simple_profile())
    ok = await sm.transition_to("startup")
    assert ok  # same-phase transitions always succeed


@pytest.mark.asyncio
async def test_transition_history():
    sm = StateMachine(_simple_profile())
    await sm.transition_to("nominal")
    await sm.transition_to("science")

    assert len(sm.history) == 2
    assert sm.history[0].from_phase == "startup"
    assert sm.history[0].to_phase == "nominal"
    assert sm.history[1].from_phase == "nominal"
    assert sm.history[1].to_phase == "science"


@pytest.mark.asyncio
async def test_guard_veto():
    """Guards can veto transitions."""
    sm = StateMachine(_simple_profile())

    async def deny_all(from_p: str, to_p: str) -> bool:
        return False

    sm.add_guard(deny_all)
    ok = await sm.transition_to("nominal")
    assert not ok
    assert sm.phase_name == "startup"


@pytest.mark.asyncio
async def test_guard_allow():
    """Guards that return True allow transitions."""
    sm = StateMachine(_simple_profile())

    async def allow_all(from_p: str, to_p: str) -> bool:
        return True

    sm.add_guard(allow_all)
    ok = await sm.transition_to("nominal")
    assert ok


def test_timeout_detection():
    """Timeout returns auto_next when phase duration exceeds limit."""
    import time
    sm = StateMachine(_timeout_profile())
    # Initially no timeout
    assert sm.check_timeout() is None
    # Fake elapsed time
    sm.current.entered_at = time.time() - 1.0
    assert sm.check_timeout() == "b"


def test_phase_info():
    sm = StateMachine(_simple_profile())
    info = sm.get_phase_info()
    assert info["phase"] == "startup"
    assert "nominal" in info["transitions_to"]


def test_available_transitions():
    sm = StateMachine(_simple_profile())
    available = sm.get_available_transitions()
    assert set(available) == {"nominal", "safe"}


def test_list_phases():
    sm = StateMachine(_simple_profile())
    phases = sm.list_phases()
    assert len(phases) == 4
    names = [p["name"] for p in phases]
    assert "startup" in names
    assert "safe" in names


def test_cubesat_profile_loads():
    """Built-in CubeSat LEO profile loads and has correct initial phase."""
    profile = get_mission_profile("cubesat_leo")
    sm = StateMachine(profile)
    assert sm.phase_name == "startup"
    assert len(profile.phases) >= 4


def test_cansat_profile_loads():
    """Built-in CanSat profile loads and has correct initial phase."""
    profile = get_mission_profile("cansat_standard")
    sm = StateMachine(profile)
    assert sm.phase_name == "pre_launch"
    phase_names = [p.name for p in profile.phases]
    assert "ascent" in phase_names
    assert "descent" in phase_names


def test_rocket_profile_loads():
    """Built-in rocket profile loads."""
    profile = get_mission_profile("rocket_competition")
    sm = StateMachine(profile)
    assert sm.phase_name == "ground_checkout"


def test_hab_profile_loads():
    """Built-in HAB profile loads."""
    profile = get_mission_profile("hab_standard")
    sm = StateMachine(profile)
    assert sm.phase_name == "ground_setup"


def test_drone_profile_loads():
    """Built-in drone profile loads."""
    profile = get_mission_profile("drone_survey")
    sm = StateMachine(profile)
    assert sm.phase_name == "preflight"


def test_invalid_initial_phase():
    """Profile with unknown initial phase raises ValueError."""
    profile = MissionProfile(
        mission_type=MissionType.CUSTOM,
        platform=PlatformCategory.CUSTOM,
        phases=[PhaseDefinition(name="a")],
        initial_phase="nonexistent",
    )
    with pytest.raises(ValueError):
        StateMachine(profile)
