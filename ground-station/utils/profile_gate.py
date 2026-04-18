"""Ground-station page gating — show only views applicable to the profile.

The ground station is a multi-page Streamlit app auto-discovered from
``pages/``. For a CanSat mission, orbit trackers and ADCS monitors are
irrelevant; for a 1U CubeSat without a camera, the imagery page is empty.

This module provides a single helper, :func:`page_applies`, which every
page calls at the top of its module body. If the active mission profile
does not use the page, the helper renders a short notice and stops the
page early.

The decision is purely declarative: each page declares
``{"platforms": [...], "form_factors": [...], "features": [...],
"orbital": true/false}`` and this module matches those requirements
against ``mission_config.json``.
"""

from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass, field
from typing import Iterable

try:
    import streamlit as st  # type: ignore
except ImportError:  # pragma: no cover - Streamlit is optional at import time
    st = None  # type: ignore


@dataclass(frozen=True)
class PageRequirements:
    """Declarative requirements for a ground-station page.

    Attributes:
        platforms: Platform categories where the page applies (empty = any).
        form_factors: Form-factor keys where the page applies (empty = any).
        features: Feature flags that must be true for the page to apply.
        requires_orbit: If True, the mission config must contain an
            ``orbit`` block and the platform must be CubeSat.
    """

    platforms: tuple[str, ...] = ()
    form_factors: tuple[str, ...] = ()
    features: tuple[str, ...] = ()
    requires_orbit: bool = False


@dataclass
class MissionContext:
    """Snapshot of the mission config used for gating decisions."""

    platform: str
    form_factor: str
    features: set[str] = field(default_factory=set)
    has_orbit: bool = False
    config: dict = field(default_factory=dict)


def _config_path() -> pathlib.Path:
    """Resolve the path to ``mission_config.json`` at the repo root."""
    here = pathlib.Path(__file__).resolve()
    return here.parent.parent.parent / "mission_config.json"


def load_mission_context(config_override: dict | None = None) -> MissionContext:
    """Load the mission context from ``mission_config.json``.

    Args:
        config_override: For tests — pass the dict directly.

    Returns:
        A MissionContext summarising platform, form factor, and enabled
        features. If the config is missing, returns a permissive context
        (everything is applicable).
    """
    if config_override is not None:
        config = config_override
    else:
        path = _config_path()
        if not path.exists():
            return MissionContext(platform="", form_factor="",
                                  features=set(), has_orbit=False,
                                  config={})
        config = json.loads(path.read_text(encoding="utf-8"))

    mission = config.get("mission", {})
    satellite = config.get("satellite", {})
    platform = mission.get("platform") or ""
    form_factor = satellite.get("form_factor") or ""

    feature_cfg = config.get("features", {})
    enabled_features = {k for k, v in feature_cfg.items() if v is True}

    # Treat subsystem.enabled = true as the feature being enabled, so
    # older templates that don't carry a "features" block still work.
    for key, cfg in config.get("subsystems", {}).items():
        if isinstance(cfg, dict) and cfg.get("enabled") is True:
            enabled_features.add(key)

    has_orbit = bool(config.get("orbit"))

    return MissionContext(
        platform=platform,
        form_factor=form_factor,
        features=enabled_features,
        has_orbit=has_orbit,
        config=config,
    )


def matches(context: MissionContext, req: PageRequirements) -> bool:
    """Return True if the page's requirements are satisfied by the mission."""
    if req.requires_orbit and not context.has_orbit:
        return False
    if req.platforms and context.platform not in req.platforms:
        # Empty platform string = permissive (no mission config) → allow.
        if context.platform != "":
            return False
    if req.form_factors and context.form_factor not in req.form_factors:
        if context.form_factor != "":
            return False
    if req.features:
        if not set(req.features).issubset(context.features):
            return False
    return True


def page_applies(
    *,
    platforms: Iterable[str] = (),
    form_factors: Iterable[str] = (),
    features: Iterable[str] = (),
    requires_orbit: bool = False,
    page_label: str = "This page",
) -> bool:
    """Return True if the calling page applies to the current mission.

    If the page does not apply and Streamlit is available, render a
    short explanatory notice and call :func:`streamlit.stop`.

    Args:
        platforms: Applicable platform categories.
        form_factors: Applicable form-factor keys.
        features: Required feature flags (all must be enabled).
        requires_orbit: Whether an orbital mission is required.
        page_label: Friendly label shown in the notice.

    Returns:
        True if the page applies; False if Streamlit is not available.
        When Streamlit is available and the page does not apply, the
        function does not return — :func:`streamlit.stop` is invoked.
    """
    req = PageRequirements(
        platforms=tuple(platforms),
        form_factors=tuple(form_factors),
        features=tuple(features),
        requires_orbit=requires_orbit,
    )
    context = load_mission_context()

    if matches(context, req):
        return True

    if st is not None:
        st.warning(
            f"{page_label} is hidden for the current mission "
            f"(platform={context.platform or '?'}, "
            f"form_factor={context.form_factor or '?'}).\n\n"
            f"Required: platforms={list(req.platforms) or 'any'}, "
            f"form_factors={list(req.form_factors) or 'any'}, "
            f"features={list(req.features) or 'none'}"
            + (" — orbital only" if req.requires_orbit else "")
        )
        st.stop()
    return False
