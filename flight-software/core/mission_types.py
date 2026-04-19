"""Mission type registry — platform categories, phases, and profile lookup.

Public surface:
    * :class:`PlatformCategory` — top-level vehicle category.
    * :class:`MissionType` — concrete profile identifier.
    * :class:`PhaseDefinition` — one phase in a mission.
    * :class:`MissionProfile` — full profile (phases + modules + metadata).
    * :func:`get_mission_profile` — lookup by ``MissionType``.
    * :func:`register_mission_profile` — register a custom profile.
    * :func:`list_mission_types` — every registered type.
    * :func:`build_profile_from_config` — resolve from ``mission_config.json``.

Built-in profiles live in :mod:`core._profiles` and are registered on
module import. The flight controller consumes
:func:`get_mission_profile` to configure the state machine, module
registry, and power manager.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from enum import Enum
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

    # CubeSat variants by orbit / role
    CUBESAT_LEO = "cubesat_leo"
    CUBESAT_SSO = "cubesat_sso"
    CUBESAT_TECH_DEMO = "cubesat_tech_demo"

    # CubeSat variants by physical size (1U-12U).
    # These share the LEO phase graph but bring form-factor-specific module
    # lists and resource envelopes loaded through the FormFactor registry.
    CUBESAT_1U = "cubesat_1u"
    CUBESAT_1_5U = "cubesat_1_5u"
    CUBESAT_2U = "cubesat_2u"
    CUBESAT_3U = "cubesat_3u"
    CUBESAT_6U = "cubesat_6u"
    CUBESAT_12U = "cubesat_12u"

    # CanSat variants
    CANSAT_MINIMAL = "cansat_minimal"
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
# Profile registry
# ---------------------------------------------------------------------------

_PROFILES: dict[MissionType, MissionProfile] = {}


def _register_builtins() -> None:
    """Register all built-in mission profiles from ``core._profiles``."""
    # Imported here to avoid a circular import: _profiles/*.py depend on
    # MissionProfile / MissionType / PhaseDefinition / PlatformCategory
    # defined above.
    from . import _profiles  # noqa: PLC0415

    for factory in _profiles.BUILTIN_FACTORIES:
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


def build_profile_from_config(config: dict[str, Any]) -> MissionProfile:
    """Build a MissionProfile from a mission_config.json dict.

    If config contains a known ``mission_type``, the built-in profile is
    loaded and then overridden by any explicit config values. If the type
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
        base.phases = [PhaseDefinition(**p) for p in phases_cfg]
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
