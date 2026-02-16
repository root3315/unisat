"""Mission Analyzer — Comprehensive mission analysis combining all simulators."""

import json
from pathlib import Path

from orbit_simulator import elements_from_config, propagate
from power_simulator import simulate_power
from thermal_simulator import simulate_thermal
from link_budget_calculator import calculate_link_budget


def analyze_mission(config_path: str = "../mission_config.json") -> dict:
    """Run complete mission analysis and return summary."""
    config_file = Path(__file__).parent / config_path
    if config_file.exists():
        config = json.loads(config_file.read_text(encoding="utf-8"))
    else:
        config = {
            "orbit": {"altitude_km": 550, "inclination_deg": 97.6},
            "subsystems": {"eps": {"solar_panels": 6, "panel_efficiency": 0.295}},
        }

    orbit = config.get("orbit", {})
    alt = orbit.get("altitude_km", 550)
    inc = orbit.get("inclination_deg", 97.6)

    print("=" * 60)
    print("  UniSat Mission Analysis")
    print("=" * 60)

    # Orbit
    print("\n[1/4] Orbit Simulation...")
    elements = elements_from_config(alt, inc)
    track = propagate(elements, 6000, dt_s=30)
    print(f"  Orbit period: ~{6000 / len(track) * len(track) / 60:.0f} min")
    print(f"  Ground track: {len(track)} points")
    lats = [s.lat for s in track]
    print(f"  Latitude range: {min(lats):.1f}° to {max(lats):.1f}°")

    # Power
    print("\n[2/4] Power Budget Simulation...")
    power = simulate_power(altitude_km=alt, inclination_deg=inc)
    socs = [p.battery_soc_pct for p in power]
    solar = [p.solar_power_w for p in power]
    eclipses = sum(1 for p in power if p.in_eclipse)
    print(f"  SOC range: {min(socs):.1f}% — {max(socs):.1f}%")
    print(f"  Max solar: {max(solar):.1f} W")
    print(f"  Eclipse fraction: {eclipses / len(power) * 100:.1f}%")

    # Thermal
    print("\n[3/4] Thermal Analysis...")
    thermal = simulate_thermal(altitude_km=alt)
    internal = [s.internal_temp_c for s in thermal]
    print(f"  Internal temp range: {min(internal):.1f}°C to {max(internal):.1f}°C")

    # Link budget
    print("\n[4/4] Link Budget...")
    uhf = calculate_link_budget(437, 1.0, 0.0, 14.0, 2000, 9600)
    sband = calculate_link_budget(2400, 2.0, 6.0, 20.0, 2000, 256000)
    print(f"  UHF:    SNR={uhf.snr_db} dB, margin={uhf.margin_db} dB")
    print(f"  S-band: SNR={sband.snr_db} dB, margin={sband.margin_db} dB")

    print("\n" + "=" * 60)
    print("  Analysis Complete")
    print("=" * 60)

    return {
        "orbit_points": len(track),
        "soc_min": min(socs), "soc_max": max(socs),
        "temp_min": min(internal), "temp_max": max(internal),
        "uhf_margin_db": uhf.margin_db, "sband_margin_db": sband.margin_db,
    }


if __name__ == "__main__":
    results = analyze_mission()
