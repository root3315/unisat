"""Tests for CanSat descent controller — parachute, simulation, competition."""

import sys
import math
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from descent_controller import (
    DescentController, DescentConfig, DescentPhase,
    design_parachute, G, RHO_SEA_LEVEL,
)


def _default_controller() -> DescentController:
    config = DescentConfig(cansat_mass_kg=0.350, parachute_diameter_m=0.6)
    return DescentController(config)


def test_terminal_velocity_sea_level():
    """Terminal velocity at sea level should be reasonable (5-15 m/s)."""
    ctrl = _default_controller()
    v_term = ctrl.terminal_velocity(altitude_m=0.0)
    assert 3.0 < v_term < 15.0, f"Terminal velocity {v_term} out of range"


def test_terminal_velocity_increases_with_altitude():
    """Terminal velocity should increase at higher altitude (thinner air)."""
    ctrl = _default_controller()
    v_low = ctrl.terminal_velocity(altitude_m=0.0)
    v_high = ctrl.terminal_velocity(altitude_m=500.0)
    assert v_high > v_low


def test_parachute_area_calculation():
    """Parachute area should match pi * r^2 for configured diameter."""
    ctrl = _default_controller()
    area = ctrl.parachute_area()
    expected = math.pi * (0.6 / 2) ** 2
    assert abs(area - expected) < 1e-9


def test_descent_simulation_produces_valid_results():
    """Simulation should produce telemetry and plausible descent values."""
    ctrl = _default_controller()
    result = ctrl.simulate_descent(launch_altitude_m=500.0, dt=0.1)

    assert result.max_altitude_m == 500.0
    assert result.total_descent_time_s > 10.0
    assert result.deploy_altitude_m > 0
    assert len(result.telemetry) > 50
    assert result.landing_velocity_ms > 0


def test_descent_telemetry_altitude_decreasing():
    """Telemetry altitude should generally decrease over time."""
    ctrl = _default_controller()
    result = ctrl.simulate_descent(launch_altitude_m=500.0)
    altitudes = [t.altitude_m for t in result.telemetry]
    # First point should be higher than last point
    assert altitudes[0] > altitudes[-1]


def test_competition_requirements_validation():
    """Default config should pass competition requirements (6-11 m/s)."""
    ctrl = _default_controller()
    result = ctrl.simulate_descent(launch_altitude_m=500.0)
    checks = ctrl.validate_competition_requirements(result)

    assert isinstance(checks, dict)
    assert "descent_rate_ok" in checks
    assert "total_time_ok" in checks
    assert "landing_velocity_safe" in checks
    assert "parachute_deployed" in checks
    assert "telemetry_count" in checks
    assert checks["parachute_deployed"] is True
    assert checks["total_time_ok"] is True


def test_design_parachute_returns_valid_design():
    """design_parachute should return sensible diameter and area."""
    result = design_parachute(mass_kg=0.350, target_velocity_ms=8.0)

    assert "required_area_m2" in result
    assert "diameter_m" in result
    assert "drag_coefficient" in result
    assert result["diameter_m"] > 0
    assert result["required_area_m2"] > 0
    assert result["drag_coefficient"] == 1.75
    assert result["shroud_lines"] >= 6


def test_design_parachute_heavier_mass_needs_larger_chute():
    """A heavier CanSat should require a larger parachute diameter."""
    light = design_parachute(mass_kg=0.200, target_velocity_ms=8.0)
    heavy = design_parachute(mass_kg=0.500, target_velocity_ms=8.0)
    assert heavy["diameter_m"] > light["diameter_m"]
