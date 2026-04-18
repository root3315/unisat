"""Tests for the new 1U-12U CubeSat and CanSat minimal/advanced profiles."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.mission_types import (
    MissionType,
    PlatformCategory,
    build_profile_from_config,
    get_mission_profile,
    list_mission_types,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
TEMPLATE_DIR = REPO_ROOT / "mission_templates"


CUBESAT_SIZES = [
    ("cubesat_1u",   MissionType.CUBESAT_1U,   0.2),
    ("cubesat_1_5u", MissionType.CUBESAT_1_5U, 0.5),
    ("cubesat_2u",   MissionType.CUBESAT_2U,   0.5),
    ("cubesat_3u",   MissionType.CUBESAT_3U,   1.0),
    ("cubesat_6u",   MissionType.CUBESAT_6U,   2.0),
    ("cubesat_12u",  MissionType.CUBESAT_12U,  5.0),
]


@pytest.mark.parametrize("key,mtype,expected_hz", CUBESAT_SIZES)
def test_cubesat_sized_profiles_registered(
    key: str, mtype: MissionType, expected_hz: float,
) -> None:
    profile = get_mission_profile(mtype)
    assert profile.platform == PlatformCategory.CUBESAT
    assert profile.default_telemetry_hz == pytest.approx(expected_hz)
    assert profile.competition.get("form_factor") == key
    # CubeSat profiles always share the LEO phase graph.
    phase_names = {p.name for p in profile.phases}
    assert {"startup", "nominal", "safe_mode"}.issubset(phase_names)


def test_cansat_minimal_uses_lighter_modules() -> None:
    profile = get_mission_profile(MissionType.CANSAT_MINIMAL)
    assert profile.platform == PlatformCategory.CANSAT
    assert "descent_controller" not in profile.core_modules
    assert profile.default_telemetry_hz == pytest.approx(4.0)
    assert profile.competition["max_mass_g"] == 350


def test_cansat_advanced_includes_descent_and_higher_hz() -> None:
    profile = get_mission_profile(MissionType.CANSAT_ADVANCED)
    assert profile.platform == PlatformCategory.CANSAT
    assert "descent_controller" in profile.core_modules
    assert profile.default_telemetry_hz == pytest.approx(20.0)
    assert profile.competition["max_mass_g"] == 500


def test_list_mission_types_covers_all_profiles() -> None:
    types_listed = set(list_mission_types())
    assert {
        "cubesat_1u", "cubesat_1_5u", "cubesat_2u",
        "cubesat_3u", "cubesat_6u", "cubesat_12u",
        "cansat_minimal", "cansat_standard", "cansat_advanced",
    }.issubset(types_listed)


@pytest.mark.parametrize("template_name", [
    "cubesat_1u", "cubesat_1_5u", "cubesat_2u",
    "cubesat_3u", "cubesat_6u", "cubesat_12u",
    "cansat_minimal", "cansat_standard", "cansat_advanced",
])
def test_each_template_builds_into_a_profile(template_name: str) -> None:
    path = TEMPLATE_DIR / f"{template_name}.json"
    config = json.loads(path.read_text(encoding="utf-8"))
    profile = build_profile_from_config(config)
    assert profile.mission_type.value == template_name
    assert profile.phases  # non-empty phase graph
    # The template's form_factor key matches the profile's competition field
    # (for CubeSats) or the satellite.form_factor field (for all).
    ff_key = config["satellite"]["form_factor"]
    if profile.platform == PlatformCategory.CUBESAT:
        assert profile.competition["form_factor"] == ff_key
    else:
        assert profile.competition.get("form_factor", ff_key) == ff_key
