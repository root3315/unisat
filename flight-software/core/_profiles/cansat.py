"""CanSat mission profiles — minimal / standard / advanced.

The three variants share the same phase graph (pre_launch →
launch_detect → ascent → apogee → descent → landed). They differ in
module lists, telemetry rate, and regulation envelopes.
"""

from __future__ import annotations

from ..mission_types import (
    MissionProfile,
    MissionType,
    PhaseDefinition,
    PlatformCategory,
)


def cansat_standard_profile() -> MissionProfile:
    """CDS-compliant CanSat (≤500 g, Ø68 × 80 mm)."""
    return MissionProfile(
        mission_type=MissionType.CANSAT_STANDARD,
        platform=PlatformCategory.CANSAT,
        phases=[
            PhaseDefinition(
                name="pre_launch",
                display_name="Pre-Launch / Ground Checkout",
                transitions_to=["launch_detect"],
                required_modules=["telemetry", "health", "imu", "barometer"],
            ),
            PhaseDefinition(
                name="launch_detect",
                display_name="Launch Detection",
                transitions_to=["ascent", "pre_launch"],
                timeout_s=600,
                auto_next="pre_launch",
                required_modules=["telemetry", "imu", "barometer"],
            ),
            PhaseDefinition(
                name="ascent",
                transitions_to=["apogee"],
                timeout_s=120,
                auto_next="apogee",
                required_modules=["telemetry", "imu", "barometer", "data_logger"],
            ),
            PhaseDefinition(
                name="apogee",
                display_name="Apogee / Ejection",
                transitions_to=["descent"],
                timeout_s=30,
                auto_next="descent",
                required_modules=["telemetry", "imu", "barometer", "descent_controller"],
            ),
            PhaseDefinition(
                name="descent",
                display_name="Parachute Descent",
                transitions_to=["landed"],
                timeout_s=300,
                auto_next="landed",
                required_modules=["telemetry", "imu", "barometer", "descent_controller",
                                  "data_logger", "payload"],
            ),
            PhaseDefinition(
                name="landed",
                transitions_to=[],
                timeout_s=3600,
                required_modules=["telemetry", "comm"],
                disabled_modules=["descent_controller"],
            ),
        ],
        initial_phase="pre_launch",
        core_modules=["telemetry", "data_logger", "health", "imu", "barometer"],
        optional_modules=["comm", "camera", "payload", "descent_controller", "gnss"],
        default_telemetry_hz=10.0,
        safe_mode_config={"comm_timeout_s": 300, "beacon_interval_s": 5},
        power_config={"soc_low": 20.0, "soc_critical": 10.0},
        competition={
            "type": "cansat",
            "max_mass_g": 500,
            "outer_diameter_mm": 68,
            "inner_diameter_mm": 64,
            "height_mm": 80,
            "descent_rate_range_m_s": [6.0, 11.0],
            "max_landing_velocity_m_s": 12.0,
            "min_telemetry_samples": 100,
        },
    )


def cansat_minimal_profile() -> MissionProfile:
    """Lightweight CanSat (≤350 g) — telemetry only, no parachute pyro."""
    base = cansat_standard_profile()
    return MissionProfile(
        mission_type=MissionType.CANSAT_MINIMAL,
        platform=PlatformCategory.CANSAT,
        phases=base.phases,
        initial_phase=base.initial_phase,
        core_modules=["telemetry", "data_logger", "health", "imu", "barometer"],
        optional_modules=["comm", "gnss"],
        default_telemetry_hz=4.0,
        safe_mode_config=dict(base.safe_mode_config),
        power_config={"soc_low": 20.0, "soc_critical": 10.0},
        competition={
            "type": "cansat",
            "form_factor": "cansat_minimal",
            "max_mass_g": 350,
            "outer_diameter_mm": 66,
            "inner_diameter_mm": 64,
            "height_mm": 115,
            "descent_rate_range_m_s": [5.0, 15.0],
        },
    )


def cansat_advanced_profile() -> MissionProfile:
    """Advanced CanSat with autorotator, secondary payload, guided descent."""
    base = cansat_standard_profile()
    return MissionProfile(
        mission_type=MissionType.CANSAT_ADVANCED,
        platform=PlatformCategory.CANSAT,
        phases=base.phases,
        initial_phase=base.initial_phase,
        core_modules=list(base.core_modules) + ["descent_controller"],
        optional_modules=["comm", "camera", "payload", "gnss", "image_processor"],
        default_telemetry_hz=20.0,
        safe_mode_config=dict(base.safe_mode_config),
        power_config={"soc_low": 25.0, "soc_critical": 12.0},
        competition={
            "type": "cansat",
            "form_factor": "cansat_advanced",
            "max_mass_g": 500,
            "outer_diameter_mm": 68,
            "inner_diameter_mm": 64,
            "height_mm": 115,
            "descent_rate_range_m_s": [6.0, 11.0],
            "max_landing_velocity_m_s": 12.0,
            "min_telemetry_samples": 200,
        },
    )
