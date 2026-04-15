"""Tests for the orbit simulator module."""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from orbit_simulator import R_EARTH, elements_from_config, propagate


class TestElementsFromConfig:
    """Tests for creating orbital elements from config parameters."""

    def test_semi_major_axis_equals_altitude_plus_earth_radius(self):
        elems = elements_from_config(altitude_km=550.0, inclination_deg=97.6)
        assert elems.semi_major_axis_km == R_EARTH + 550.0

    def test_inclination_preserved(self):
        elems = elements_from_config(altitude_km=400.0, inclination_deg=51.6)
        assert elems.inclination_deg == 51.6

    def test_default_eccentricity_near_circular(self):
        elems = elements_from_config(altitude_km=550.0, inclination_deg=97.6)
        assert elems.eccentricity == 0.0001

    def test_custom_eccentricity(self):
        elems = elements_from_config(altitude_km=550.0, inclination_deg=97.6, eccentricity=0.01)
        assert elems.eccentricity == 0.01

    def test_initial_angles_are_zero(self):
        elems = elements_from_config(altitude_km=550.0, inclination_deg=97.6)
        assert elems.raan_deg == 0.0
        assert elems.arg_perigee_deg == 0.0
        assert elems.true_anomaly_deg == 0.0


class TestPropagation:
    """Tests for orbit propagation results."""

    def test_point_count_matches_duration_and_timestep(self):
        elems = elements_from_config(550.0, 97.6)
        track = propagate(elems, duration_s=600, dt_s=60.0)
        assert len(track) == 10  # 600/60

    def test_point_count_one_orbit(self):
        elems = elements_from_config(550.0, 97.6)
        track = propagate(elems, duration_s=5760, dt_s=30.0)
        assert len(track) == 192  # 5760/30

    def test_latitude_range_bounded_by_inclination(self):
        inc = 51.6
        elems = elements_from_config(400.0, inc)
        track = propagate(elems, duration_s=6000, dt_s=30.0)
        lats = [sv.lat for sv in track]
        # Latitude should never exceed inclination (+ small margin for J2)
        assert max(lats) <= inc + 2.0
        assert min(lats) >= -(inc + 2.0)

    def test_altitude_stays_near_configured(self):
        alt_target = 550.0
        elems = elements_from_config(alt_target, 97.6)
        track = propagate(elems, duration_s=6000, dt_s=60.0)
        for sv in track:
            # Near-circular orbit, altitude should stay within ~20 km
            assert abs(sv.alt - alt_target) < 20.0, (
                f"Altitude {sv.alt:.1f} km deviated too far from {alt_target} km"
            )

    def test_first_point_starts_near_equator(self):
        elems = elements_from_config(550.0, 97.6)
        track = propagate(elems, duration_s=600, dt_s=60.0)
        # With true_anomaly=0 and arg_perigee=0, initial latitude is near 0
        assert abs(track[0].lat) < 5.0

    def test_propagation_returns_state_vectors_with_velocity(self):
        elems = elements_from_config(550.0, 97.6)
        track = propagate(elems, duration_s=120, dt_s=60.0)
        for sv in track:
            speed = math.sqrt(sv.vx**2 + sv.vy**2 + sv.vz**2)
            # LEO orbital speed ~7.5 km/s
            assert 6.0 < speed < 9.0, f"Speed {speed:.2f} km/s is outside LEO range"
