"""Analytical Solutions — Closed-form orbital mechanics for aerospace olympiads.

Provides exact analytical solutions alongside numerical simulations
for validation and theoretical understanding.
"""

import math
from dataclasses import dataclass

MU = 398600.4418  # Earth gravitational parameter (km^3/s^2)
R_EARTH = 6371.0  # Earth radius (km)
J2 = 1.08263e-3  # Earth oblateness coefficient
OMEGA_EARTH = 7.2921159e-5  # Earth rotation rate (rad/s)


@dataclass
class OrbitParameters:
    """Complete set of derived orbital parameters."""
    altitude_km: float
    semi_major_axis_km: float
    period_s: float
    period_min: float
    velocity_kms: float
    angular_velocity_rads: float
    orbits_per_day: float
    ground_track_shift_deg: float


@dataclass
class J2Perturbations:
    """J2 perturbation rates."""
    raan_rate_deg_day: float
    arg_perigee_rate_deg_day: float
    mean_anomaly_rate_deg_day: float
    nodal_period_s: float
    is_sun_synchronous: bool
    required_inclination_for_sso_deg: float


@dataclass
class EclipseGeometry:
    """Eclipse duration and geometry."""
    eclipse_fraction: float
    eclipse_duration_s: float
    sunlit_duration_s: float
    earth_angular_radius_deg: float
    beta_angle_deg: float


def compute_orbit_parameters(altitude_km: float) -> OrbitParameters:
    """Derive all orbital parameters from altitude (circular orbit).

    Kepler's Third Law: T = 2*pi * sqrt(a^3 / mu)
    Vis-viva for circular orbit: v = sqrt(mu / r)
    """
    a = R_EARTH + altitude_km
    period = 2 * math.pi * math.sqrt(a**3 / MU)
    velocity = math.sqrt(MU / a)
    n = 2 * math.pi / period
    orbits_per_day = 86400 / period
    ground_shift = 360 / orbits_per_day

    return OrbitParameters(
        altitude_km=altitude_km,
        semi_major_axis_km=a,
        period_s=round(period, 2),
        period_min=round(period / 60, 2),
        velocity_kms=round(velocity, 3),
        angular_velocity_rads=round(n, 6),
        orbits_per_day=round(orbits_per_day, 2),
        ground_track_shift_deg=round(ground_shift, 2),
    )


def compute_j2_perturbations(altitude_km: float, inclination_deg: float,
                              eccentricity: float = 0.0) -> J2Perturbations:
    """Compute secular J2 perturbation rates.

    RAAN rate: dΩ/dt = -3/2 * n * J2 * (R_E/p)^2 * cos(i)
    Argument of perigee: dω/dt = 3/4 * n * J2 * (R_E/p)^2 * (5*cos²(i) - 1)
    """
    a = R_EARTH + altitude_km
    inc = math.radians(inclination_deg)
    p = a * (1 - eccentricity**2)
    n = math.sqrt(MU / a**3)

    # RAAN precession rate
    raan_rate = -1.5 * n * J2 * (R_EARTH / p)**2 * math.cos(inc)
    raan_deg_day = math.degrees(raan_rate) * 86400

    # Argument of perigee rate
    omega_rate = 0.75 * n * J2 * (R_EARTH / p)**2 * (5 * math.cos(inc)**2 - 1)
    omega_deg_day = math.degrees(omega_rate) * 86400

    # Mean anomaly correction
    m_rate = 0.75 * n * J2 * (R_EARTH / p)**2 * math.sqrt(1 - eccentricity**2) * \
             (3 * math.cos(inc)**2 - 1)
    m_deg_day = math.degrees(m_rate) * 86400

    # Nodal period (corrected for J2)
    nodal_period = 2 * math.pi / (n + m_rate)

    # Sun-synchronous inclination: dΩ/dt = 0.9856 deg/day
    sso_target_rate = 0.9856 * math.pi / 180 / 86400
    cos_i_sso = -sso_target_rate / (1.5 * n * J2 * (R_EARTH / p)**2)
    cos_i_sso = max(-1, min(1, cos_i_sso))
    sso_inc = math.degrees(math.acos(cos_i_sso))

    is_sso = abs(raan_deg_day - 0.9856) < 0.05

    return J2Perturbations(
        raan_rate_deg_day=round(raan_deg_day, 4),
        arg_perigee_rate_deg_day=round(omega_deg_day, 4),
        mean_anomaly_rate_deg_day=round(m_deg_day, 4),
        nodal_period_s=round(nodal_period, 2),
        is_sun_synchronous=is_sso,
        required_inclination_for_sso_deg=round(sso_inc, 2),
    )


def compute_eclipse(altitude_km: float, inclination_deg: float,
                    beta_angle_deg: float = 0.0) -> EclipseGeometry:
    """Compute eclipse geometry analytically.

    Earth angular radius: rho = arcsin(R_E / (R_E + h))
    Eclipse half-angle: theta = arccos(cos(rho) / cos(beta))
    Eclipse fraction: f = theta / pi
    """
    a = R_EARTH + altitude_km
    rho = math.asin(R_EARTH / a)
    rho_deg = math.degrees(rho)
    beta = math.radians(beta_angle_deg)

    cos_ratio = math.cos(rho) / math.cos(beta)
    if abs(cos_ratio) > 1:
        # No eclipse (high beta angle)
        eclipse_fraction = 0.0
    else:
        theta = math.acos(cos_ratio)
        eclipse_fraction = theta / math.pi

    period = 2 * math.pi * math.sqrt(a**3 / MU)
    eclipse_duration = eclipse_fraction * period
    sunlit_duration = period - eclipse_duration

    return EclipseGeometry(
        eclipse_fraction=round(eclipse_fraction, 4),
        eclipse_duration_s=round(eclipse_duration, 1),
        sunlit_duration_s=round(sunlit_duration, 1),
        earth_angular_radius_deg=round(rho_deg, 2),
        beta_angle_deg=beta_angle_deg,
    )


def compute_delta_v(altitude_1_km: float, altitude_2_km: float) -> dict:
    """Hohmann transfer delta-V between two circular orbits.

    dV1 = sqrt(mu/r1) * (sqrt(2*r2/(r1+r2)) - 1)
    dV2 = sqrt(mu/r2) * (1 - sqrt(2*r1/(r1+r2)))
    """
    r1 = R_EARTH + altitude_1_km
    r2 = R_EARTH + altitude_2_km

    v1_circular = math.sqrt(MU / r1)
    v2_circular = math.sqrt(MU / r2)

    dv1 = v1_circular * (math.sqrt(2 * r2 / (r1 + r2)) - 1)
    dv2 = v2_circular * (1 - math.sqrt(2 * r1 / (r1 + r2)))

    transfer_time = math.pi * math.sqrt((r1 + r2)**3 / (8 * MU))

    return {
        "dv1_kms": round(abs(dv1), 4),
        "dv2_kms": round(abs(dv2), 4),
        "total_dv_kms": round(abs(dv1) + abs(dv2), 4),
        "transfer_time_s": round(transfer_time, 1),
        "transfer_time_min": round(transfer_time / 60, 1),
    }


def compute_deorbit_lifetime(altitude_km: float, mass_kg: float,
                              area_m2: float, cd: float = 2.2) -> dict:
    """Estimate orbital lifetime due to atmospheric drag.

    Using King-Hele's approximation for circular orbits.
    Atmospheric density model: exponential with scale height.
    """
    # Simplified density model (exponential atmosphere)
    scale_heights = {
        200: (2.789e-10, 37.105), 300: (7.248e-11, 53.628),
        400: (2.803e-11, 58.515), 500: (1.184e-11, 60.828),
        600: (5.215e-12, 63.822), 700: (2.541e-12, 65.654),
        800: (1.170e-12, 76.377),
    }

    # Find closest altitude bracket
    closest = min(scale_heights.keys(), key=lambda x: abs(x - altitude_km))
    rho0, h_scale = scale_heights[closest]

    a = R_EARTH + altitude_km
    v = math.sqrt(MU / a)
    ballistic_coeff = mass_kg / (cd * area_m2)

    # Decay rate: da/dt = -rho * v * a / ballistic_coeff (simplified)
    decay_rate_km_day = rho0 * v * 1000 * a / ballistic_coeff * 86400

    if decay_rate_km_day > 0.001:
        lifetime_days = altitude_km / decay_rate_km_day
    else:
        lifetime_days = 365 * 25  # >25 years

    return {
        "altitude_km": altitude_km,
        "atmospheric_density_kgm3": rho0,
        "ballistic_coefficient_kgm2": round(ballistic_coeff, 2),
        "decay_rate_km_day": round(decay_rate_km_day, 4),
        "estimated_lifetime_days": round(lifetime_days, 0),
        "estimated_lifetime_years": round(lifetime_days / 365.25, 1),
        "within_25yr_guideline": lifetime_days < 25 * 365.25,
    }


if __name__ == "__main__":
    print("=" * 60)
    print("  UniSat Analytical Solutions")
    print("=" * 60)

    # 1. Orbit parameters
    orbit = compute_orbit_parameters(550)
    print(f"\n1. Orbit at {orbit.altitude_km} km:")
    print(f"   Period: {orbit.period_min} min")
    print(f"   Velocity: {orbit.velocity_kms} km/s")
    print(f"   Orbits/day: {orbit.orbits_per_day}")

    # 2. J2 perturbations
    j2 = compute_j2_perturbations(550, 97.6)
    print(f"\n2. J2 Perturbations:")
    print(f"   RAAN rate: {j2.raan_rate_deg_day} deg/day")
    print(f"   SSO: {j2.is_sun_synchronous}")
    print(f"   Required SSO inc: {j2.required_inclination_for_sso_deg}°")

    # 3. Eclipse
    eclipse = compute_eclipse(550, 97.6)
    print(f"\n3. Eclipse:")
    print(f"   Fraction: {eclipse.eclipse_fraction * 100:.1f}%")
    print(f"   Duration: {eclipse.eclipse_duration_s:.0f}s / {eclipse.sunlit_duration_s:.0f}s")

    # 4. Hohmann transfer
    dv = compute_delta_v(400, 550)
    print(f"\n4. Hohmann 400→550 km:")
    print(f"   Total ΔV: {dv['total_dv_kms']} km/s")
    print(f"   Transfer time: {dv['transfer_time_min']} min")

    # 5. Deorbit lifetime
    life = compute_deorbit_lifetime(550, 4.0, 0.03)
    print(f"\n5. Orbital Lifetime:")
    print(f"   Estimate: {life['estimated_lifetime_years']} years")
    print(f"   25-year compliant: {life['within_25yr_guideline']}")
