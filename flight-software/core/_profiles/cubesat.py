"""CubeSat mission profiles — LEO reference + 1U–12U size variants.

The sized profiles share the LEO phase graph (startup → deployment →
detumbling → nominal → …) but tune the module list, telemetry rate,
and safe-mode parameters to match the energy budget and typical
payload fit of that physical size. The form-factor registry is the
authoritative source for mass / volume / power envelopes; these
profiles only carry *software* defaults.
"""

from __future__ import annotations

from ..mission_types import (
    MissionProfile,
    MissionType,
    PhaseDefinition,
    PlatformCategory,
)


def cubesat_leo_profile() -> MissionProfile:
    """Reference Low-Earth-Orbit CubeSat profile."""
    return MissionProfile(
        mission_type=MissionType.CUBESAT_LEO,
        platform=PlatformCategory.CUBESAT,
        phases=[
            PhaseDefinition(
                name="startup",
                transitions_to=["deployment", "safe_mode"],
                timeout_s=300,
                auto_next="deployment",
            ),
            PhaseDefinition(
                name="deployment",
                display_name="Antenna/Panel Deployment",
                transitions_to=["detumbling", "safe_mode"],
                timeout_s=1800,
                auto_next="detumbling",
                required_modules=["telemetry", "health", "eps"],
            ),
            PhaseDefinition(
                name="detumbling",
                transitions_to=["nominal", "safe_mode"],
                timeout_s=3600,
                auto_next="nominal",
                required_modules=["telemetry", "health", "adcs", "eps"],
            ),
            PhaseDefinition(
                name="nominal",
                transitions_to=["science", "comm_window", "safe_mode", "low_power"],
                required_modules=["telemetry", "health", "adcs", "eps", "comm", "scheduler"],
            ),
            PhaseDefinition(
                name="science",
                display_name="Science/Payload Operations",
                transitions_to=["nominal", "safe_mode", "low_power"],
                required_modules=["telemetry", "health", "payload", "data_logger"],
            ),
            PhaseDefinition(
                name="comm_window",
                display_name="Communication Window",
                transitions_to=["nominal", "safe_mode"],
                required_modules=["telemetry", "comm", "data_logger"],
            ),
            PhaseDefinition(
                name="low_power",
                transitions_to=["nominal", "safe_mode"],
                required_modules=["telemetry", "health", "eps"],
                disabled_modules=["camera", "payload", "comm_sband"],
            ),
            PhaseDefinition(
                name="safe_mode",
                transitions_to=["nominal", "low_power"],
                required_modules=["telemetry", "health", "comm"],
                disabled_modules=["camera", "payload", "comm_sband", "adcs"],
            ),
        ],
        initial_phase="startup",
        core_modules=["telemetry", "data_logger", "health", "scheduler", "eps"],
        optional_modules=["comm", "adcs", "camera", "payload", "gnss", "orbit_predictor"],
        default_telemetry_hz=1.0,
        safe_mode_config={"comm_timeout_s": 86400, "beacon_interval_s": 30},
        power_config={"soc_low": 30.0, "soc_critical": 15.0},
    )


def _cubesat_sized_profile(
    mission_type: MissionType,
    form_factor_key: str,
    *,
    telemetry_hz: float,
    optional_modules: list[str],
) -> MissionProfile:
    """Build a size-specific CubeSat profile reusing the LEO phase graph."""
    leo = cubesat_leo_profile()
    return MissionProfile(
        mission_type=mission_type,
        platform=PlatformCategory.CUBESAT,
        phases=leo.phases,
        initial_phase=leo.initial_phase,
        core_modules=list(leo.core_modules),
        optional_modules=list(optional_modules),
        default_telemetry_hz=telemetry_hz,
        safe_mode_config=dict(leo.safe_mode_config),
        power_config=dict(leo.power_config),
        competition={"form_factor": form_factor_key},
    )


def cubesat_1u_profile() -> MissionProfile:
    return _cubesat_sized_profile(
        MissionType.CUBESAT_1U, "cubesat_1u",
        telemetry_hz=0.2,
        optional_modules=["comm", "gnss"],
    )


def cubesat_1_5u_profile() -> MissionProfile:
    return _cubesat_sized_profile(
        MissionType.CUBESAT_1_5U, "cubesat_1_5u",
        telemetry_hz=0.5,
        optional_modules=["comm", "gnss", "camera"],
    )


def cubesat_2u_profile() -> MissionProfile:
    return _cubesat_sized_profile(
        MissionType.CUBESAT_2U, "cubesat_2u",
        telemetry_hz=0.5,
        optional_modules=["comm", "adcs", "gnss", "camera", "payload"],
    )


def cubesat_3u_profile() -> MissionProfile:
    return _cubesat_sized_profile(
        MissionType.CUBESAT_3U, "cubesat_3u",
        telemetry_hz=1.0,
        optional_modules=["comm", "adcs", "gnss", "camera", "payload",
                          "orbit_predictor", "image_processor"],
    )


def cubesat_6u_profile() -> MissionProfile:
    return _cubesat_sized_profile(
        MissionType.CUBESAT_6U, "cubesat_6u",
        telemetry_hz=2.0,
        optional_modules=["comm", "adcs", "gnss", "camera", "payload",
                          "orbit_predictor", "image_processor"],
    )


def cubesat_12u_profile() -> MissionProfile:
    return _cubesat_sized_profile(
        MissionType.CUBESAT_12U, "cubesat_12u",
        telemetry_hz=5.0,
        optional_modules=["comm", "adcs", "gnss", "camera", "payload",
                          "orbit_predictor", "image_processor"],
    )
