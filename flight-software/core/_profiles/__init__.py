"""Built-in mission profile factories.

Kept as an internal subpackage to keep ``core.mission_types`` focused on
the public API (enums, dataclasses, registration helpers). Each module
below owns a family of profiles:

- :mod:`cubesat` — LEO phase graph + 1U..12U size variants
- :mod:`cansat`  — minimal / standard / advanced
- :mod:`other`   — rocket, HAB, drone

Consumers should not import from here directly; go through
:func:`core.mission_types.get_mission_profile`.
"""

from __future__ import annotations

from .cansat import (
    cansat_advanced_profile,
    cansat_minimal_profile,
    cansat_standard_profile,
)
from .cubesat import (
    cubesat_12u_profile,
    cubesat_1_5u_profile,
    cubesat_1u_profile,
    cubesat_2u_profile,
    cubesat_3u_profile,
    cubesat_6u_profile,
    cubesat_leo_profile,
)
from .other import (
    drone_survey_profile,
    hab_standard_profile,
    rocket_competition_profile,
)

BUILTIN_FACTORIES = [
    cubesat_leo_profile,
    cubesat_1u_profile,
    cubesat_1_5u_profile,
    cubesat_2u_profile,
    cubesat_3u_profile,
    cubesat_6u_profile,
    cubesat_12u_profile,
    cansat_minimal_profile,
    cansat_standard_profile,
    cansat_advanced_profile,
    rocket_competition_profile,
    hab_standard_profile,
    drone_survey_profile,
]

__all__ = [
    "BUILTIN_FACTORIES",
    "cansat_advanced_profile",
    "cansat_minimal_profile",
    "cansat_standard_profile",
    "cubesat_12u_profile",
    "cubesat_1_5u_profile",
    "cubesat_1u_profile",
    "cubesat_2u_profile",
    "cubesat_3u_profile",
    "cubesat_6u_profile",
    "cubesat_leo_profile",
    "drone_survey_profile",
    "hab_standard_profile",
    "rocket_competition_profile",
]
