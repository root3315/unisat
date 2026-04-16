"""Mass Validator — Check mass budget for all platform types."""

from dataclasses import dataclass

# Mass limits by form factor (kg)
FORM_FACTOR_LIMITS: dict[str, float] = {
    # CubeSat
    "1U": 1.33, "2U": 2.66, "3U": 4.0, "6U": 12.0, "12U": 24.0,
    # CanSat
    "cansat_standard": 0.35, "cansat_custom": 0.5,
    # Rocket avionics
    "rocket_avionics": 0.5, "rocket_custom": 2.0,
    # HAB payloads
    "hab_payload_small": 1.0, "hab_payload_medium": 2.0, "hab_payload_large": 5.0,
    # Drone
    "drone_small": 2.5, "drone_medium": 5.0,
    # Custom
    "custom": 10.0,
}

# Component masses (kg) — shared across platforms
COMPONENT_MASSES: dict[str, float] = {
    # Common
    "obc": 0.15, "harness": 0.15, "structure": 0.50,
    # EPS
    "eps_board": 0.10, "battery_pack": 0.50, "solar_panels": 0.20,
    # Comms
    "comm_uhf": 0.10, "comm_sband": 0.12,
    # ADCS
    "adcs_magnetorquers": 0.15, "adcs_reaction_wheels": 0.35, "adcs_sensors": 0.08,
    # Sensors
    "gnss": 0.05, "imu": 0.02, "barometer": 0.01,
    # Payload
    "camera": 0.30, "payload": 0.20,
    # CanSat / rocket specific
    "descent_controller": 0.03, "thermal": 0.10,
    # Margin placeholder
    "margin_20pct": 0.0,
}

# Platform-specific structure mass overrides
STRUCTURE_MASS: dict[str, float] = {
    "cansat_standard": 0.05, "cansat_custom": 0.08,
    "rocket_avionics": 0.10, "rocket_custom": 0.15,
    "hab_payload_small": 0.15, "hab_payload_medium": 0.25, "hab_payload_large": 0.40,
    "drone_small": 0.80, "drone_medium": 1.50,
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
    """Validate mass budget for given configuration."""
    limit = FORM_FACTOR_LIMITS.get(form_factor, 4.0)
    items: dict[str, float] = {}

    # Structure (platform-specific)
    items["structure"] = STRUCTURE_MASS.get(form_factor, COMPONENT_MASSES["structure"])
    items["harness"] = COMPONENT_MASSES["harness"]
    items["obc"] = COMPONENT_MASSES["obc"]

    # Thermal (only CubeSat)
    if form_factor in ("1U", "2U", "3U", "6U", "12U"):
        items["thermal"] = COMPONENT_MASSES["thermal"]

    if enabled_subsystems.get("eps", False):
        items["eps_board"] = COMPONENT_MASSES["eps_board"]
        items["battery_pack"] = COMPONENT_MASSES["battery_pack"]
        items["solar_panels"] = COMPONENT_MASSES["solar_panels"]

    if enabled_subsystems.get("comm_uhf", False):
        items["comm_uhf"] = COMPONENT_MASSES["comm_uhf"]
    if enabled_subsystems.get("comm_sband", False):
        items["comm_sband"] = COMPONENT_MASSES["comm_sband"]

    if enabled_subsystems.get("adcs", False):
        items["adcs_magnetorquers"] = COMPONENT_MASSES["adcs_magnetorquers"]
        items["adcs_reaction_wheels"] = COMPONENT_MASSES["adcs_reaction_wheels"]
        items["adcs_sensors"] = COMPONENT_MASSES["adcs_sensors"]

    if enabled_subsystems.get("gnss", False):
        items["gnss"] = COMPONENT_MASSES["gnss"]
    if enabled_subsystems.get("imu", False):
        items["imu"] = COMPONENT_MASSES["imu"]
    if enabled_subsystems.get("barometer", False):
        items["barometer"] = COMPONENT_MASSES["barometer"]
    if enabled_subsystems.get("camera", False):
        items["camera"] = COMPONENT_MASSES["camera"]
    if enabled_subsystems.get("payload", False):
        items["payload"] = COMPONENT_MASSES["payload"]
    if enabled_subsystems.get("descent_controller", False):
        items["descent_controller"] = COMPONENT_MASSES["descent_controller"]

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
