"""Tests for the IGRF dipole model."""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from igrf_model import compute_field, simple_dipole_field, R_EARTH


class TestFieldMagnitude:
    """Test that field magnitudes fall within expected physical ranges."""

    def test_equator_magnitude_in_range(self):
        """At the equator the total field should be ~25,000-35,000 nT at 400 km."""
        field = compute_field(0.0, 0.0, 400.0)
        assert 24_000 < field.magnitude < 35_000

    def test_north_pole_magnitude_in_range(self):
        """At the north pole the field should be ~45,000-65,000 nT at 400 km."""
        field = compute_field(90.0, 0.0, 400.0)
        assert 45_000 < field.magnitude < 65_000

    def test_south_pole_magnitude_in_range(self):
        """At the south pole the field should be ~45,000-65,000 nT at 400 km."""
        field = compute_field(-90.0, 0.0, 400.0)
        assert 45_000 < field.magnitude < 65_000

    def test_field_decreases_with_altitude(self):
        """Field magnitude should decrease as altitude increases."""
        low = compute_field(45.0, 0.0, 300.0)
        high = compute_field(45.0, 0.0, 800.0)
        assert low.magnitude > high.magnitude


class TestInclination:
    """Test that the field inclination matches expected physical behavior."""

    def test_equator_inclination_near_zero(self):
        """At the geographic equator, inclination should be roughly horizontal."""
        field = compute_field(0.0, 0.0, 400.0)
        assert abs(field.inclination_deg) < 25.0

    def test_north_pole_inclination_near_positive_90(self):
        """At the north pole, field should dip steeply downward (positive)."""
        field = compute_field(90.0, 0.0, 400.0)
        assert field.inclination_deg > 70.0

    def test_south_pole_inclination_near_negative_90(self):
        """At the south pole, field should point steeply upward (negative)."""
        field = compute_field(-90.0, 0.0, 400.0)
        assert field.inclination_deg < -70.0


class TestSimpleDipole:
    """Test the axial dipole comparison function."""

    def test_axial_dipole_returns_two_components(self):
        bh, bz = simple_dipole_field(0.0, 400.0)
        assert isinstance(bh, float)
        assert isinstance(bz, float)

    def test_axial_dipole_equator_mostly_horizontal(self):
        """At the equator the axial dipole field is purely horizontal."""
        bh, bz = simple_dipole_field(0.0, 400.0)
        assert abs(bh) > abs(bz)

    def test_axial_dipole_pole_mostly_vertical(self):
        """At the pole the axial dipole field is purely vertical."""
        bh, bz = simple_dipole_field(90.0, 400.0)
        assert abs(bz) > abs(bh)
