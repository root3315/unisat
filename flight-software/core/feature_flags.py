"""Feature flags — selective enabling of subsystems based on mission profile.

Three kinds of gates collaborate:

* **Form-factor gate**: a module may declare that it only applies to certain
  form factors (e.g. ``reaction_wheels`` requires a CubeSat 3U or larger).
* **Platform gate**: a module may only apply to certain platform categories
  (e.g. ``descent_controller`` requires CANSAT, SUBORBITAL or HAB).
* **Explicit flag**: the operator can always force-enable or force-disable a
  module via ``features.<flag>`` in ``mission_config.json``.

The resolver is deterministic:

    ``explicit override`` → ``form factor match`` → ``platform match`` →
    ``default``

which means an explicit ``false`` is always honoured and an explicit ``true``
can only be overruled by a physical-envelope check in the form-factor
registry (handled outside this module by the CLI/configurator).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Iterable

from core.form_factors import FormFactor
from core.mission_types import MissionProfile, PlatformCategory

logger = logging.getLogger("unisat.features")


@dataclass(frozen=True)
class FeatureDescriptor:
    """Describe one gated feature.

    Attributes:
        flag: Short identifier used in config (``"orbit_predictor"``).
        default: Default value when the flag is unset.
        platforms: Platform categories where this feature is applicable.
            Empty tuple = applicable to every platform.
        form_factors: Form-factor keys where this feature is applicable.
            Empty tuple = applicable to every form factor.
        requires_bands: Radio bands required for the feature to be useful.
        requires_adcs_tiers: ADCS tiers required for the feature.
        description: Human-readable description.
    """

    flag: str
    default: bool = False
    platforms: tuple[PlatformCategory, ...] = ()
    form_factors: tuple[str, ...] = ()
    requires_bands: tuple[str, ...] = ()
    requires_adcs_tiers: tuple[str, ...] = ()
    description: str = ""

    def applies_to_platform(self, platform: PlatformCategory) -> bool:
        return not self.platforms or platform in self.platforms

    def applies_to_form_factor(self, form_factor_key: str) -> bool:
        return not self.form_factors or form_factor_key in self.form_factors


# ---------------------------------------------------------------------------
# Central feature registry
# ---------------------------------------------------------------------------

FEATURES: dict[str, FeatureDescriptor] = {
    # Flight-dynamics features.
    "orbit_predictor": FeatureDescriptor(
        flag="orbit_predictor",
        default=False,
        platforms=(PlatformCategory.CUBESAT,),
        description="SGP4 / TLE propagator — orbital missions only",
    ),
    "reaction_wheels": FeatureDescriptor(
        flag="reaction_wheels",
        default=False,
        platforms=(PlatformCategory.CUBESAT,),
        form_factors=("cubesat_2u", "cubesat_3u", "cubesat_6u", "cubesat_12u"),
        requires_adcs_tiers=("reaction_wheels_1axis",
                             "reaction_wheels_3axis",
                             "reaction_wheels_with_gps",
                             "star_tracker_fine_pointing"),
        description="Reaction-wheel fine pointing",
    ),
    "magnetorquers": FeatureDescriptor(
        flag="magnetorquers",
        default=False,
        platforms=(PlatformCategory.CUBESAT,),
        requires_adcs_tiers=("magnetorquer",
                             "magnetorquer_plus_sensors",
                             "reaction_wheels_1axis",
                             "reaction_wheels_3axis"),
        description="Magnetorquer detumbling / coarse pointing",
    ),
    "star_tracker": FeatureDescriptor(
        flag="star_tracker",
        default=False,
        platforms=(PlatformCategory.CUBESAT,),
        form_factors=("cubesat_3u", "cubesat_6u", "cubesat_12u"),
        requires_adcs_tiers=("star_tracker_fine_pointing",),
        description="Star-tracker attitude determination",
    ),

    # Suborbital / descent features.
    "descent_controller": FeatureDescriptor(
        flag="descent_controller",
        default=True,
        platforms=(PlatformCategory.CANSAT,
                   PlatformCategory.SUBORBITAL_ROCKET,
                   PlatformCategory.HIGH_ALTITUDE_BALLOON),
        description="Parachute deployment + descent rate monitor",
    ),
    "parachute_pyro": FeatureDescriptor(
        flag="parachute_pyro",
        default=False,
        platforms=(PlatformCategory.CANSAT,
                   PlatformCategory.SUBORBITAL_ROCKET),
        description="Pyro ignitor for parachute deployment",
    ),
    "drogue_chute": FeatureDescriptor(
        flag="drogue_chute",
        default=False,
        platforms=(PlatformCategory.SUBORBITAL_ROCKET,),
        description="Two-stage drogue + main descent",
    ),

    # Radio features.
    "uhf_radio": FeatureDescriptor(
        flag="uhf_radio",
        default=True,
        description="UHF (amateur or ISM) down/up link",
    ),
    "s_band_radio": FeatureDescriptor(
        flag="s_band_radio",
        default=False,
        platforms=(PlatformCategory.CUBESAT,),
        form_factors=("cubesat_2u", "cubesat_3u", "cubesat_6u", "cubesat_12u"),
        requires_bands=("s_band",),
        description="S-band high-rate downlink",
    ),
    "x_band_radio": FeatureDescriptor(
        flag="x_band_radio",
        default=False,
        platforms=(PlatformCategory.CUBESAT,),
        form_factors=("cubesat_3u", "cubesat_6u", "cubesat_12u"),
        requires_bands=("x_band",),
        description="X-band very-high-rate downlink",
    ),
    "optical_comm": FeatureDescriptor(
        flag="optical_comm",
        default=False,
        platforms=(PlatformCategory.CUBESAT,),
        form_factors=("cubesat_6u", "cubesat_12u"),
        requires_bands=("optical",),
        description="Optical laser downlink",
    ),

    # Power features.
    "solar_panels": FeatureDescriptor(
        flag="solar_panels",
        default=False,
        description="Body-mounted or deployable solar panels",
    ),
    "eclipse_fdir": FeatureDescriptor(
        flag="eclipse_fdir",
        default=False,
        platforms=(PlatformCategory.CUBESAT,),
        description="FDIR logic for eclipse / low-SoC events",
    ),

    # Imaging features.
    "camera": FeatureDescriptor(
        flag="camera",
        default=False,
        description="On-board camera for Earth/lab imaging",
    ),
    "image_processor": FeatureDescriptor(
        flag="image_processor",
        default=False,
        description="On-board image compression / analytics",
    ),

    # Navigation features.
    "gnss": FeatureDescriptor(
        flag="gnss",
        default=False,
        description="GNSS receiver for position fixes",
    ),
    "imu": FeatureDescriptor(
        flag="imu",
        default=True,
        description="Inertial Measurement Unit (accel/gyro/mag)",
    ),
    "barometer": FeatureDescriptor(
        flag="barometer",
        default=False,
        platforms=(PlatformCategory.CANSAT,
                   PlatformCategory.SUBORBITAL_ROCKET,
                   PlatformCategory.HIGH_ALTITUDE_BALLOON,
                   PlatformCategory.DRONE),
        description="Barometric altimeter for atmospheric flight",
    ),

    # Propulsion.
    "propulsion": FeatureDescriptor(
        flag="propulsion",
        default=False,
        platforms=(PlatformCategory.CUBESAT,),
        form_factors=("cubesat_3u", "cubesat_6u", "cubesat_12u"),
        description="Cold-gas / electric propulsion",
    ),
}


@dataclass
class ResolvedFlags:
    """Resolved feature-flag state for a mission.

    Attributes:
        enabled: Flags resolved to True.
        disabled: Flags resolved to False.
        reasons: Map of flag -> human-readable reason (for UI + logs).
        warnings: Non-fatal advisories (e.g. envelope conflicts).
    """

    enabled: set[str] = field(default_factory=set)
    disabled: set[str] = field(default_factory=set)
    reasons: dict[str, str] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    def is_enabled(self, flag: str) -> bool:
        return flag in self.enabled

    def as_dict(self) -> dict[str, Any]:
        return {
            "enabled": sorted(self.enabled),
            "disabled": sorted(self.disabled),
            "reasons": dict(self.reasons),
            "warnings": list(self.warnings),
        }


def resolve_flags(
    profile: MissionProfile,
    form_factor: FormFactor,
    config: dict[str, Any],
) -> ResolvedFlags:
    """Resolve every registered feature flag against the mission context.

    Args:
        profile: Active mission profile.
        form_factor: Resolved form-factor specification.
        config: Raw mission configuration dict.

    Returns:
        A ResolvedFlags capturing enabled/disabled state + reasons.
    """
    explicit = dict(config.get("features", {}))
    adcs_cfg = config.get("subsystems", {}).get("adcs", {})
    adcs_tier = adcs_cfg.get("tier") or adcs_cfg.get("mode") or ""

    comm_cfg = config.get("subsystems", {}).get("comm", {})
    configured_bands = _collect_bands(comm_cfg)

    result = ResolvedFlags()

    for flag, descriptor in FEATURES.items():
        decision, reason = _decide(
            descriptor=descriptor,
            explicit_override=explicit.get(flag),
            profile=profile,
            form_factor=form_factor,
            adcs_tier=adcs_tier,
            configured_bands=configured_bands,
        )
        if decision:
            result.enabled.add(flag)
        else:
            result.disabled.add(flag)
        result.reasons[flag] = reason

    # Surface unknown flags in explicit config as warnings — typo-catcher.
    for unknown in set(explicit) - set(FEATURES):
        result.warnings.append(f"unknown feature flag in config: {unknown!r}")
        logger.warning("Ignoring unknown feature flag: %s", unknown)

    return result


def _collect_bands(comm_cfg: dict[str, Any]) -> set[str]:
    """Extract configured radio bands from the comm subsystem config."""
    bands: set[str] = set()
    if comm_cfg.get("uhf", {}).get("enabled"):
        freq = comm_cfg["uhf"].get("frequency_mhz", 0)
        if 430 <= freq <= 440:
            bands.add("uhf_amateur")
        if 433 == int(freq):
            bands.add("ism_433")
        if 868 == int(freq):
            bands.add("ism_868")
        if 915 == int(freq):
            bands.add("ism_915")
    if comm_cfg.get("s_band", {}).get("enabled"):
        bands.add("s_band")
    if comm_cfg.get("x_band", {}).get("enabled"):
        bands.add("x_band")
    if comm_cfg.get("ka_band", {}).get("enabled"):
        bands.add("ka_band")
    if comm_cfg.get("optical", {}).get("enabled"):
        bands.add("optical")
    if comm_cfg.get("lora", {}).get("enabled"):
        bands.add("lora")
    return bands


def _decide(
    *,
    descriptor: FeatureDescriptor,
    explicit_override: Any,
    profile: MissionProfile,
    form_factor: FormFactor,
    adcs_tier: str,
    configured_bands: Iterable[str],
) -> tuple[bool, str]:
    """Resolve a single flag against the five-stage pipeline.

    Returns:
        (decision, reason).
    """
    if isinstance(explicit_override, bool):
        return (
            explicit_override,
            "explicit config override" if explicit_override
            else "explicit config disable",
        )

    if not descriptor.applies_to_platform(profile.platform):
        return False, (
            f"platform {profile.platform.value} not in "
            f"{[p.value for p in descriptor.platforms]}"
        )

    if not descriptor.applies_to_form_factor(form_factor.key):
        return False, (
            f"form factor {form_factor.key!r} not in "
            f"{list(descriptor.form_factors)}"
        )

    if descriptor.requires_adcs_tiers and adcs_tier:
        if adcs_tier not in descriptor.requires_adcs_tiers:
            return False, f"ADCS tier {adcs_tier!r} incompatible"

    if descriptor.requires_bands:
        bands = set(configured_bands)
        if not bands.intersection(descriptor.requires_bands):
            return False, (
                f"radio bands {sorted(bands)} lack "
                f"{list(descriptor.requires_bands)}"
            )

    return descriptor.default, (
        "default enabled" if descriptor.default else "default disabled"
    )


def describe_flag(flag: str) -> dict[str, Any]:
    """Return a JSON-friendly descriptor for a single flag (for docs/UI)."""
    if flag not in FEATURES:
        raise KeyError(f"Unknown feature flag: {flag}")
    d = FEATURES[flag]
    return {
        "flag": d.flag,
        "default": d.default,
        "platforms": [p.value for p in d.platforms],
        "form_factors": list(d.form_factors),
        "requires_bands": list(d.requires_bands),
        "requires_adcs_tiers": list(d.requires_adcs_tiers),
        "description": d.description,
    }


def list_flags() -> list[str]:
    """List all registered feature flags."""
    return sorted(FEATURES)
