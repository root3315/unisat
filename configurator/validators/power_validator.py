"""Power Validator — Check energy balance for the mission.

Accepts both canonical form-factor keys (``cubesat_3u`` …) and the pre-v1.3.0
legacy keys (``3U`` …) via the same ``_ALIASES`` pattern used by
``mass_validator`` and ``volume_validator``.
"""

from dataclasses import dataclass

SOLAR_CONSTANT = 1361  # W/m^2
PANEL_AREA_M2 = 0.01  # per panel face


@dataclass
class PowerResult:
    """Power validation result."""
    generation_w: float
    consumption_nominal_w: float
    consumption_peak_w: float
    net_nominal_w: float
    net_peak_w: float
    valid: bool
    details: dict[str, float]


SUBSYSTEM_POWER = {
    "obc": (0.5, 0.8),
    "comm_uhf": (1.0, 1.5),
    "comm_sband": (2.0, 2.5),
    "adcs": (0.8, 1.2),
    "gnss": (0.3, 0.4),
    "camera": (0.0, 3.0),
    "payload": (0.5, 0.8),
    "heater": (0.0, 2.0),
}


# Legacy-to-canonical key aliases — older configs and UI code used the short
# CubeSat codes ("1U", "3U" …) before v1.3.0 consolidated everything under the
# form_factors registry. Kept so pre-migration configs still resolve.
_ALIASES: dict[str, str] = {
    "1U": "cubesat_1u",
    "1.5U": "cubesat_1_5u",
    "2U": "cubesat_2u",
    "3U": "cubesat_3u",
    "6U": "cubesat_6u",
    "12U": "cubesat_12u",
}


def _canonical_key(form_factor: str) -> str:
    """Return the registry key for ``form_factor`` (accepts legacy aliases)."""
    return _ALIASES.get(form_factor, form_factor)


_CANONICAL_PANEL_COUNTS: dict[str, int] = {
    "cubesat_1u": 4,
    "cubesat_2u": 4,
    "cubesat_3u": 6,
    "cubesat_6u": 8,
    "cubesat_12u": 10,
    "cansat_standard": 0,
    "cansat_custom": 0,
    "rocket_avionics": 0,
    "rocket_custom": 0,
    "hab_payload_small": 0,
    "hab_payload_medium": 0,
    "hab_payload_large": 0,
    "drone_small": 0,
    "drone_medium": 0,
    "custom": 0,
}


def validate_power(form_factor: str, panel_efficiency: float,
                   enabled_subsystems: dict[str, bool]) -> PowerResult:
    """Validate power budget."""
    n_panels = _CANONICAL_PANEL_COUNTS.get(_canonical_key(form_factor), 0)

    # Average generation (accounting for eclipse and cosine losses)
    avg_factor = 0.35  # ~35% of orbit sunlit with average cosine
    generation = n_panels * PANEL_AREA_M2 * SOLAR_CONSTANT * panel_efficiency * avg_factor

    details = {}
    nominal_total = 0.0
    peak_total = 0.0

    for name, (nominal, peak) in SUBSYSTEM_POWER.items():
        if enabled_subsystems.get(name, False) or name == "obc":
            details[f"{name}_nominal"] = nominal
            details[f"{name}_peak"] = peak
            nominal_total += nominal
            peak_total += peak

    net_nominal = generation - nominal_total
    net_peak = generation - peak_total

    return PowerResult(
        generation_w=round(generation, 2),
        consumption_nominal_w=round(nominal_total, 2),
        consumption_peak_w=round(peak_total, 2),
        net_nominal_w=round(net_nominal, 2),
        net_peak_w=round(net_peak, 2),
        valid=net_nominal > 0,
        details=details,
    )
