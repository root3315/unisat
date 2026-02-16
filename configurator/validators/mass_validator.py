"""Mass Validator — Check satellite mass budget against limits."""

from dataclasses import dataclass

FORM_FACTOR_LIMITS = {"1U": 1.33, "2U": 2.66, "3U": 4.0, "6U": 12.0}

COMPONENT_MASSES = {
    "obc": 0.15, "eps_board": 0.10, "battery_pack": 0.50, "solar_panels": 0.20,
    "comm_uhf": 0.10, "comm_sband": 0.12, "adcs_magnetorquers": 0.15,
    "adcs_reaction_wheels": 0.35, "adcs_sensors": 0.08, "gnss": 0.05,
    "camera": 0.30, "payload": 0.20, "structure": 0.50, "harness": 0.15,
    "thermal": 0.10, "margin_20pct": 0.0,
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
    items = {}

    items["structure"] = COMPONENT_MASSES["structure"]
    items["harness"] = COMPONENT_MASSES["harness"]
    items["thermal"] = COMPONENT_MASSES["thermal"]
    items["obc"] = COMPONENT_MASSES["obc"]

    if enabled_subsystems.get("eps", True):
        items["eps_board"] = COMPONENT_MASSES["eps_board"]
        items["battery_pack"] = COMPONENT_MASSES["battery_pack"]
        items["solar_panels"] = COMPONENT_MASSES["solar_panels"]

    if enabled_subsystems.get("comm_uhf", True):
        items["comm_uhf"] = COMPONENT_MASSES["comm_uhf"]
    if enabled_subsystems.get("comm_sband", False):
        items["comm_sband"] = COMPONENT_MASSES["comm_sband"]
    if enabled_subsystems.get("adcs", True):
        items["adcs_magnetorquers"] = COMPONENT_MASSES["adcs_magnetorquers"]
        items["adcs_reaction_wheels"] = COMPONENT_MASSES["adcs_reaction_wheels"]
        items["adcs_sensors"] = COMPONENT_MASSES["adcs_sensors"]
    if enabled_subsystems.get("gnss", True):
        items["gnss"] = COMPONENT_MASSES["gnss"]
    if enabled_subsystems.get("camera", True):
        items["camera"] = COMPONENT_MASSES["camera"]
    if enabled_subsystems.get("payload", True):
        items["payload"] = COMPONENT_MASSES["payload"]

    subtotal = sum(items.values())
    margin_20 = subtotal * 0.20
    items["margin_20pct"] = round(margin_20, 3)
    total = subtotal + margin_20

    return MassResult(
        total_kg=round(total, 3), limit_kg=limit,
        margin_kg=round(limit - total, 3),
        margin_pct=round((limit - total) / limit * 100, 1),
        valid=total <= limit, items=items,
    )
