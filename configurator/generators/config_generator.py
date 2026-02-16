"""Config Generator — Build mission_config.json from user selections."""

import json
from typing import Any


def generate_config(
    mission_name: str = "UniSat-1",
    form_factor: str = "3U",
    orbit_type: str = "SSO",
    altitude_km: float = 550,
    inclination_deg: float = 97.6,
    subsystems: dict[str, bool] | None = None,
    gs_lat: float = 41.2995,
    gs_lon: float = 69.2401,
) -> dict[str, Any]:
    """Generate a complete mission_config.json."""
    if subsystems is None:
        subsystems = {
            "obc": True, "eps": True, "comm": True, "adcs": True,
            "gnss": True, "camera": True, "payload": True,
        }

    mass_map = {"1U": 1.33, "2U": 2.66, "3U": 4.0, "6U": 12.0}
    dim_map = {
        "1U": [100, 100, 113.5], "2U": [100, 100, 227.0],
        "3U": [100, 100, 340.5], "6U": [100, 226.3, 340.5],
    }
    panel_map = {"1U": 4, "2U": 4, "3U": 6, "6U": 8}

    config = {
        "mission": {
            "name": mission_name, "version": "1.0.0",
            "description": "Universal modular CubeSat platform",
            "operator": "Team Name", "launch_date": "2026-01-01T00:00:00Z",
        },
        "satellite": {
            "form_factor": form_factor, "mass_kg": mass_map.get(form_factor, 4.0),
            "dimensions_mm": dim_map.get(form_factor, [100, 100, 340.5]),
        },
        "orbit": {
            "type": orbit_type, "altitude_km": altitude_km,
            "inclination_deg": inclination_deg, "expected_lifetime_years": 2,
        },
        "subsystems": {
            "obc": {"enabled": True, "mcu": "STM32F446RE", "clock_mhz": 180},
            "eps": {
                "enabled": subsystems.get("eps", True),
                "solar_panels": panel_map.get(form_factor, 6),
                "panel_efficiency": 0.295, "battery_capacity_wh": 30,
                "bus_voltage": 5.0,
            },
            "comm": {
                "enabled": subsystems.get("comm", True),
                "uhf": {"enabled": True, "frequency_mhz": 437.0, "data_rate_bps": 9600},
                "s_band": {"enabled": True, "frequency_mhz": 2400, "data_rate_kbps": 256},
            },
            "adcs": {"enabled": subsystems.get("adcs", True)},
            "gnss": {"enabled": subsystems.get("gnss", True)},
            "camera": {"enabled": subsystems.get("camera", True)},
            "payload": {"enabled": subsystems.get("payload", True), "type": "radiation_monitor"},
        },
        "ground_station": {
            "location": {"name": "Ground Station", "latitude": gs_lat,
                         "longitude": gs_lon, "altitude_m": 455},
            "antenna": {"type": "yagi", "gain_dbi": 14, "frequency_mhz": 437},
        },
    }
    return config


def save_config(config: dict, path: str = "mission_config.json") -> None:
    """Save configuration to JSON file."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)
