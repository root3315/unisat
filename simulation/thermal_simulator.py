"""Thermal Simulator — Six-face thermal model for CubeSat."""

import math
import numpy as np
from dataclasses import dataclass

STEFAN_BOLTZMANN = 5.670374419e-8  # W/m^2/K^4
SOLAR_CONSTANT = 1361.0  # W/m^2
EARTH_IR = 237.0  # W/m^2 (average)
ALBEDO = 0.3
COSMIC_BACKGROUND = 2.725  # K


@dataclass
class ThermalState:
    """Temperature of each face and internal."""
    time_s: float
    face_temps_c: list[float]  # +X, -X, +Y, -Y, +Z, -Z
    internal_temp_c: float
    in_eclipse: bool


def simulate_thermal(altitude_km: float = 550, duration_orbits: int = 3,
                     dt_s: float = 30.0, absorptivity: float = 0.88,
                     emissivity: float = 0.85, face_area_m2: float = 0.01,
                     mass_kg: float = 4.0, specific_heat: float = 900.0,
                     internal_dissipation_w: float = 3.5) -> list[ThermalState]:
    """Simulate thermal environment for a CubeSat."""
    r = 6371 + altitude_km
    period_s = 2 * math.pi * math.sqrt(r ** 3 / 398600.4418)
    duration_s = duration_orbits * period_s

    earth_view_factor = 0.5 * (1 - math.sqrt(1 - (6371 / r) ** 2))
    eclipse_fraction = 0.35  # Typical for SSO

    thermal_mass = mass_kg * specific_heat  # J/K
    results = []
    steps = int(duration_s / dt_s)

    # Initial temperatures (K)
    temps_k = [293.15] * 6  # 20°C all faces
    internal_k = 293.15

    for i in range(steps):
        t = i * dt_s
        phase = (t % period_s) / period_s
        in_eclipse = phase > (1 - eclipse_fraction)

        new_temps = []
        total_absorbed = 0.0
        total_radiated = 0.0

        for face in range(6):
            temp_k = temps_k[face]

            # Solar input (only when sunlit, and only on sun-facing faces)
            q_solar = 0.0
            if not in_eclipse:
                sun_cos = [0.5, -0.3, 0.4, -0.2, 0.8, -0.1][face]
                sun_cos = max(0, sun_cos * math.sin(2 * math.pi * phase))
                q_solar = SOLAR_CONSTANT * absorptivity * face_area_m2 * sun_cos

            # Earth IR
            q_earth_ir = EARTH_IR * emissivity * face_area_m2 * earth_view_factor

            # Albedo (only when sunlit and Earth-facing)
            q_albedo = 0.0
            if not in_eclipse and face >= 4:
                q_albedo = SOLAR_CONSTANT * ALBEDO * absorptivity * face_area_m2 * earth_view_factor * 0.5

            # Radiation to space
            q_radiated = emissivity * STEFAN_BOLTZMANN * face_area_m2 * temp_k ** 4

            # Internal dissipation (distributed equally)
            q_internal = internal_dissipation_w / 6.0

            # Net heat
            q_net = q_solar + q_earth_ir + q_albedo + q_internal - q_radiated
            total_absorbed += q_solar + q_earth_ir + q_albedo + q_internal
            total_radiated += q_radiated

            # Temperature update
            dt_temp = q_net / (thermal_mass / 6) * dt_s
            new_temp = temp_k + dt_temp
            new_temps.append(max(100.0, new_temp))  # Floor at 100K

        temps_k = new_temps
        internal_k = np.mean(temps_k)

        results.append(ThermalState(
            time_s=t,
            face_temps_c=[t - 273.15 for t in temps_k],
            internal_temp_c=internal_k - 273.15,
            in_eclipse=in_eclipse,
        ))

    return results


if __name__ == "__main__":
    states = simulate_thermal()
    print(f"Simulated {len(states)} thermal states")
    temps = [s.internal_temp_c for s in states]
    print(f"Internal temp range: {min(temps):.1f}°C to {max(temps):.1f}°C")
