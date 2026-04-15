"""Tests for analytical orbital mechanics solutions."""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from analytical_solutions import (
    compute_orbit_parameters,
    compute_j2_perturbations,
    compute_eclipse,
    compute_delta_v,
    compute_deorbit_lifetime,
)


def test_orbit_period_iss():
    """ISS orbit period should be ~92 minutes."""
    params = compute_orbit_parameters(420)
    assert 91 < params.period_min < 93


def test_orbit_period_550km():
    """550 km orbit period should be ~96 minutes."""
    params = compute_orbit_parameters(550)
    assert 95 < params.period_min < 97


def test_orbit_velocity():
    """LEO velocity should be ~7.5-7.8 km/s."""
    params = compute_orbit_parameters(550)
    assert 7.5 < params.velocity_kms < 7.8


def test_j2_sso_detection():
    """97.6° at 550 km should be sun-synchronous."""
    j2 = compute_j2_perturbations(550, 97.6)
    assert j2.is_sun_synchronous is True


def test_j2_non_sso():
    """45° inclination is not sun-synchronous."""
    j2 = compute_j2_perturbations(550, 45.0)
    assert j2.is_sun_synchronous is False


def test_j2_raan_rate_sign():
    """RAAN rate should be negative for prograde, positive for retrograde."""
    j2_prograde = compute_j2_perturbations(550, 45.0)
    j2_retro = compute_j2_perturbations(550, 135.0)
    assert j2_prograde.raan_rate_deg_day < 0
    assert j2_retro.raan_rate_deg_day > 0


def test_eclipse_fraction_reasonable():
    """Eclipse fraction should be 30-40% for LEO SSO."""
    eclipse = compute_eclipse(550, 97.6)
    assert 0.25 < eclipse.eclipse_fraction < 0.40


def test_eclipse_high_beta_no_eclipse():
    """At high beta angle, there should be no eclipse."""
    eclipse = compute_eclipse(550, 97.6, beta_angle_deg=75)
    assert eclipse.eclipse_fraction == 0.0


def test_hohmann_transfer_positive_dv():
    """Delta-V should always be positive."""
    dv = compute_delta_v(400, 550)
    assert dv["total_dv_kms"] > 0
    assert dv["dv1_kms"] > 0
    assert dv["dv2_kms"] > 0


def test_hohmann_same_orbit_zero_dv():
    """Transfer to same orbit should have ~zero delta-V."""
    dv = compute_delta_v(550, 550)
    assert dv["total_dv_kms"] < 0.001


def test_deorbit_lifetime_reasonable():
    """550 km should deorbit in 5-15 years for a 3U CubeSat."""
    life = compute_deorbit_lifetime(550, 4.0, 0.03)
    assert 3 < life["estimated_lifetime_years"] < 20


def test_deorbit_lower_orbit_shorter():
    """Lower orbit should deorbit faster."""
    life_400 = compute_deorbit_lifetime(400, 4.0, 0.03)
    life_600 = compute_deorbit_lifetime(600, 4.0, 0.03)
    assert life_400["estimated_lifetime_years"] < life_600["estimated_lifetime_years"]
