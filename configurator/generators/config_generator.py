"""Config Generator — Build mission_config.json for any platform type."""

import json
from pathlib import Path
from typing import Any


# Default templates per mission type
_TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


def generate_config(
    mission_name: str = "UniSat-1",
    mission_type: str = "cubesat_leo",
    platform: str = "cubesat",
    form_factor: str = "3U",
    orbit_type: str = "SSO",
    altitude_km: float = 550,
    inclination_deg: float = 97.6,
    telemetry_hz: float = 1.0,
    subsystems: dict[str, bool] | None = None,
    gs_lat: float = 41.2995,
    gs_lon: float = 69.2401,
    competition: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Generate a complete mission_config.json for any platform.

    Args:
        mission_name: Human-readable mission name.
        mission_type: Mission type string (e.g. "cansat_standard").
        platform: Platform category (e.g. "cubesat", "cansat").
        form_factor: Physical form factor.
        orbit_type: Orbit type (for orbital missions).
        altitude_km: Orbital altitude (for orbital missions).
        inclination_deg: Orbital inclination (for orbital missions).
        telemetry_hz: Telemetry rate.
        subsystems: Dict of subsystem name -> enabled bool.
        gs_lat: Ground station latitude.
        gs_lon: Ground station longitude.
        competition: Optional competition-specific config dict.

    Returns:
        Complete mission configuration dict.
    """
    if subsystems is None:
        subsystems = {"obc": True}

    config: dict[str, Any] = {
        "mission": {
            "name": mission_name,
            "version": "1.0.0",
            "description": f"{platform} mission",
            "mission_type": mission_type,
            "platform": platform,
            "operator": "Team Name",
            "telemetry_hz": telemetry_hz,
        },
        "satellite": {
            "form_factor": form_factor,
        },
        "subsystems": {},
    }

    # Add orbit section only for orbital missions
    if platform == "cubesat":
        config["orbit"] = {
            "type": orbit_type,
            "altitude_km": altitude_km,
            "inclination_deg": inclination_deg,
            "expected_lifetime_years": 2,
        }

    # Add subsystems
    for name, enabled in subsystems.items():
        config["subsystems"][name] = {"enabled": enabled}

    # Add ground station
    config["ground_station"] = {
        "location": {
            "name": "Ground Station",
            "latitude": gs_lat,
            "longitude": gs_lon,
            "altitude_m": 0,
        },
    }

    # Add competition config
    if competition:
        config["mission"]["competition"] = competition

    return config


def load_template(mission_type: str) -> dict[str, Any] | None:
    """Load a mission template by type.

    Args:
        mission_type: Mission type string.

    Returns:
        Template config dict, or None if not found.
    """
    templates_dir = Path(__file__).parent.parent.parent / "mission_templates"
    template_path = templates_dir / f"{mission_type}.json"
    if template_path.exists():
        with open(template_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def save_config(config: dict, path: str = "mission_config.json") -> None:
    """Save configuration to JSON file."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)
