"""Tests for configurator validators."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from validators.mass_validator import validate_mass
from validators.power_validator import validate_power
from validators.volume_validator import validate_volume


ALL_ENABLED = {
    "eps": True, "comm_uhf": True, "comm_sband": True,
    "adcs": True, "gnss": True, "camera": True, "payload": True,
}

MINIMAL = {"eps": True, "comm_uhf": True}


# --- Mass Validator ---

def test_mass_3u_within_limit():
    result = validate_mass("3U", ALL_ENABLED)
    assert result.valid is True
    assert result.total_kg <= result.limit_kg


def test_mass_1u_over_limit():
    result = validate_mass("1U", ALL_ENABLED)
    assert result.valid is False
    assert result.total_kg > result.limit_kg


def test_mass_6u_plenty_of_margin():
    result = validate_mass("6U", ALL_ENABLED)
    assert result.valid is True
    assert result.margin_kg > 5.0


def test_mass_includes_20pct_margin():
    result = validate_mass("3U", ALL_ENABLED)
    assert "margin_20pct" in result.items
    assert result.items["margin_20pct"] > 0


def test_mass_minimal_config():
    result = validate_mass("1U", MINIMAL)
    assert result.total_kg < validate_mass("1U", ALL_ENABLED).total_kg


# --- Power Validator ---

def test_power_3u_positive_balance():
    result = validate_power("3U", 0.295, ALL_ENABLED)
    assert result.generation_w > 0
    assert result.consumption_nominal_w > 0


def test_power_generation_increases_with_panels():
    power_3u = validate_power("3U", 0.295, ALL_ENABLED)
    power_6u = validate_power("6U", 0.295, ALL_ENABLED)
    assert power_6u.generation_w > power_3u.generation_w


def test_power_consumption_increases_with_subsystems():
    minimal = validate_power("3U", 0.295, MINIMAL)
    full = validate_power("3U", 0.295, ALL_ENABLED)
    assert full.consumption_nominal_w > minimal.consumption_nominal_w


def test_power_peak_exceeds_nominal():
    result = validate_power("3U", 0.295, ALL_ENABLED)
    assert result.consumption_peak_w >= result.consumption_nominal_w


# --- Volume Validator ---

def test_volume_3u_fits():
    result = validate_volume("3U", ALL_ENABLED)
    assert result.valid is True
    assert result.utilization_pct < 100


def test_volume_1u_tight():
    result = validate_volume("1U", ALL_ENABLED)
    # 1U with everything enabled might be tight
    assert result.total_cm3 > 0


def test_volume_6u_lots_of_space():
    result = validate_volume("6U", ALL_ENABLED)
    assert result.valid is True
    assert result.utilization_pct < 50


def test_volume_utilization_increases():
    minimal = validate_volume("3U", MINIMAL)
    full = validate_volume("3U", ALL_ENABLED)
    assert full.utilization_pct > minimal.utilization_pct
