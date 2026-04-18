"""Form-factor registry — physical envelopes for every supported platform.

Each FormFactor captures the mass, volume, power, and mechanical envelope
constraints of a specific vehicle class. It is the single source of truth
consumed by the mass budget tool, the power budget tool, the configurator,
and by guards inside the flight software that reject misconfigured missions.

Supported classes:
    * CanSat variants (minimal / standard / advanced)
    * CubeSat sizes 1U, 1.5U, 2U, 3U, 6U, 12U
    * Suborbital rocket payload, HAB, drone, rover
    * ``custom`` for user-defined shapes

Numeric envelopes below follow the published standards (CDS Rev. 14 for
CubeSats, ESA/ESTEC CanSat regulations, and common team experience).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class FormFactorClass(Enum):
    """Top-level form-factor families."""

    CANSAT = "cansat"
    CUBESAT = "cubesat"
    SUBORBITAL = "suborbital"
    HAB = "hab"
    DRONE = "drone"
    ROVER = "rover"
    CUSTOM = "custom"


@dataclass(frozen=True)
class MassEnvelope:
    """Allowed mass range in kilograms.

    Attributes:
        min_kg: Lower bound (useful for sanity checks, usually 0).
        max_kg: Upper bound enforced by the regulation.
        nominal_kg: Typical mass used by the default budget.
    """

    min_kg: float
    max_kg: float
    nominal_kg: float


@dataclass(frozen=True)
class VolumeEnvelope:
    """Bounding box / cylindrical envelope in millimetres."""

    shape: str
    dimensions_mm: dict[str, float]
    volume_cm3: float


@dataclass(frozen=True)
class PowerEnvelope:
    """Typical power envelope for the form factor (for budgeting only).

    Attributes:
        peak_w: Maximum instantaneous power draw.
        average_w: Orbit- or mission-averaged power draw.
        battery_capacity_wh_typical: Reference battery size.
        solar_capable: Whether surface-mounted solar is mechanically possible.
    """

    peak_w: float
    average_w: float
    battery_capacity_wh_typical: float
    solar_capable: bool


@dataclass(frozen=True)
class FormFactor:
    """Full physical specification of a vehicle class.

    Attributes:
        key: Machine-readable identifier, e.g. ``"cubesat_3u"``.
        display_name: Human-readable label.
        family: Top-level class (``CUBESAT``, ``CANSAT`` …).
        mass: Mass envelope.
        volume: Mechanical envelope.
        power: Power envelope.
        allowed_adcs_tiers: ADCS tiers mechanically feasible for this shape.
        allowed_comm_bands: Radio bands typically flown with this shape.
        max_deployables: Maximum number of deployable panels / antennas.
        supports_propulsion: Whether propulsion modules are usable.
        regulation_notes: Free-form reference to the governing rulebook.
    """

    key: str
    display_name: str
    family: FormFactorClass
    mass: MassEnvelope
    volume: VolumeEnvelope
    power: PowerEnvelope
    allowed_adcs_tiers: tuple[str, ...]
    allowed_comm_bands: tuple[str, ...]
    max_deployables: int = 0
    supports_propulsion: bool = False
    regulation_notes: str = ""
    extra: dict[str, Any] = field(default_factory=dict)

    def check_mass(self, mass_kg: float) -> tuple[bool, str]:
        """Verify a mass against the envelope.

        Returns:
            (ok, message) — ``ok=False`` flags a regulation violation.
        """
        if mass_kg < self.mass.min_kg:
            return False, (
                f"mass {mass_kg:.3f} kg below minimum "
                f"{self.mass.min_kg:.3f} kg for {self.display_name}"
            )
        if mass_kg > self.mass.max_kg:
            return False, (
                f"mass {mass_kg:.3f} kg exceeds maximum "
                f"{self.mass.max_kg:.3f} kg for {self.display_name}"
            )
        return True, "mass within envelope"

    def is_adcs_tier_supported(self, tier: str) -> bool:
        """Check whether an ADCS tier is mechanically possible."""
        return tier in self.allowed_adcs_tiers

    def is_comm_band_supported(self, band: str) -> bool:
        """Check whether a radio band is typically flown on this class."""
        return band in self.allowed_comm_bands


# ---------------------------------------------------------------------------
# Built-in form factors
# ---------------------------------------------------------------------------

# Standard CubeSat unit volume is 100 x 100 x 113.5 mm (CDS Rev. 14).
_U = {"x_mm": 100.0, "y_mm": 100.0, "z_mm": 113.5}
_U_VOL_CM3 = 100.0 * 100.0 * 113.5 / 1000.0  # one U ≈ 1135 cm^3


def _cubesat_volume(units: float) -> VolumeEnvelope:
    """Return a stacked-U bounding box (along +Z)."""
    return VolumeEnvelope(
        shape="rectangular",
        dimensions_mm={"x": 100.0, "y": 100.0, "z": 113.5 * units},
        volume_cm3=_U_VOL_CM3 * units,
    )


_FORM_FACTORS: dict[str, FormFactor] = {}


def _register(form_factor: FormFactor) -> None:
    _FORM_FACTORS[form_factor.key] = form_factor


# --- CanSat family ---------------------------------------------------------

_register(FormFactor(
    key="cansat_minimal",
    display_name="CanSat Minimal (≤350 g)",
    family=FormFactorClass.CANSAT,
    mass=MassEnvelope(min_kg=0.10, max_kg=0.35, nominal_kg=0.30),
    volume=VolumeEnvelope(
        shape="cylindrical",
        dimensions_mm={"outer_d": 66.0, "inner_d": 64.0, "height": 115.0},
        volume_cm3=393.0,
    ),
    power=PowerEnvelope(peak_w=1.5, average_w=0.6,
                        battery_capacity_wh_typical=2.0, solar_capable=False),
    allowed_adcs_tiers=("none",),
    allowed_comm_bands=("ism_433", "ism_868", "ism_915"),
    max_deployables=1,
    regulation_notes="Simple telemetry CanSat — no active control",
))

_register(FormFactor(
    key="cansat_standard",
    display_name="CanSat Standard (≤500 g)",
    family=FormFactorClass.CANSAT,
    mass=MassEnvelope(min_kg=0.30, max_kg=0.50, nominal_kg=0.45),
    volume=VolumeEnvelope(
        shape="cylindrical",
        dimensions_mm={"outer_d": 68.0, "inner_d": 64.0, "height": 80.0},
        volume_cm3=260.0,
    ),
    power=PowerEnvelope(peak_w=2.5, average_w=1.0,
                        battery_capacity_wh_typical=3.3, solar_capable=False),
    allowed_adcs_tiers=("none",),
    allowed_comm_bands=("ism_433", "ism_868", "ism_915", "lora"),
    max_deployables=2,
    regulation_notes="Competition-standard CanSat: 68 mm outer diameter, 500 g",
))

_register(FormFactor(
    key="cansat_advanced",
    display_name="CanSat Advanced (≤500 g, active descent)",
    family=FormFactorClass.CANSAT,
    mass=MassEnvelope(min_kg=0.35, max_kg=0.50, nominal_kg=0.49),
    volume=VolumeEnvelope(
        shape="cylindrical",
        dimensions_mm={"outer_d": 68.0, "inner_d": 64.0, "height": 115.0},
        volume_cm3=372.0,
    ),
    power=PowerEnvelope(peak_w=4.0, average_w=1.5,
                        battery_capacity_wh_typical=5.0, solar_capable=False),
    allowed_adcs_tiers=("none", "passive_spin"),
    allowed_comm_bands=("ism_433", "ism_868", "ism_915", "lora", "uhf_amateur"),
    max_deployables=3,
    regulation_notes="CanSat with autorotator or guided descent — still 500 g limit",
))


# --- CubeSat family --------------------------------------------------------

_register(FormFactor(
    key="cubesat_1u",
    display_name="CubeSat 1U",
    family=FormFactorClass.CUBESAT,
    mass=MassEnvelope(min_kg=0.20, max_kg=2.00, nominal_kg=1.33),
    volume=_cubesat_volume(1.0),
    power=PowerEnvelope(peak_w=3.0, average_w=1.0,
                        battery_capacity_wh_typical=10.0, solar_capable=True),
    allowed_adcs_tiers=("none", "passive_magnetic", "magnetorquer",
                        "magnetorquer_plus_sensors"),
    allowed_comm_bands=("uhf_amateur", "vhf_amateur"),
    max_deployables=4,
    regulation_notes="CDS Rev. 14 — 1U envelope, 2 kg hard limit",
))

_register(FormFactor(
    key="cubesat_1_5u",
    display_name="CubeSat 1.5U",
    family=FormFactorClass.CUBESAT,
    mass=MassEnvelope(min_kg=0.30, max_kg=3.00, nominal_kg=2.00),
    volume=_cubesat_volume(1.5),
    power=PowerEnvelope(peak_w=5.0, average_w=1.8,
                        battery_capacity_wh_typical=15.0, solar_capable=True),
    allowed_adcs_tiers=("none", "passive_magnetic", "magnetorquer",
                        "magnetorquer_plus_sensors"),
    allowed_comm_bands=("uhf_amateur", "vhf_amateur"),
    max_deployables=4,
    regulation_notes="CDS Rev. 14 — 1.5U envelope",
))

_register(FormFactor(
    key="cubesat_2u",
    display_name="CubeSat 2U",
    family=FormFactorClass.CUBESAT,
    mass=MassEnvelope(min_kg=0.50, max_kg=4.00, nominal_kg=2.66),
    volume=_cubesat_volume(2.0),
    power=PowerEnvelope(peak_w=7.0, average_w=2.5,
                        battery_capacity_wh_typical=20.0, solar_capable=True),
    allowed_adcs_tiers=("passive_magnetic", "magnetorquer",
                        "magnetorquer_plus_sensors",
                        "reaction_wheels_1axis"),
    allowed_comm_bands=("uhf_amateur", "vhf_amateur", "s_band"),
    max_deployables=6,
    regulation_notes="CDS Rev. 14 — 2U envelope",
))

_register(FormFactor(
    key="cubesat_3u",
    display_name="CubeSat 3U",
    family=FormFactorClass.CUBESAT,
    mass=MassEnvelope(min_kg=0.80, max_kg=6.00, nominal_kg=4.00),
    volume=_cubesat_volume(3.0),
    power=PowerEnvelope(peak_w=12.0, average_w=4.0,
                        battery_capacity_wh_typical=30.0, solar_capable=True),
    allowed_adcs_tiers=("passive_magnetic", "magnetorquer",
                        "magnetorquer_plus_sensors",
                        "reaction_wheels_3axis",
                        "reaction_wheels_with_gps"),
    allowed_comm_bands=("uhf_amateur", "vhf_amateur", "s_band", "x_band"),
    max_deployables=8,
    supports_propulsion=True,
    regulation_notes="CDS Rev. 14 — 3U envelope (LEO workhorse)",
))

_register(FormFactor(
    key="cubesat_6u",
    display_name="CubeSat 6U",
    family=FormFactorClass.CUBESAT,
    mass=MassEnvelope(min_kg=2.00, max_kg=12.00, nominal_kg=8.00),
    volume=VolumeEnvelope(
        shape="rectangular",
        dimensions_mm={"x": 226.3, "y": 100.0, "z": 366.0},
        volume_cm3=8280.0,
    ),
    power=PowerEnvelope(peak_w=25.0, average_w=8.0,
                        battery_capacity_wh_typical=80.0, solar_capable=True),
    allowed_adcs_tiers=("magnetorquer_plus_sensors",
                        "reaction_wheels_3axis",
                        "reaction_wheels_with_gps",
                        "star_tracker_fine_pointing"),
    allowed_comm_bands=("uhf_amateur", "s_band", "x_band", "ka_band"),
    max_deployables=12,
    supports_propulsion=True,
    regulation_notes="NASA 6U standard envelope 226.3 x 100 x 366 mm",
))

_register(FormFactor(
    key="cubesat_12u",
    display_name="CubeSat 12U",
    family=FormFactorClass.CUBESAT,
    mass=MassEnvelope(min_kg=4.00, max_kg=24.00, nominal_kg=16.00),
    volume=VolumeEnvelope(
        shape="rectangular",
        dimensions_mm={"x": 226.3, "y": 226.3, "z": 366.0},
        volume_cm3=18725.0,
    ),
    power=PowerEnvelope(peak_w=45.0, average_w=15.0,
                        battery_capacity_wh_typical=160.0, solar_capable=True),
    allowed_adcs_tiers=("reaction_wheels_3axis",
                        "reaction_wheels_with_gps",
                        "star_tracker_fine_pointing"),
    allowed_comm_bands=("s_band", "x_band", "ka_band", "optical"),
    max_deployables=16,
    supports_propulsion=True,
    regulation_notes="12U envelope — research-class LEO/deep-space missions",
))


# --- Other platforms -------------------------------------------------------

_register(FormFactor(
    key="rocket_payload",
    display_name="Sounding-rocket payload",
    family=FormFactorClass.SUBORBITAL,
    mass=MassEnvelope(min_kg=0.10, max_kg=10.00, nominal_kg=1.50),
    volume=VolumeEnvelope(
        shape="cylindrical",
        dimensions_mm={"outer_d": 100.0, "height": 300.0},
        volume_cm3=2360.0,
    ),
    power=PowerEnvelope(peak_w=10.0, average_w=3.0,
                        battery_capacity_wh_typical=12.0, solar_capable=False),
    allowed_adcs_tiers=("none", "passive_spin"),
    allowed_comm_bands=("ism_433", "ism_915", "uhf_amateur", "s_band"),
    max_deployables=2,
    regulation_notes="Variable — check launch provider envelope",
))

_register(FormFactor(
    key="hab_payload",
    display_name="High-altitude balloon payload",
    family=FormFactorClass.HAB,
    mass=MassEnvelope(min_kg=0.10, max_kg=4.00, nominal_kg=1.00),
    volume=VolumeEnvelope(
        shape="rectangular",
        dimensions_mm={"x": 150.0, "y": 150.0, "z": 150.0},
        volume_cm3=3375.0,
    ),
    power=PowerEnvelope(peak_w=5.0, average_w=1.2,
                        battery_capacity_wh_typical=30.0, solar_capable=True),
    allowed_adcs_tiers=("none",),
    allowed_comm_bands=("ism_433", "ism_868", "ism_915", "aprs", "uhf_amateur"),
    max_deployables=0,
    regulation_notes="FAA Part 101 / equivalent national rules",
))

_register(FormFactor(
    key="drone_small",
    display_name="Small UAS (<5 kg)",
    family=FormFactorClass.DRONE,
    mass=MassEnvelope(min_kg=0.25, max_kg=5.00, nominal_kg=1.50),
    volume=VolumeEnvelope(
        shape="rectangular",
        dimensions_mm={"x": 500.0, "y": 500.0, "z": 200.0},
        volume_cm3=50000.0,
    ),
    power=PowerEnvelope(peak_w=200.0, average_w=80.0,
                        battery_capacity_wh_typical=100.0, solar_capable=False),
    allowed_adcs_tiers=("imu_attitude_control",),
    allowed_comm_bands=("ism_433", "ism_868", "ism_915", "ism_2400"),
    max_deployables=0,
    regulation_notes="Regulated under national civil aviation authority",
))

_register(FormFactor(
    key="rover_small",
    display_name="Small ground rover",
    family=FormFactorClass.ROVER,
    mass=MassEnvelope(min_kg=1.0, max_kg=30.0, nominal_kg=8.0),
    volume=VolumeEnvelope(
        shape="rectangular",
        dimensions_mm={"x": 400.0, "y": 300.0, "z": 250.0},
        volume_cm3=30000.0,
    ),
    power=PowerEnvelope(peak_w=80.0, average_w=15.0,
                        battery_capacity_wh_typical=150.0, solar_capable=True),
    allowed_adcs_tiers=("none", "imu_attitude_control"),
    allowed_comm_bands=("ism_433", "ism_915", "ism_2400", "uhf_amateur"),
    max_deployables=0,
    regulation_notes="Not applicable — ground vehicle",
))

_register(FormFactor(
    key="custom",
    display_name="Custom platform",
    family=FormFactorClass.CUSTOM,
    mass=MassEnvelope(min_kg=0.0, max_kg=1000.0, nominal_kg=1.0),
    volume=VolumeEnvelope(
        shape="custom", dimensions_mm={}, volume_cm3=0.0,
    ),
    power=PowerEnvelope(peak_w=0.0, average_w=0.0,
                        battery_capacity_wh_typical=0.0, solar_capable=False),
    allowed_adcs_tiers=("none", "passive_magnetic", "passive_spin",
                        "magnetorquer", "magnetorquer_plus_sensors",
                        "reaction_wheels_1axis",
                        "reaction_wheels_3axis",
                        "reaction_wheels_with_gps",
                        "star_tracker_fine_pointing",
                        "imu_attitude_control"),
    allowed_comm_bands=("ism_433", "ism_868", "ism_915", "ism_2400",
                        "lora", "aprs", "uhf_amateur", "vhf_amateur",
                        "s_band", "x_band", "ka_band", "optical"),
    max_deployables=99,
    supports_propulsion=True,
    regulation_notes="User-defined — no built-in checks",
))


def get_form_factor(key: str) -> FormFactor:
    """Look up a form factor by key.

    Args:
        key: Identifier such as ``"cubesat_3u"`` or ``"cansat_standard"``.

    Returns:
        The matching FormFactor.

    Raises:
        KeyError: If the key is unknown.
    """
    if key not in _FORM_FACTORS:
        raise KeyError(
            f"Unknown form factor: {key!r}. Known: {sorted(_FORM_FACTORS)}"
        )
    return _FORM_FACTORS[key]


def list_form_factors() -> list[str]:
    """Return all registered form factor keys."""
    return sorted(_FORM_FACTORS)


def list_by_family(family: FormFactorClass | str) -> list[FormFactor]:
    """Return all form factors in a given family."""
    if isinstance(family, str):
        family = FormFactorClass(family)
    return [f for f in _FORM_FACTORS.values() if f.family == family]


def summarise(form_factor: FormFactor) -> dict[str, Any]:
    """Serialise a form factor to a JSON-friendly dict for UI rendering."""
    return {
        "key": form_factor.key,
        "display_name": form_factor.display_name,
        "family": form_factor.family.value,
        "mass": {
            "min_kg": form_factor.mass.min_kg,
            "max_kg": form_factor.mass.max_kg,
            "nominal_kg": form_factor.mass.nominal_kg,
        },
        "volume": {
            "shape": form_factor.volume.shape,
            "dimensions_mm": dict(form_factor.volume.dimensions_mm),
            "volume_cm3": form_factor.volume.volume_cm3,
        },
        "power": {
            "peak_w": form_factor.power.peak_w,
            "average_w": form_factor.power.average_w,
            "battery_capacity_wh_typical":
                form_factor.power.battery_capacity_wh_typical,
            "solar_capable": form_factor.power.solar_capable,
        },
        "adcs_tiers": list(form_factor.allowed_adcs_tiers),
        "comm_bands": list(form_factor.allowed_comm_bands),
        "max_deployables": form_factor.max_deployables,
        "supports_propulsion": form_factor.supports_propulsion,
        "regulation_notes": form_factor.regulation_notes,
    }
