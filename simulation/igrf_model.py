"""Simplified IGRF (International Geomagnetic Reference Field) Model.

Dipole approximation of Earth's magnetic field for CubeSat attitude
determination and magnetorquer control. Uses IGRF-13 coefficients
(Alken et al., 2021) for epoch 2025.0.

The model computes the geomagnetic field vector at any point above
Earth's surface using the first-order (dipole) spherical harmonic
expansion. This is sufficient for CubeSat ADCS simulation where
sub-percent accuracy is not required.

Reference:
    Alken, P., et al. (2021). International Geomagnetic Reference
    Field: the thirteenth generation. Earth, Planets and Space, 73, 49.
    https://doi.org/10.1186/s40623-020-01288-x
"""

import math
import numpy as np
from dataclasses import dataclass

# Earth reference radius for IGRF (km)
R_EARTH = 6371.2

# IGRF-13 Gauss coefficients for epoch 2025.0 (nT)
# These are the first-degree (dipole) terms only.
G10 = -29404.8  # g(1,0)
G11 = -1450.9   # g(1,1)
H11 = 4652.5    # h(1,1)

# Derived dipole moment (nT * km^3)
# M = R_EARTH^3 * sqrt(g10^2 + g11^2 + h11^2)
DIPOLE_MOMENT = R_EARTH**3 * math.sqrt(G10**2 + G11**2 + H11**2)

# Dipole axis direction (geographic coordinates of geomagnetic north pole)
POLE_COLATITUDE_RAD = math.acos(G10 / math.sqrt(G10**2 + G11**2 + H11**2))
POLE_LONGITUDE_RAD = math.atan2(H11, -G11)


@dataclass
class MagneticField:
    """Geomagnetic field vector and derived quantities."""
    bx: float       # North component (nT)
    by: float       # East component (nT)
    bz: float       # Down component (nT)
    magnitude: float # Total field intensity (nT)
    inclination_deg: float  # Dip angle (positive downward)
    declination_deg: float  # Angle from geographic north (positive east)


def compute_field(lat_deg: float, lon_deg: float, alt_km: float) -> MagneticField:
    """Compute the geomagnetic field at a given location.

    Uses a tilted dipole approximation with IGRF-13 first-degree
    Gauss coefficients. The dipole axis is tilted ~9.7 degrees from
    the geographic axis.

    Args:
        lat_deg: Geodetic latitude in degrees (-90 to 90).
        lon_deg: Longitude in degrees (-180 to 360).
        alt_km: Altitude above sea level in km.

    Returns:
        MagneticField with components in North-East-Down (NED) frame.
    """
    lat = math.radians(lat_deg)
    lon = math.radians(lon_deg)
    r = R_EARTH + alt_km

    # Ratio (a/r)^3 for field scaling
    ratio = (R_EARTH / r) ** 3

    # Compute field components in geocentric spherical coordinates
    # using direct spherical harmonic expansion (degree 1 only).
    #
    # B_r     = -dV/dr     (radial, positive outward)
    # B_theta = -(1/r) dV/dtheta  (southward, positive south)
    # B_phi   = -(1/(r sin(theta))) dV/dphi  (eastward)
    #
    # For n=1 terms:
    cos_lat = math.cos(lat)
    sin_lat = math.sin(lat)
    cos_lon = math.cos(lon)
    sin_lon = math.sin(lon)

    # Geocentric colatitude theta = 90 - lat (simplified, ignoring
    # geodetic-geocentric correction which is < 0.2 degrees)
    cos_theta = sin_lat  # cos(90 - lat) = sin(lat)
    sin_theta = cos_lat  # sin(90 - lat) = cos(lat)

    # Radial component (positive outward)
    br = -2.0 * ratio * (
        G10 * cos_theta
        + (G11 * cos_lon + H11 * sin_lon) * sin_theta
    )

    # Theta component (positive southward)
    bt = -ratio * (
        -G10 * sin_theta
        + (G11 * cos_lon + H11 * sin_lon) * cos_theta
    )

    # Phi component (positive eastward)
    bp = -ratio * (
        -G11 * sin_lon + H11 * cos_lon
    )

    # Convert spherical (r, theta, phi) to NED (North, East, Down)
    # North = -B_theta (theta points south, north is opposite)
    # East  = B_phi
    # Down  = -B_r (r points outward, down is opposite)
    bx = -bt   # North
    by = bp    # East
    bz = -br   # Down

    magnitude = math.sqrt(bx**2 + by**2 + bz**2)
    bh = math.sqrt(bx**2 + by**2)  # Horizontal intensity

    inclination = math.degrees(math.atan2(bz, bh))
    declination = math.degrees(math.atan2(by, bx))

    return MagneticField(
        bx=bx, by=by, bz=bz,
        magnitude=magnitude,
        inclination_deg=inclination,
        declination_deg=declination,
    )


def simple_dipole_field(lat_deg: float, alt_km: float) -> tuple[float, float]:
    """Compute axial dipole field for comparison (centered, untilted).

    Returns (B_horizontal, B_vertical) in nT assuming a pure axial
    dipole aligned with the rotation axis.
    """
    lat = math.radians(lat_deg)
    r = R_EARTH + alt_km
    ratio = (R_EARTH / r) ** 3

    # Axial dipole uses only g10
    b0 = abs(G10)

    b_r = -2.0 * b0 * ratio * math.sin(lat)
    b_theta = -b0 * ratio * math.cos(lat)

    return (-b_theta, -b_r)  # (horizontal_north, down)


def main() -> None:
    """Demonstrate IGRF model at several locations."""
    locations = [
        ("Equator (0N, 0E)",            0.0,    0.0,  400.0),
        ("North Pole",                  90.0,    0.0,  400.0),
        ("South Pole",                 -90.0,    0.0,  400.0),
        ("Moscow (55.7N, 37.6E)",       55.7,   37.6,  400.0),
        ("New York (40.7N, -74.0E)",    40.7,  -74.0,  400.0),
        ("Sao Paulo (-23.5S, -46.6W)", -23.5,  -46.6,  400.0),
        ("ISS typical (51.6N, 0E)",     51.6,    0.0,  420.0),
    ]

    print("=" * 78)
    print("UniSat IGRF-13 Dipole Model (epoch 2025.0)")
    print(f"Dipole tilt: {math.degrees(POLE_COLATITUDE_RAD):.1f} deg from rotation axis")
    print("=" * 78)
    print(f"{'Location':<30} {'|B| nT':>9} {'Incl':>7} {'Decl':>7}"
          f"  {'Bx(N)':>9} {'By(E)':>9} {'Bz(D)':>9}")
    print("-" * 78)

    for name, lat, lon, alt in locations:
        field = compute_field(lat, lon, alt)
        print(f"{name:<30} {field.magnitude:9.1f} {field.inclination_deg:7.1f}"
              f" {field.declination_deg:7.1f}  {field.bx:9.1f}"
              f" {field.by:9.1f} {field.bz:9.1f}")

    # Compare tilted dipole with simple axial dipole at equator
    print("\n--- Axial dipole comparison at 400 km ---")
    for lat in [0, 30, 60, 90]:
        full = compute_field(lat, 0.0, 400.0)
        bh, bz = simple_dipole_field(lat, 400.0)
        simple_mag = math.sqrt(bh**2 + bz**2)
        diff_pct = 100.0 * abs(full.magnitude - simple_mag) / full.magnitude
        print(f"  Lat {lat:3d}: IGRF dipole = {full.magnitude:.0f} nT, "
              f"axial dipole = {simple_mag:.0f} nT, "
              f"diff = {diff_pct:.1f}%")


if __name__ == "__main__":
    main()
