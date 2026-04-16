"""Power Simulator — Solar generation and eclipse modeling."""

import math
import numpy as np
from dataclasses import dataclass


@dataclass
class PowerProfile:
    """Power state at a time step."""
    time_s: float
    solar_power_w: float
    consumption_w: float
    net_power_w: float
    battery_soc_pct: float
    in_eclipse: bool


def simulate_power(altitude_km: float = 550, inclination_deg: float = 97.6,
                   panel_area_m2: float = 0.06, panel_count: int = 6,
                   efficiency: float = 0.295, consumption_w: float = 3.5,
                   battery_wh: float = 30.0, duration_orbits: int = 3,
                   dt_s: float = 30.0) -> list[PowerProfile]:
    """Simulate power budget over multiple orbits."""
    r = 6371 + altitude_km
    period_s = 2 * math.pi * math.sqrt(r ** 3 / 398600.4418)
    duration_s = duration_orbits * period_s

    # Eclipse fraction (simplified for SSO)
    eclipse_fraction = math.acos(math.sqrt(
        max(0, 1 - (6371 / r) ** 2)
    )) / math.pi

    solar_constant = 1361  # W/m^2
    total_panel_area = panel_area_m2 * panel_count
    max_solar_power = solar_constant * total_panel_area * efficiency

    results = []
    steps = int(duration_s / dt_s)
    soc = 80.0  # Start at 80%

    for i in range(steps):
        t = i * dt_s
        orbit_phase = (t % period_s) / period_s

        # Eclipse model: ~35% of orbit in shadow for SSO
        in_eclipse = orbit_phase > (1 - eclipse_fraction)

        if in_eclipse:
            solar_power = 0.0
        else:
            # Cosine loss based on sun angle
            sun_angle = math.sin(2 * math.pi * orbit_phase)
            solar_power = max_solar_power * max(0, 0.5 + 0.5 * sun_angle)

        net = solar_power - consumption_w
        soc += (net / battery_wh) * (dt_s / 3600.0) * 100.0
        soc = max(0.0, min(100.0, soc))

        results.append(PowerProfile(
            time_s=t, solar_power_w=solar_power,
            consumption_w=consumption_w, net_power_w=net,
            battery_soc_pct=soc, in_eclipse=in_eclipse,
        ))

    return results


if __name__ == "__main__":
    profile = simulate_power()
    eclipses = sum(1 for p in profile if p.in_eclipse)
    print(f"Simulated {len(profile)} time steps")
    print(f"Eclipse fraction: {eclipses / len(profile) * 100:.1f}%")
    print(f"SOC range: {min(p.battery_soc_pct for p in profile):.1f}% - "
          f"{max(p.battery_soc_pct for p in profile):.1f}%")
