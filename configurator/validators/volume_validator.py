"""Volume Validator — Check component fit within CubeSat form factor."""

from dataclasses import dataclass

FORM_FACTOR_VOLUMES = {
    "1U": {"x_mm": 100, "y_mm": 100, "z_mm": 113.5, "volume_cm3": 1135},
    "2U": {"x_mm": 100, "y_mm": 100, "z_mm": 227.0, "volume_cm3": 2270},
    "3U": {"x_mm": 100, "y_mm": 100, "z_mm": 340.5, "volume_cm3": 3405},
    "6U": {"x_mm": 100, "y_mm": 226.3, "z_mm": 340.5, "volume_cm3": 7704},
}

COMPONENT_VOLUMES_CM3 = {
    "obc_board": 50, "eps_board": 60, "battery_pack": 200,
    "comm_uhf": 40, "comm_sband": 50, "adcs_unit": 150,
    "gnss_module": 15, "camera_module": 80, "payload_module": 100,
    "harness_misc": 50,
}


@dataclass
class VolumeResult:
    """Volume validation result."""
    total_cm3: float
    available_cm3: float
    utilization_pct: float
    valid: bool
    items: dict[str, float]


def validate_volume(form_factor: str,
                    enabled_subsystems: dict[str, bool]) -> VolumeResult:
    """Validate volume budget."""
    specs = FORM_FACTOR_VOLUMES.get(form_factor, FORM_FACTOR_VOLUMES["3U"])
    available = specs["volume_cm3"]

    items = {"obc_board": COMPONENT_VOLUMES_CM3["obc_board"],
             "harness_misc": COMPONENT_VOLUMES_CM3["harness_misc"]}

    if enabled_subsystems.get("eps", True):
        items["eps_board"] = COMPONENT_VOLUMES_CM3["eps_board"]
        items["battery_pack"] = COMPONENT_VOLUMES_CM3["battery_pack"]
    if enabled_subsystems.get("comm_uhf", True):
        items["comm_uhf"] = COMPONENT_VOLUMES_CM3["comm_uhf"]
    if enabled_subsystems.get("comm_sband", False):
        items["comm_sband"] = COMPONENT_VOLUMES_CM3["comm_sband"]
    if enabled_subsystems.get("adcs", True):
        items["adcs_unit"] = COMPONENT_VOLUMES_CM3["adcs_unit"]
    if enabled_subsystems.get("gnss", True):
        items["gnss_module"] = COMPONENT_VOLUMES_CM3["gnss_module"]
    if enabled_subsystems.get("camera", True):
        items["camera_module"] = COMPONENT_VOLUMES_CM3["camera_module"]
    if enabled_subsystems.get("payload", True):
        items["payload_module"] = COMPONENT_VOLUMES_CM3["payload_module"]

    total = sum(items.values())
    util = total / available * 100

    return VolumeResult(
        total_cm3=total, available_cm3=available,
        utilization_pct=round(util, 1), valid=total <= available,
        items=items,
    )
