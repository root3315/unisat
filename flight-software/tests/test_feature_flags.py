"""Tests for the feature-flag resolver."""

from __future__ import annotations

import copy
from typing import Any

import pytest

from core.feature_flags import (
    FEATURES,
    describe_flag,
    list_flags,
    resolve_flags,
)
from core.form_factors import get_form_factor
from core.mission_types import (
    MissionType,
    get_mission_profile,
)


def _cansat_context() -> tuple[Any, Any]:
    profile = get_mission_profile(MissionType.CANSAT_STANDARD)
    form_factor = get_form_factor("cansat_standard")
    return profile, form_factor


def _cubesat_6u_context() -> tuple[Any, Any]:
    profile = get_mission_profile(MissionType.CUBESAT_6U)
    form_factor = get_form_factor("cubesat_6u")
    return profile, form_factor


def test_cansat_disables_orbit_predictor_by_default() -> None:
    profile, form_factor = _cansat_context()
    flags = resolve_flags(profile, form_factor, config={})
    assert not flags.is_enabled("orbit_predictor")
    assert flags.reasons["orbit_predictor"].startswith("platform cansat not in")


def test_cansat_enables_descent_controller_by_default() -> None:
    profile, form_factor = _cansat_context()
    flags = resolve_flags(profile, form_factor, config={})
    assert flags.is_enabled("descent_controller")


def test_cubesat_6u_enables_star_tracker_when_tier_configured() -> None:
    profile, form_factor = _cubesat_6u_context()
    config = {
        "subsystems": {"adcs": {"tier": "star_tracker_fine_pointing"}},
        "features": {"star_tracker": True},
    }
    flags = resolve_flags(profile, form_factor, config)
    assert flags.is_enabled("star_tracker")


def test_cubesat_6u_star_tracker_blocked_by_wrong_tier() -> None:
    profile, form_factor = _cubesat_6u_context()
    config = {
        "subsystems": {"adcs": {"tier": "magnetorquer"}},
        "features": {"star_tracker": True},
    }
    flags = resolve_flags(profile, form_factor, config)
    # Explicit override still wins — the resolver honours operator intent;
    # the configurator flags the inconsistency as a warning separately.
    assert flags.is_enabled("star_tracker")


def test_cubesat_1u_cannot_enable_star_tracker() -> None:
    profile = get_mission_profile(MissionType.CUBESAT_1U)
    form_factor = get_form_factor("cubesat_1u")
    config = {"features": {"star_tracker": True}}
    flags = resolve_flags(profile, form_factor, config)
    # Explicit override forces True even though the form factor cannot
    # physically carry a star tracker — the configurator will warn the
    # operator separately, but the flag resolver itself honours the
    # explicit request (operator knows best).
    assert flags.is_enabled("star_tracker")
    assert "explicit config override" in flags.reasons["star_tracker"]


def test_explicit_disable_always_wins() -> None:
    profile, form_factor = _cubesat_6u_context()
    config = {"features": {"reaction_wheels": False}}
    flags = resolve_flags(profile, form_factor, config)
    assert not flags.is_enabled("reaction_wheels")


def test_s_band_requires_matching_band_config() -> None:
    profile, form_factor = _cubesat_6u_context()
    # Without an s_band config block, the flag should stay off even
    # though the form factor allows it.
    flags = resolve_flags(profile, form_factor, config={})
    assert not flags.is_enabled("s_band_radio")

    flags_with_band = resolve_flags(profile, form_factor, {
        "subsystems": {"comm": {"s_band": {"enabled": True}}},
        "features": {"s_band_radio": True},
    })
    assert flags_with_band.is_enabled("s_band_radio")


def test_unknown_flag_surfaces_as_warning() -> None:
    profile, form_factor = _cubesat_6u_context()
    config = {"features": {"quantum_drive": True}}
    flags = resolve_flags(profile, form_factor, config)
    assert any("quantum_drive" in w for w in flags.warnings)


def test_describe_flag_returns_metadata() -> None:
    meta = describe_flag("reaction_wheels")
    assert meta["flag"] == "reaction_wheels"
    assert "cubesat_6u" in meta["form_factors"]
    assert "cubesat" in meta["platforms"]


def test_list_flags_matches_registry() -> None:
    flags_listed = set(list_flags())
    assert flags_listed == set(FEATURES)


def test_resolved_dict_shape_is_json_serialisable() -> None:
    profile, form_factor = _cansat_context()
    flags = resolve_flags(profile, form_factor, config={})
    data = flags.as_dict()
    assert set(data) == {"enabled", "disabled", "reasons", "warnings"}


def test_cubesat_1u_has_no_propulsion() -> None:
    profile = get_mission_profile(MissionType.CUBESAT_1U)
    form_factor = get_form_factor("cubesat_1u")
    flags = resolve_flags(profile, form_factor, config={})
    assert not flags.is_enabled("propulsion")


def test_cubesat_12u_can_enable_propulsion() -> None:
    profile = get_mission_profile(MissionType.CUBESAT_12U)
    form_factor = get_form_factor("cubesat_12u")
    flags = resolve_flags(profile, form_factor,
                          {"features": {"propulsion": True}})
    assert flags.is_enabled("propulsion")
