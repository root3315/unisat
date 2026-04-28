"""Regression guard for mission_templates/*.json.

For every JSON file under ``mission_templates/``, parse it and feed the
result through ``build_profile_from_config()``. The resulting
``MissionProfile`` must satisfy a small set of non-trivial invariants —
this catches a class of typos the form-factor validator does not, such as
a renamed phase key or a typo'd initial phase, by checking that the
profile actually round-trips end-to-end.

Closes the looser claim in mission_templates/README.md that every shipped
template is a valid end-to-end profile, complementing
``configurator/tests/test_validators.py::test_every_template_references_a_known_form_factor``
which only checks the ``satellite.form_factor`` field.

See issue #17 for context.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.mission_types import (
    MissionProfile,
    PhaseDefinition,
    PlatformCategory,
    build_profile_from_config,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
TEMPLATES_DIR = REPO_ROOT / "mission_templates"
TEMPLATE_PATHS = sorted(TEMPLATES_DIR.glob("*.json"))


def test_templates_directory_is_populated() -> None:
    """Sanity check: the parametrised test below is meaningless if no
    templates were found (e.g. the directory was renamed). Fail loudly
    so the gap shows up as a real test failure, not as 0 collected tests.
    """
    assert TEMPLATE_PATHS, (
        f"No mission_templates/*.json found at {TEMPLATES_DIR}. "
        "Did the directory move?"
    )


@pytest.mark.parametrize(
    "template_path",
    TEMPLATE_PATHS,
    ids=lambda p: p.name,
)
def test_every_template_builds_into_valid_profile(template_path: Path) -> None:
    """Every shipped mission template must build into a valid
    ``MissionProfile`` via ``build_profile_from_config``.
    """
    config = json.loads(template_path.read_text(encoding="utf-8"))
    profile = build_profile_from_config(config)

    assert isinstance(profile, MissionProfile), (
        f"{template_path.name}: build_profile_from_config returned "
        f"{type(profile).__name__!r}, expected MissionProfile"
    )

    assert profile.mission_type is not None, (
        f"{template_path.name}: mission_type is None"
    )

    assert isinstance(profile.platform, PlatformCategory), (
        f"{template_path.name}: platform is not a PlatformCategory enum value "
        f"(got {profile.platform!r})"
    )

    assert profile.phases, (
        f"{template_path.name}: phases is empty -- a profile needs at least "
        "one phase to be runnable"
    )
    for phase in profile.phases:
        assert isinstance(phase, PhaseDefinition), (
            f"{template_path.name}: phases contains a "
            f"{type(phase).__name__!r}, expected PhaseDefinition"
        )

    phase_names = {p.name for p in profile.phases}
    assert profile.initial_phase in phase_names, (
        f"{template_path.name}: initial_phase {profile.initial_phase!r} is "
        f"not one of the phase names {sorted(phase_names)}"
    )

    assert profile.default_telemetry_hz > 0, (
        f"{template_path.name}: default_telemetry_hz must be positive, got "
        f"{profile.default_telemetry_hz}"
    )
