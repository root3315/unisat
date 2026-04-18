"""Tests for the form-factor registry."""

from __future__ import annotations

import pytest

from core.form_factors import (
    FormFactorClass,
    get_form_factor,
    list_by_family,
    list_form_factors,
    summarise,
)


def test_registry_enumerates_expected_keys() -> None:
    keys = set(list_form_factors())
    expected = {
        "cansat_minimal", "cansat_standard", "cansat_advanced",
        "cubesat_1u", "cubesat_1_5u", "cubesat_2u",
        "cubesat_3u", "cubesat_6u", "cubesat_12u",
        "rocket_payload", "hab_payload", "drone_small", "rover_small",
        "custom",
    }
    missing = expected - keys
    assert not missing, f"missing form factors in registry: {missing}"


def test_list_by_family_returns_cubesats() -> None:
    cubesats = list_by_family(FormFactorClass.CUBESAT)
    keys = {f.key for f in cubesats}
    assert keys == {"cubesat_1u", "cubesat_1_5u", "cubesat_2u",
                    "cubesat_3u", "cubesat_6u", "cubesat_12u"}


@pytest.mark.parametrize("key,max_kg", [
    ("cansat_minimal", 0.35),
    ("cansat_standard", 0.50),
    ("cansat_advanced", 0.50),
])
def test_cansat_mass_envelope_matches_regulation(key: str, max_kg: float) -> None:
    f = get_form_factor(key)
    assert f.mass.max_kg == pytest.approx(max_kg)
    assert f.family == FormFactorClass.CANSAT


@pytest.mark.parametrize("key,max_kg", [
    ("cubesat_1u", 2.0),
    ("cubesat_2u", 4.0),
    ("cubesat_3u", 6.0),
    ("cubesat_6u", 12.0),
    ("cubesat_12u", 24.0),
])
def test_cubesat_mass_limits_follow_cds_rev14(key: str, max_kg: float) -> None:
    f = get_form_factor(key)
    assert f.mass.max_kg == pytest.approx(max_kg)


def test_check_mass_flags_over_envelope() -> None:
    cansat = get_form_factor("cansat_standard")
    ok, msg = cansat.check_mass(0.48)
    assert ok, msg
    ok, msg = cansat.check_mass(0.55)
    assert not ok and "exceeds" in msg


def test_cubesat_12u_allows_star_tracker_not_1u() -> None:
    assert get_form_factor("cubesat_12u").is_adcs_tier_supported(
        "star_tracker_fine_pointing")
    assert not get_form_factor("cubesat_1u").is_adcs_tier_supported(
        "star_tracker_fine_pointing")


def test_cansat_does_not_allow_reaction_wheels() -> None:
    for key in ("cansat_minimal", "cansat_standard", "cansat_advanced"):
        ff = get_form_factor(key)
        assert not ff.is_adcs_tier_supported("reaction_wheels_3axis")


def test_summarise_produces_json_friendly_dict() -> None:
    data = summarise(get_form_factor("cubesat_6u"))
    assert data["key"] == "cubesat_6u"
    assert data["mass"]["max_kg"] == 12.0
    assert "s_band" in data["comm_bands"]
    assert "star_tracker_fine_pointing" in data["adcs_tiers"]


def test_unknown_form_factor_raises() -> None:
    with pytest.raises(KeyError):
        get_form_factor("cubesat_42u")


def test_custom_form_factor_is_permissive() -> None:
    ff = get_form_factor("custom")
    assert ff.supports_propulsion
    assert ff.check_mass(0.0)[0]
    assert ff.check_mass(500.0)[0]
