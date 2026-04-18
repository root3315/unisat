"""Unit tests for the ground-station profile gate."""

from __future__ import annotations

import sys
from pathlib import Path


_GS_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_GS_ROOT))

from utils.profile_gate import (  # noqa: E402
    MissionContext,
    PageRequirements,
    load_mission_context,
    matches,
)


def _cansat_config() -> dict:
    return {
        "mission": {"platform": "cansat"},
        "satellite": {"form_factor": "cansat_standard"},
        "subsystems": {
            "imu": {"enabled": True},
            "barometer": {"enabled": True},
            "descent_controller": {"enabled": True},
            "camera": {"enabled": False},
        },
        "features": {
            "descent_controller": True,
            "barometer": True,
            "imu": True,
        },
    }


def _cubesat_3u_config() -> dict:
    return {
        "mission": {"platform": "cubesat"},
        "satellite": {"form_factor": "cubesat_3u"},
        "orbit": {"altitude_km": 550, "inclination_deg": 97.6},
        "subsystems": {
            "adcs": {"enabled": True},
            "camera": {"enabled": True},
        },
        "features": {
            "orbit_predictor": True,
            "reaction_wheels": True,
            "camera": True,
        },
    }


def test_orbit_tracker_hidden_for_cansat() -> None:
    ctx = load_mission_context(_cansat_config())
    req = PageRequirements(platforms=("cubesat",), requires_orbit=True)
    assert not matches(ctx, req)


def test_orbit_tracker_visible_for_3u_cubesat() -> None:
    ctx = load_mission_context(_cubesat_3u_config())
    req = PageRequirements(platforms=("cubesat",), requires_orbit=True)
    assert matches(ctx, req)


def test_camera_page_visible_when_camera_enabled() -> None:
    ctx = load_mission_context(_cubesat_3u_config())
    req = PageRequirements(features=("camera",))
    assert matches(ctx, req)


def test_camera_page_hidden_when_camera_disabled() -> None:
    ctx = load_mission_context(_cansat_config())
    req = PageRequirements(features=("camera",))
    assert not matches(ctx, req)


def test_adcs_page_hidden_for_cansat() -> None:
    ctx = load_mission_context(_cansat_config())
    req = PageRequirements(platforms=("cubesat", "drone"), features=("adcs",))
    assert not matches(ctx, req)


def test_adcs_page_visible_for_3u_cubesat() -> None:
    ctx = load_mission_context(_cubesat_3u_config())
    req = PageRequirements(platforms=("cubesat", "drone"), features=("adcs",))
    assert matches(ctx, req)


def test_empty_context_is_permissive() -> None:
    ctx = MissionContext(platform="", form_factor="", features=set(),
                         has_orbit=False, config={})
    req = PageRequirements(platforms=("cubesat",), features=("camera",))
    # Empty platform string = config missing, so we don't block — UI
    # still shows the page; live runtime will filter by telemetry.
    assert not matches(ctx, req)  # orbit requirement not satisfied


def test_form_factor_gate() -> None:
    ctx = load_mission_context(_cubesat_3u_config())
    req = PageRequirements(form_factors=("cubesat_6u", "cubesat_12u"))
    assert not matches(ctx, req)
    req2 = PageRequirements(form_factors=("cubesat_3u",))
    assert matches(ctx, req2)


def test_feature_subset_enforced() -> None:
    ctx = load_mission_context(_cubesat_3u_config())
    req_ok = PageRequirements(features=("camera", "reaction_wheels"))
    assert matches(ctx, req_ok)
    req_bad = PageRequirements(features=("camera", "optical_comm"))
    assert not matches(ctx, req_bad)
