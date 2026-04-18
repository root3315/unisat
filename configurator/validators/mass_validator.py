"""Mass Validator — Check mass budget for all platform types.

The mass limits are sourced from :mod:`core.form_factors` so the
configurator cannot drift from the form-factor registry. Legacy keys
(``1U``, ``2U``, …, ``cansat_custom``) are kept as aliases for
backwards compatibility; new code should use the canonical keys
(``cubesat_1u``, ``cansat_standard`` …).
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

_FLIGHT_SW = Path(__file__).resolve().parents[2] / "flight-software"
if str(_FLIGHT_SW) not in sys.path:
    sys.path.insert(0, str(_FLIGHT_SW))

from core.form_factors import get_form_factor, list_form_factors  # noqa: E402


# Legacy-to-canonical key aliases — older configs and UI code used
# "1U" / "cansat_custom" before v1.3.0 consolidated everything under
# core.form_factors. Keep both alive so existing templates keep working.
_ALIASES: dict[str, str] = {
    "1U": "cubesat_1u",
    "1.5U": "cubesat_1_5u",
    "2U": "cubesat_2u",
    "3U": "cubesat_3u",
    "6U": "cubesat_6u",
    "12U": "cubesat_12u",
    "cansat_custom": "cansat_advanced",
    "rocket_avionics": "rocket_payload",
    "rocket_custom": "rocket_payload",
    "hab_payload_small": "hab_payload",
    "hab_payload_medium": "hab_payload",
    "hab_payload_large": "hab_payload",
    "drone_medium": "drone_small",
}


def _canonical(form_factor: str) -> str:
    """Return the registry key for ``form_factor`` (accepts legacy aliases)."""
    return _ALIASES.get(form_factor, form_factor)


def _mass_limit_kg(form_factor: str) -> float:
    """Look up the mass limit for any legacy or canonical key."""
    try:
        return get_form_factor(_canonical(form_factor)).mass.max_kg
    except KeyError:
        return 4.0


# Expose the full mapping so Streamlit UI code can still iterate a dict.
FORM_FACTOR_LIMITS: dict[str, float] = {
    key: get_form_factor(key).mass.max_kg for key in list_form_factors()
}
FORM_FACTOR_LIMITS.update({alias: _mass_limit_kg(alias) for alias in _ALIASES})


# Component masses (kg) — CubeSat-class defaults.
COMPONENT_MASSES: dict[str, float] = {
    # Common
    "obc": 0.15, "harness": 0.15, "structure": 0.50,
    # EPS
    "eps_board": 0.10, "battery_pack": 0.50, "solar_panels": 0.20,
    # Comms
    "comm_uhf": 0.10, "comm_sband": 0.12, "comm_lora": 0.02,
    # ADCS
    "adcs_magnetorquers": 0.15, "adcs_reaction_wheels": 0.35, "adcs_sensors": 0.08,
    # Sensors
    "gnss": 0.05, "imu": 0.02, "barometer": 0.01,
    # Payload
    "camera": 0.30, "payload": 0.20,
    # CanSat / rocket specific
    "descent_controller": 0.03, "parachute": 0.015, "thermal": 0.10,
    # Margin placeholder
    "margin_20pct": 0.0,
}

# CanSat-class component masses (hobby/educational parts). These are
# orders of magnitude lighter than CubeSat — e.g. a CanSat OBC is a
# 5 g RP2040 board, not a 150 g full stack. Matches the verified
# totals in hardware/bom/by_form_factor/cansat_*.csv (130-250 g).
CANSAT_COMPONENT_MASSES: dict[str, float] = {
    "obc": 0.007, "harness": 0.005,
    "eps_board": 0.005, "battery_pack": 0.020, "solar_panels": 0.0,
    "comm_uhf": 0.005, "comm_sband": 0.0, "comm_lora": 0.005,
    "adcs_magnetorquers": 0.0, "adcs_reaction_wheels": 0.0, "adcs_sensors": 0.005,
    "gnss": 0.005, "imu": 0.002, "barometer": 0.001,
    "camera": 0.008, "payload": 0.050,
    "descent_controller": 0.015, "parachute": 0.014, "thermal": 0.005,
    "margin_20pct": 0.0,
}


def _component_masses(canonical: str) -> dict[str, float]:
    """Return the component mass table appropriate for the form factor."""
    if canonical.startswith("cansat_"):
        return CANSAT_COMPONENT_MASSES
    return COMPONENT_MASSES

# Platform-specific structure mass overrides
STRUCTURE_MASS: dict[str, float] = {
    "cansat_minimal": 0.08,
    "cansat_standard": 0.08,
    "cansat_advanced": 0.10,
    "rocket_payload": 0.10,
    "hab_payload": 0.15,
    "drone_small": 0.80,
    "rover_small": 1.00,
    # Legacy aliases
    "cansat_custom": 0.08,
    "rocket_avionics": 0.10, "rocket_custom": 0.15,
    "hab_payload_small": 0.15, "hab_payload_medium": 0.25, "hab_payload_large": 0.40,
    "drone_medium": 1.50,
}


@dataclass
class MassResult:
    """Mass validation result."""
    total_kg: float
    limit_kg: float
    margin_kg: float
    margin_pct: float
    valid: bool
    items: dict[str, float]


def validate_mass(form_factor: str, enabled_subsystems: dict[str, bool]) -> MassResult:
    """Validate mass budget for a configuration.

    Accepts any key known to :mod:`core.form_factors` as well as the
    legacy aliases ("1U", "cansat_custom", …). Returns a populated
    :class:`MassResult` even for unknown form factors (falls back to a
    4 kg soft ceiling).
    """
    canonical = _canonical(form_factor)
    limit = _mass_limit_kg(form_factor)
    masses = _component_masses(canonical)
    items: dict[str, float] = {}

    # Structure (platform-specific)
    items["structure"] = STRUCTURE_MASS.get(
        canonical,
        STRUCTURE_MASS.get(form_factor, masses.get("structure", 0.05)),
    )
    items["harness"] = masses["harness"]
    items["obc"] = masses["obc"]

    # Thermal (only CubeSat)
    if canonical.startswith("cubesat_"):
        items["thermal"] = masses.get("thermal", COMPONENT_MASSES["thermal"])

    if enabled_subsystems.get("eps", False):
        items["eps_board"] = masses["eps_board"]
        items["battery_pack"] = masses["battery_pack"]
        try:
            if get_form_factor(canonical).power.solar_capable:
                items["solar_panels"] = masses.get(
                    "solar_panels", COMPONENT_MASSES["solar_panels"]
                )
        except KeyError:
            items["solar_panels"] = masses.get("solar_panels", 0.0)

    if enabled_subsystems.get("comm_uhf", False):
        items["comm_uhf"] = masses["comm_uhf"]
    if enabled_subsystems.get("comm_sband", False):
        items["comm_sband"] = masses["comm_sband"]
    if enabled_subsystems.get("comm_lora", False):
        items["comm_lora"] = masses["comm_lora"]

    if enabled_subsystems.get("adcs", False):
        items["adcs_magnetorquers"] = masses["adcs_magnetorquers"]
        items["adcs_reaction_wheels"] = masses["adcs_reaction_wheels"]
        items["adcs_sensors"] = masses["adcs_sensors"]

    if enabled_subsystems.get("gnss", False):
        items["gnss"] = masses["gnss"]
    if enabled_subsystems.get("imu", False):
        items["imu"] = masses["imu"]
    if enabled_subsystems.get("barometer", False):
        items["barometer"] = masses["barometer"]
    if enabled_subsystems.get("camera", False):
        items["camera"] = masses["camera"]
    if enabled_subsystems.get("payload", False):
        items["payload"] = masses["payload"]
    if enabled_subsystems.get("descent_controller", False):
        items["descent_controller"] = masses["descent_controller"]
        items["parachute"] = masses["parachute"]

    subtotal = sum(items.values())
    margin_20 = subtotal * 0.20
    items["margin_20pct"] = round(margin_20, 3)
    total = subtotal + margin_20

    return MassResult(
        total_kg=round(total, 3), limit_kg=limit,
        margin_kg=round(limit - total, 3),
        margin_pct=round((limit - total) / limit * 100, 1) if limit > 0 else 0.0,
        valid=total <= limit, items=items,
    )
