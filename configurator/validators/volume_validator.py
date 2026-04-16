"""Volume Validator — Check component fit for all platform types."""

from dataclasses import dataclass

# Volume specs by form factor
FORM_FACTOR_VOLUMES: dict[str, dict[str, float]] = {
    # CubeSat standards
    "1U": {"x_mm": 100, "y_mm": 100, "z_mm": 113.5, "volume_cm3": 1135},
    "2U": {"x_mm": 100, "y_mm": 100, "z_mm": 227.0, "volume_cm3": 2270},
    "3U": {"x_mm": 100, "y_mm": 100, "z_mm": 340.5, "volume_cm3": 3405},
    "6U": {"x_mm": 100, "y_mm": 226.3, "z_mm": 340.5, "volume_cm3": 7704},
    "12U": {"x_mm": 226.3, "y_mm": 226.3, "z_mm": 340.5, "volume_cm3": 17438},
    # CanSat
    "cansat_standard": {"diameter_mm": 64, "can_height_mm": 68, "capsule_height_mm": 80, "x_mm": 64, "y_mm": 64, "z_mm": 80, "volume_cm3": 257},
    "cansat_custom": {"x_mm": 80, "y_mm": 80, "z_mm": 150, "volume_cm3": 960},
    # Rocket
    "rocket_avionics": {"x_mm": 50, "y_mm": 50, "z_mm": 100, "volume_cm3": 250},
    "rocket_custom": {"x_mm": 80, "y_mm": 80, "z_mm": 200, "volume_cm3": 1280},
    # HAB
    "hab_payload_small": {"x_mm": 150, "y_mm": 150, "z_mm": 100, "volume_cm3": 2250},
    "hab_payload_medium": {"x_mm": 200, "y_mm": 200, "z_mm": 150, "volume_cm3": 6000},
    "hab_payload_large": {"x_mm": 300, "y_mm": 300, "z_mm": 200, "volume_cm3": 18000},
    # Drone
    "drone_small": {"x_mm": 200, "y_mm": 200, "z_mm": 100, "volume_cm3": 4000},
    "drone_medium": {"x_mm": 300, "y_mm": 300, "z_mm": 150, "volume_cm3": 13500},
    # Custom
    "custom": {"x_mm": 200, "y_mm": 200, "z_mm": 200, "volume_cm3": 8000},
}

COMPONENT_VOLUMES_CM3: dict[str, float] = {
    "obc_board": 50, "eps_board": 60, "battery_pack": 200,
    "comm_uhf": 40, "comm_sband": 50, "adcs_unit": 150,
    "gnss_module": 15, "imu_module": 5, "barometer_module": 3,
    "camera_module": 80, "payload_module": 100,
    "descent_controller_module": 20, "harness_misc": 50,
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
    """Validate volume budget for given configuration."""
    specs = FORM_FACTOR_VOLUMES.get(form_factor, FORM_FACTOR_VOLUMES.get("3U", {}))
    available = specs.get("volume_cm3", 3405)

    items: dict[str, float] = {
        "obc_board": COMPONENT_VOLUMES_CM3["obc_board"],
        "harness_misc": COMPONENT_VOLUMES_CM3["harness_misc"],
    }

    if enabled_subsystems.get("eps", False):
        items["eps_board"] = COMPONENT_VOLUMES_CM3["eps_board"]
        items["battery_pack"] = COMPONENT_VOLUMES_CM3["battery_pack"]
    if enabled_subsystems.get("comm_uhf", False):
        items["comm_uhf"] = COMPONENT_VOLUMES_CM3["comm_uhf"]
    if enabled_subsystems.get("comm_sband", False):
        items["comm_sband"] = COMPONENT_VOLUMES_CM3["comm_sband"]
    if enabled_subsystems.get("adcs", False):
        items["adcs_unit"] = COMPONENT_VOLUMES_CM3["adcs_unit"]
    if enabled_subsystems.get("gnss", False):
        items["gnss_module"] = COMPONENT_VOLUMES_CM3["gnss_module"]
    if enabled_subsystems.get("imu", False):
        items["imu_module"] = COMPONENT_VOLUMES_CM3["imu_module"]
    if enabled_subsystems.get("barometer", False):
        items["barometer_module"] = COMPONENT_VOLUMES_CM3["barometer_module"]
    if enabled_subsystems.get("camera", False):
        items["camera_module"] = COMPONENT_VOLUMES_CM3["camera_module"]
    if enabled_subsystems.get("payload", False):
        items["payload_module"] = COMPONENT_VOLUMES_CM3["payload_module"]
    if enabled_subsystems.get("descent_controller", False):
        items["descent_controller_module"] = COMPONENT_VOLUMES_CM3["descent_controller_module"]

    total = sum(items.values())
    util = (total / available * 100) if available > 0 else 0.0

    return VolumeResult(
        total_cm3=total, available_cm3=available,
        utilization_pct=round(util, 1), valid=total <= available,
        items=items,
    )
