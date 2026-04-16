"""Mission type registry — defines supported platforms and competition profiles.

Each MissionType describes the platform category, default mission phases,
required/optional modules, and competition-specific constraints. The flight
controller loads the appropriate profile from mission_config.json and uses
it to configure the state machine, module registry, and power manager.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any


class PlatformCategory(Enum):
    """Top-level vehicle categories."""

    CUBESAT = "cubesat"
    CANSAT = "cansat"
    SUBORBITAL_ROCKET = "suborbital_rocket"
    HIGH_ALTITUDE_BALLOON = "high_altitude_balloon"
    DRONE = "drone"
    ROVER = "rover"
    CUSTOM = "custom"


class MissionType(Enum):
    """Specific mission types with pre-built profiles."""

    # CubeSat variants
    CUBESAT_LEO = "cubesat_leo"
    CUBESAT_SSO = "cubesat_sso"
    CUBESAT_TECH_DEMO = "cubesat_tech_demo"

    # CanSat variants
    CANSAT_STANDARD = "cansat_standard"
    CANSAT_ADVANCED = "cansat_advanced"

    # Rocket variants
    ROCKET_SOUNDING = "rocket_sounding"
    ROCKET_COMPETITION = "rocket_competition"

    # HAB variants
    HAB_STANDARD = "hab_standard"
    HAB_LONG_DURATION = "hab_long_duration"

    # Drone variants
    DRONE_SURVEY = "drone_survey"
    DRONE_INSPECTION = "drone_inspection"

    # Rover
    ROVER_EXPLORATION = "rover_exploration"

    # Custom (user-defined phases and modules)
    CUSTOM = "custom"


@dataclass
class PhaseDefinition:
    """Definition of a single mission phase.

    Attributes:
        name: Machine-readable phase name (e.g. "ascent").
        display_name: Human-readable name (e.g. "Ascent Phase").
        transitions_to: Phase names this phase can transition to.
        timeout_s: Max duration before auto-transition (0 = no limit).
        auto_next: Phase to auto-transition to on timeout (empty = stay).
        required_modules: Modules that must be active in this phase.
        disabled_modules: Modules to shut down in this phase.
        entry_event: Event fired on phase entry.
        exit_event: Event fired on phase exit.
    """

    name: str
    display_name: str = ""
    transitions_to: list[str] = field(default_factory=list)
    timeout_s: float = 0.0
    auto_next: str = ""
    required_modules: list[str] = field(default_factory=list)
    disabled_modules: list[str] = field(default_factory=list)
    entry_event: str = ""
    exit_event: str = ""

    def __post_init__(self) -> None:
        if not self.display_name:
            self.display_name = self.name.replace("_", " ").title()
        if not self.entry_event:
            self.entry_event = f"phase.{self.name}.enter"
        if not self.exit_event:
            self.exit_event = f"phase.{self.name}.exit"


@dataclass
class MissionProfile:
    """Complete mission profile combining platform, phases, and modules.

    Attributes:
        mission_type: The mission type enum value.
        platform: Platform category.
        phases: Ordered list of phase definitions.
        initial_phase: Name of the starting phase.
        core_modules: Modules always loaded regardless of config.
        optional_modules: Modules loaded only if enabled in config.
        default_telemetry_hz: Default telemetry rate.
        safe_mode_config: Override safe mode parameters per mission.
        power_config: Override power thresholds per mission.
        competition: Optional competition-specific metadata.
    """

    mission_type: MissionType
    platform: PlatformCategory
    phases: list[PhaseDefinition] = field(default_factory=list)
    initial_phase: str = "startup"
    core_modules: list[str] = field(default_factory=list)
    optional_modules: list[str] = field(default_factory=list)
    default_telemetry_hz: float = 1.0
    safe_mode_config: dict[str, Any] = field(default_factory=dict)
    power_config: dict[str, Any] = field(default_factory=dict)
    competition: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Built-in mission profiles
# ---------------------------------------------------------------------------

def _cubesat_leo_profile() -> MissionProfile:
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


def _cansat_standard_profile() -> MissionProfile:
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
            "can_diameter_mm": 64,
            "can_height_mm": 68,
            "capsule_height_mm": 80,
            "descent_rate_range_m_s": [6.0, 11.0],
            "max_landing_velocity_m_s": 12.0,
            "min_telemetry_samples": 100,
        },
    )


def _rocket_competition_profile() -> MissionProfile:
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


def _hab_standard_profile() -> MissionProfile:
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


def _drone_survey_profile() -> MissionProfile:
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


# ---------------------------------------------------------------------------
# Profile registry
# ---------------------------------------------------------------------------

_PROFILES: dict[MissionType, MissionProfile] = {}


def _register_builtins() -> None:
    """Register all built-in mission profiles."""
    for factory in [
        _cubesat_leo_profile,
        _cansat_standard_profile,
        _rocket_competition_profile,
        _hab_standard_profile,
        _drone_survey_profile,
    ]:
        profile = factory()
        _PROFILES[profile.mission_type] = profile


_register_builtins()


def get_mission_profile(mission_type: MissionType | str) -> MissionProfile:
    """Look up a built-in mission profile by type.

    Args:
        mission_type: MissionType enum or its string value.

    Returns:
        The matching MissionProfile.

    Raises:
        KeyError: If no profile matches the given type.
    """
    if isinstance(mission_type, str):
        try:
            mission_type = MissionType(mission_type)
        except ValueError as exc:
            raise KeyError(f"Unknown mission type: {mission_type}") from exc
    if mission_type not in _PROFILES:
        raise KeyError(f"No built-in profile for mission type: {mission_type.value}")
    return _PROFILES[mission_type]


def register_mission_profile(profile: MissionProfile) -> None:
    """Register a custom mission profile.

    Args:
        profile: The profile to register (overrides existing if same type).
    """
    _PROFILES[profile.mission_type] = profile


def list_mission_types() -> list[str]:
    """Return list of all registered mission type names."""
    return [mt.value for mt in _PROFILES]


def build_profile_from_config(config: dict) -> MissionProfile:
    """Build a MissionProfile from a mission_config.json dict.

    If config contains a known ``mission_type``, the built-in profile is
    loaded and then overridden by any explicit config values.  If the type
    is ``custom``, the profile is built entirely from config.

    Args:
        config: Parsed mission_config.json content.

    Returns:
        A fully resolved MissionProfile.
    """
    mission_cfg = config.get("mission", {})
    mission_type_str = mission_cfg.get("mission_type", "cubesat_leo")

    try:
        base = copy.deepcopy(get_mission_profile(mission_type_str))
    except (KeyError, ValueError):
        base = MissionProfile(
            mission_type=MissionType.CUSTOM,
            platform=PlatformCategory(mission_cfg.get("platform", "custom")),
        )

    # Override phases from config if provided
    phases_cfg = mission_cfg.get("phases")
    if phases_cfg:
        base.phases = [
            PhaseDefinition(**p) for p in phases_cfg
        ]
        if mission_cfg.get("initial_phase"):
            base.initial_phase = mission_cfg["initial_phase"]

    # Override module lists
    if "core_modules" in mission_cfg:
        base.core_modules = mission_cfg["core_modules"]
    if "optional_modules" in mission_cfg:
        base.optional_modules = mission_cfg["optional_modules"]

    # Override telemetry rate
    if "telemetry_hz" in mission_cfg:
        base.default_telemetry_hz = mission_cfg["telemetry_hz"]

    # Override safe mode / power
    if "safe_mode" in config:
        base.safe_mode_config.update(config["safe_mode"])
    if "power" in config:
        base.power_config.update(config["power"])

    # Competition metadata
    if "competition" in mission_cfg:
        base.competition.update(mission_cfg["competition"])

    return base
