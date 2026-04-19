"""Suborbital-rocket, high-altitude-balloon, and drone mission profiles."""

from __future__ import annotations

from ..mission_types import (
    MissionProfile,
    MissionType,
    PhaseDefinition,
    PlatformCategory,
)


def rocket_competition_profile() -> MissionProfile:
    """Student / competition rocket (SA Cup, IREC, Team America)."""
    return MissionProfile(
        mission_type=MissionType.ROCKET_COMPETITION,
        platform=PlatformCategory.SUBORBITAL_ROCKET,
        phases=[
            PhaseDefinition(
                name="ground_checkout",
                display_name="Ground Checkout",
                transitions_to=["armed"],
                required_modules=["telemetry", "health", "imu"],
            ),
            PhaseDefinition(
                name="armed",
                transitions_to=["boost", "ground_checkout"],
                timeout_s=600,
                auto_next="ground_checkout",
                required_modules=["telemetry", "imu", "barometer"],
            ),
            PhaseDefinition(
                name="boost",
                display_name="Boost Phase",
                transitions_to=["coast"],
                timeout_s=30,
                auto_next="coast",
                required_modules=["telemetry", "imu", "barometer", "data_logger"],
            ),
            PhaseDefinition(
                name="coast",
                display_name="Coast Phase",
                transitions_to=["apogee"],
                timeout_s=60,
                auto_next="apogee",
                required_modules=["telemetry", "imu", "barometer", "data_logger"],
            ),
            PhaseDefinition(
                name="apogee",
                transitions_to=["drogue_descent"],
                timeout_s=10,
                auto_next="drogue_descent",
                required_modules=["telemetry", "imu", "barometer"],
            ),
            PhaseDefinition(
                name="drogue_descent",
                display_name="Drogue Descent",
                transitions_to=["main_descent"],
                required_modules=["telemetry", "imu", "barometer", "data_logger"],
            ),
            PhaseDefinition(
                name="main_descent",
                display_name="Main Chute Descent",
                transitions_to=["landed"],
                required_modules=["telemetry", "imu", "barometer", "data_logger"],
            ),
            PhaseDefinition(
                name="landed",
                transitions_to=[],
                required_modules=["telemetry", "comm"],
            ),
        ],
        initial_phase="ground_checkout",
        core_modules=["telemetry", "data_logger", "health", "imu", "barometer"],
        optional_modules=["comm", "payload", "gnss", "camera"],
        default_telemetry_hz=20.0,
        safe_mode_config={"comm_timeout_s": 600, "beacon_interval_s": 10},
        power_config={"soc_low": 20.0, "soc_critical": 10.0},
        competition={
            "type": "rocket",
            "target_altitude_m": 3048,
            "max_acceleration_g": 20,
        },
    )


def hab_standard_profile() -> MissionProfile:
    """Standard high-altitude balloon flight."""
    return MissionProfile(
        mission_type=MissionType.HAB_STANDARD,
        platform=PlatformCategory.HIGH_ALTITUDE_BALLOON,
        phases=[
            PhaseDefinition(
                name="ground_setup",
                display_name="Ground Setup / Inflation",
                transitions_to=["ascent"],
                required_modules=["telemetry", "health", "barometer"],
            ),
            PhaseDefinition(
                name="ascent",
                transitions_to=["float", "burst"],
                timeout_s=10800,
                auto_next="float",
                required_modules=["telemetry", "health", "barometer", "gnss",
                                  "data_logger", "payload", "camera"],
            ),
            PhaseDefinition(
                name="float",
                display_name="Float Altitude",
                transitions_to=["burst"],
                timeout_s=7200,
                auto_next="burst",
                required_modules=["telemetry", "health", "barometer", "gnss",
                                  "data_logger", "payload", "camera"],
            ),
            PhaseDefinition(
                name="burst",
                display_name="Balloon Burst",
                transitions_to=["descent"],
                timeout_s=10,
                auto_next="descent",
                required_modules=["telemetry", "barometer", "gnss"],
            ),
            PhaseDefinition(
                name="descent",
                transitions_to=["landed"],
                timeout_s=5400,
                auto_next="landed",
                required_modules=["telemetry", "barometer", "gnss", "comm", "data_logger"],
            ),
            PhaseDefinition(
                name="landed",
                transitions_to=[],
                required_modules=["telemetry", "comm", "gnss"],
            ),
        ],
        initial_phase="ground_setup",
        core_modules=["telemetry", "data_logger", "health", "barometer", "gnss"],
        optional_modules=["comm", "camera", "payload", "imu"],
        default_telemetry_hz=0.5,
        safe_mode_config={"comm_timeout_s": 7200, "beacon_interval_s": 60},
        power_config={"soc_low": 25.0, "soc_critical": 10.0},
    )


def drone_survey_profile() -> MissionProfile:
    """Small-UAS survey / inspection profile."""
    return MissionProfile(
        mission_type=MissionType.DRONE_SURVEY,
        platform=PlatformCategory.DRONE,
        phases=[
            PhaseDefinition(
                name="preflight",
                display_name="Pre-Flight Check",
                transitions_to=["armed"],
                required_modules=["telemetry", "health", "imu", "gnss"],
            ),
            PhaseDefinition(
                name="armed",
                transitions_to=["takeoff", "preflight"],
                timeout_s=120,
                auto_next="preflight",
                required_modules=["telemetry", "health", "imu", "gnss"],
            ),
            PhaseDefinition(
                name="takeoff",
                transitions_to=["mission_flight"],
                timeout_s=60,
                auto_next="mission_flight",
                required_modules=["telemetry", "imu", "gnss", "barometer"],
            ),
            PhaseDefinition(
                name="mission_flight",
                display_name="Mission Flight",
                transitions_to=["return_to_home", "landing", "emergency"],
                required_modules=["telemetry", "imu", "gnss", "camera",
                                  "payload", "data_logger"],
            ),
            PhaseDefinition(
                name="return_to_home",
                display_name="Return to Home",
                transitions_to=["landing", "emergency"],
                required_modules=["telemetry", "imu", "gnss"],
                disabled_modules=["camera", "payload"],
            ),
            PhaseDefinition(
                name="landing",
                transitions_to=["landed"],
                timeout_s=120,
                auto_next="landed",
                required_modules=["telemetry", "imu", "gnss", "barometer"],
            ),
            PhaseDefinition(
                name="landed",
                transitions_to=["preflight"],
                required_modules=["telemetry", "health"],
            ),
            PhaseDefinition(
                name="emergency",
                display_name="Emergency Landing",
                transitions_to=["landed"],
                required_modules=["telemetry", "imu", "gnss"],
                disabled_modules=["camera", "payload"],
            ),
        ],
        initial_phase="preflight",
        core_modules=["telemetry", "data_logger", "health", "imu", "gnss", "barometer"],
        optional_modules=["comm", "camera", "payload"],
        default_telemetry_hz=10.0,
        safe_mode_config={"comm_timeout_s": 300, "beacon_interval_s": 5},
        power_config={"soc_low": 25.0, "soc_critical": 15.0},
    )
