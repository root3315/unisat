"""Orbit Simulator — Keplerian propagation with J2 perturbation."""

import math
from dataclasses import dataclass

MU_EARTH = 398600.4418  # km^3/s^2
R_EARTH = 6371.0  # km
J2 = 1.08263e-3
OMEGA_EARTH = 7.2921159e-5  # rad/s


@dataclass
class OrbitalElements:
    """Classical Keplerian orbital elements."""
    semi_major_axis_km: float
    eccentricity: float
    inclination_deg: float
    raan_deg: float
    arg_perigee_deg: float
    true_anomaly_deg: float


@dataclass
class StateVector:
    """Position and velocity in ECI frame."""
    x: float
    y: float
    z: float
    vx: float
    vy: float
    vz: float
    lat: float
    lon: float
    alt: float


def elements_from_config(altitude_km: float, inclination_deg: float,
                         eccentricity: float = 0.0001) -> OrbitalElements:
    """Create orbital elements from mission config parameters."""
    return OrbitalElements(
        semi_major_axis_km=R_EARTH + altitude_km,
        eccentricity=eccentricity,
        inclination_deg=inclination_deg,
        raan_deg=0.0,
        arg_perigee_deg=0.0,
        true_anomaly_deg=0.0,
    )


def propagate(elements: OrbitalElements, duration_s: float,
              dt_s: float = 60.0) -> list[StateVector]:
    """Propagate orbit with J2 perturbation."""
    a = elements.semi_major_axis_km
    e = elements.eccentricity
    inc = math.radians(elements.inclination_deg)
    raan = math.radians(elements.raan_deg)
    omega = math.radians(elements.arg_perigee_deg)
    nu = math.radians(elements.true_anomaly_deg)

    n = math.sqrt(MU_EARTH / a ** 3)  # Mean motion
    # J2 secular rates
    p = a * (1 - e ** 2)
    raan_dot = -1.5 * n * J2 * (R_EARTH / p) ** 2 * math.cos(inc)
    omega_dot = 0.75 * n * J2 * (R_EARTH / p) ** 2 * (5 * math.cos(inc) ** 2 - 1)

    results = []
    steps = int(duration_s / dt_s)

    for i in range(steps):
        t = i * dt_s
        M = nu + n * t  # Mean anomaly (simplified: circular)
        current_raan = raan + raan_dot * t
        current_omega = omega + omega_dot * t

        # Position in orbital plane
        r = a * (1 - e ** 2) / (1 + e * math.cos(M))
        x_orb = r * math.cos(M)
        y_orb = r * math.sin(M)

        # Rotation to ECI
        cos_raan = math.cos(current_raan)
        sin_raan = math.sin(current_raan)
        cos_inc = math.cos(inc)
        sin_inc = math.sin(inc)
        cos_omega = math.cos(current_omega)
        sin_omega = math.sin(current_omega)

        x_eci = (cos_raan * cos_omega - sin_raan * sin_omega * cos_inc) * x_orb + \
                (-cos_raan * sin_omega - sin_raan * cos_omega * cos_inc) * y_orb
        y_eci = (sin_raan * cos_omega + cos_raan * sin_omega * cos_inc) * x_orb + \
                (-sin_raan * sin_omega + cos_raan * cos_omega * cos_inc) * y_orb
        z_eci = (sin_omega * sin_inc) * x_orb + (cos_omega * sin_inc) * y_orb

        # ECI to geodetic
        alt = math.sqrt(x_eci**2 + y_eci**2 + z_eci**2) - R_EARTH
        lat = math.degrees(math.asin(z_eci / (R_EARTH + alt)))
        lon = math.degrees(math.atan2(y_eci, x_eci)) - math.degrees(OMEGA_EARTH * t)
        lon = ((lon + 180) % 360) - 180

        v = math.sqrt(MU_EARTH / r)
        results.append(StateVector(
            x=x_eci, y=y_eci, z=z_eci,
            vx=-v * math.sin(M), vy=v * math.cos(M), vz=0,
            lat=lat, lon=lon, alt=alt,
        ))

    return results


if __name__ == "__main__":
    elements = elements_from_config(550.0, 97.6)
    track = propagate(elements, 6000, dt_s=30)
    print(f"Propagated {len(track)} points")
    print(f"First: lat={track[0].lat:.2f}, lon={track[0].lon:.2f}, alt={track[0].alt:.1f} km")
    print(f"Last:  lat={track[-1].lat:.2f}, lon={track[-1].lon:.2f}, alt={track[-1].alt:.1f} km")
