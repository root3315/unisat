"""Volume Validator — Check component fit for all platform types.

Volume envelopes are sourced from :mod:`core.form_factors`. Legacy
keys ("1U", "cansat_custom" …) are kept as aliases so older configs
keep validating.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

_FLIGHT_SW = Path(__file__).resolve().parents[2] / "flight-software"
if str(_FLIGHT_SW) not in sys.path:
    sys.path.insert(0, str(_FLIGHT_SW))

from core.form_factors import get_form_factor, list_form_factors  # noqa: E402


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
    return _ALIASES.get(form_factor, form_factor)


def _volume_spec(form_factor: str) -> dict[str, float]:
    """Merge registry volume info with legacy bbox hints for UI display."""
    canonical = _canonical(form_factor)
    try:
        ff = get_form_factor(canonical)
    except KeyError:
        return {"volume_cm3": 3405.0, "x_mm": 100.0, "y_mm": 100.0, "z_mm": 340.5}
    spec: dict[str, float] = dict(ff.volume.dimensions_mm)
    spec["volume_cm3"] = ff.volume.volume_cm3
    # Provide rectangular bbox for cylindrical shapes so UI can show a box.
    if ff.volume.shape == "cylindrical":
        d = ff.volume.dimensions_mm.get("outer_d", 0.0)
        h = ff.volume.dimensions_mm.get("height", 0.0)
        spec.setdefault("x_mm", d)
        spec.setdefault("y_mm", d)
        spec.setdefault("z_mm", h)
    return spec


FORM_FACTOR_VOLUMES: dict[str, dict[str, float]] = {
    key: _volume_spec(key) for key in list_form_factors()
}
for alias in _ALIASES:
    FORM_FACTOR_VOLUMES[alias] = _volume_spec(alias)


COMPONENT_VOLUMES_CM3: dict[str, float] = {
    "obc_board": 50, "eps_board": 60, "battery_pack": 200,
    "comm_uhf": 40, "comm_sband": 50, "comm_lora": 8, "adcs_unit": 150,
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
    """Validate volume budget for a configuration."""
    specs = FORM_FACTOR_VOLUMES.get(
        form_factor, FORM_FACTOR_VOLUMES.get("cubesat_3u", {})
    )
    available = specs.get("volume_cm3", 3405.0)

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
    if enabled_subsystems.get("comm_lora", False):
        items["comm_lora"] = COMPONENT_VOLUMES_CM3["comm_lora"]
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
