"""UniSat Lab — unified Streamlit playground.

Launch with::

    cd /path/to/unisat
    streamlit run tools/playground.py

One browser tab gives you six interactive surfaces:
    * Form factors — browse the registry (mass / volume / power / bands)
    * Mission profile — pick + validate a mission_config against its envelope
    * CanSat SITL — run the flight simulator with live charts
    * Bill of materials — view any profile's BOM
    * Test runner — run pytest / ruff / mypy and see results
    * Firmware — peek the compile-time profile macro + per-profile build list

The page is meant for local hands-on work. No data leaves the machine.
"""

from __future__ import annotations

import csv
import io
import subprocess
import sys
import time
from pathlib import Path

import streamlit as st

# Ensure the project's Python packages resolve
REPO = Path(__file__).resolve().parent.parent
for sub in ("flight-software", "ground-station", "configurator", "simulation", "tools"):
    path = REPO / sub
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from cansat_sim import average_descent_rate, simulate_cansat_flight  # noqa: E402
from core.feature_flags import resolve_flags                          # noqa: E402
from core.form_factors import (                                      # noqa: E402
    FormFactorClass,
    get_form_factor,
    list_form_factors,
)
from core.mission_types import (                                     # noqa: E402
    get_mission_profile,
    list_mission_types,
)

from validators.mass_validator import validate_mass                  # noqa: E402
from validators.power_validator import validate_power                # noqa: E402
from validators.volume_validator import validate_volume              # noqa: E402


st.set_page_config(
    page_title="UniSat Lab",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

with st.container():
    c1, c2 = st.columns([3, 1])
    with c1:
        st.title("🛰️ UniSat Lab")
        st.caption(
            "Interactive playground for every supported form factor — "
            "registry, validator, SITL, BOM, tests, firmware profile."
        )
    with c2:
        st.metric("Form factors", len(list_form_factors()))
        st.metric("Mission profiles", len(list_mission_types()))


tab_ff, tab_mission, tab_sitl, tab_bom, tab_tests, tab_fw = st.tabs([
    "Form factors",
    "Mission profile",
    "CanSat SITL",
    "Bill of materials",
    "Test runner",
    "Firmware",
])


# ---------------------------------------------------------------------------
# Tab 1 — Form factors registry
# ---------------------------------------------------------------------------

with tab_ff:
    st.subheader("Form-factor registry")
    st.markdown(
        "Authoritative mass / volume / power envelopes + allowed ADCS "
        "tiers and radio bands, sourced from "
        "`flight-software/core/form_factors.py`. "
        "This is the single source of truth every other subsystem "
        "reads from."
    )

    family_filter = st.selectbox(
        "Family",
        options=["(all)"] + [f.value for f in FormFactorClass],
        index=0,
    )

    keys = list_form_factors()
    if family_filter != "(all)":
        keys = [k for k in keys if get_form_factor(k).family.value == family_filter]

    rows = []
    for key in keys:
        ff = get_form_factor(key)
        shape = ff.volume.shape
        if shape == "cylindrical":
            dims = (
                f"Ø{ff.volume.dimensions_mm.get('outer_d', 0):.0f}"
                f" × {ff.volume.dimensions_mm.get('height', 0):.0f}"
            )
        elif shape == "rectangular":
            d = ff.volume.dimensions_mm
            dims = f"{d.get('x', 0):.0f} × {d.get('y', 0):.0f} × {d.get('z', 0):.0f}"
        else:
            dims = "—"
        rows.append({
            "Key": key,
            "Display": ff.display_name,
            "Max mass": f"{ff.mass.max_kg * 1000:.0f} g" if ff.mass.max_kg < 2 else f"{ff.mass.max_kg:.1f} kg",
            "Volume": f"{ff.volume.volume_cm3:.0f} cm³",
            "Dimensions": dims,
            "Solar": "☀" if ff.power.solar_capable else "—",
            "Deployables": ff.max_deployables,
            "Propulsion": "🚀" if ff.supports_propulsion else "—",
        })

    st.dataframe(rows, use_container_width=True, hide_index=True)

    detail_key = st.selectbox("Inspect a form factor", options=keys, index=0)
    if detail_key:
        ff = get_form_factor(detail_key)
        c1, c2, c3 = st.columns(3)
        c1.metric("Max mass", f"{ff.mass.max_kg * 1000:.0f} g" if ff.mass.max_kg < 2 else f"{ff.mass.max_kg:.2f} kg")
        c2.metric("Peak power", f"{ff.power.peak_w:.1f} W")
        c3.metric("Battery (typ)", f"{ff.power.battery_capacity_wh_typical:.1f} Wh")

        st.markdown(f"**ADCS tiers:** {', '.join(ff.allowed_adcs_tiers)}")
        st.markdown(f"**Radio bands:** {', '.join(ff.allowed_comm_bands)}")
        st.info(ff.regulation_notes or "No regulation notes on file.")


# ---------------------------------------------------------------------------
# Tab 2 — Mission profile + validator
# ---------------------------------------------------------------------------

with tab_mission:
    st.subheader("Mission profile validator")
    st.markdown(
        "Pick a profile, tune subsystems, see if the resulting "
        "configuration fits the form-factor envelope (mass, volume, "
        "power) and which feature flags the resolver enables."
    )

    mt = st.selectbox(
        "Mission type",
        options=list_mission_types(),
        index=list_mission_types().index("cansat_standard")
        if "cansat_standard" in list_mission_types() else 0,
    )

    profile = get_mission_profile(mt)
    # Mission types like "cubesat_leo" don't match any form-factor key.
    # Map common aliases to the registered form factor they represent.
    _MT_TO_FF = {
        "cubesat_leo": "cubesat_3u",
        "cubesat_sso": "cubesat_3u",
        "cubesat_tech_demo": "cubesat_3u",
        "rocket_competition": "rocket_payload",
        "rocket_sounding": "rocket_payload",
        "hab_standard": "hab_payload",
        "hab_long_duration": "hab_payload",
        "drone_survey": "drone_small",
        "drone_inspection": "drone_small",
        "rover_exploration": "rover_small",
    }
    ff_key = profile.competition.get("form_factor") or _MT_TO_FF.get(mt, mt)

    st.caption(f"Platform: **{profile.platform.value}** · "
               f"initial phase: **{profile.initial_phase}** · "
               f"telemetry default: **{profile.default_telemetry_hz} Hz**")

    st.markdown("#### Subsystems")
    cols = st.columns(5)
    subs = {}
    all_subs = ["eps", "comm_uhf", "comm_sband", "comm_lora", "adcs",
                "gnss", "imu", "barometer", "camera", "payload",
                "descent_controller"]
    for i, name in enumerate(all_subs):
        with cols[i % 5]:
            default = name in profile.core_modules or name == "eps"
            subs[name] = st.checkbox(name, value=default, key=f"sub-{mt}-{name}")

    mass = validate_mass(ff_key, subs)
    vol = validate_volume(ff_key, subs)
    pwr = validate_power(ff_key, panel_efficiency=0.295, enabled_subsystems=subs)

    c1, c2, c3 = st.columns(3)
    with c1:
        delta = mass.limit_kg - mass.total_kg
        st.metric(
            "Mass",
            f"{mass.total_kg * 1000:.0f} g / {mass.limit_kg * 1000:.0f} g",
            delta=f"{delta * 1000:+.0f} g headroom",
            delta_color="normal" if mass.valid else "inverse",
        )
    with c2:
        st.metric(
            "Volume",
            f"{vol.total_cm3:.0f} / {vol.available_cm3:.0f} cm³",
            delta=f"{100 - vol.utilization_pct:.1f}% free",
        )
    with c3:
        st.metric(
            "Power (nominal)",
            f"{pwr.consumption_nominal_w:.1f} W",
            delta=f"gen {pwr.generation_w:.1f} W",
        )

    if not mass.valid:
        st.error(f"⚠️ Mass **{mass.total_kg * 1000:.0f} g** exceeds "
                 f"the {mass.limit_kg * 1000:.0f} g envelope for "
                 f"{ff_key}.")
    else:
        st.success(f"✅ Configuration fits the {ff_key} envelope "
                   f"with {delta * 1000:.0f} g to spare.")

    with st.expander("Feature flags resolver output"):
        try:
            resolved = resolve_flags(
                profile=profile,
                form_factor=get_form_factor(ff_key),
                config={},
            )
        except KeyError:
            st.warning(f"No form-factor envelope registered for '{ff_key}'.")
        else:
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**🟢 Enabled**")
                for flag in sorted(resolved.enabled):
                    reason = resolved.reasons.get(flag, "")
                    st.markdown(f"- `{flag}` — {reason}")
            with c2:
                st.markdown("**⚪ Disabled**")
                for flag in sorted(resolved.disabled):
                    reason = resolved.reasons.get(flag, "")
                    st.markdown(f"- `{flag}` — {reason}")
            if resolved.warnings:
                st.warning("\n".join(resolved.warnings))


# ---------------------------------------------------------------------------
# Tab 3 — CanSat SITL
# ---------------------------------------------------------------------------

with tab_sitl:
    st.subheader("CanSat SITL — simulated flight")
    st.markdown(
        "Runs the same dynamics model used by "
        "`flight-software/run_cansat.py`. Tune the launch altitude and "
        "target descent rate; watch the trajectory + phase transitions."
    )

    c1, c2, c3 = st.columns(3)
    max_alt = c1.slider("Max altitude (m)", 100, 1500, 500, step=50)
    descent_rate = c2.slider("Target descent rate (m/s)", 3.0, 15.0, 8.0, step=0.5)
    run_btn = c3.button("🚀 Launch", use_container_width=True, type="primary")

    st.caption(
        "Competition band **6 – 11 m/s**. Rates outside this window "
        "will be flagged after the run."
    )

    if run_btn or "last_flight" not in st.session_state:
        samples = simulate_cansat_flight(max_alt, descent_rate)
        st.session_state["last_flight"] = {
            "samples": samples,
            "max_alt": max_alt,
            "descent_rate": descent_rate,
        }

    flight = st.session_state["last_flight"]
    samples = flight["samples"]

    # Chart — altitude over time
    import pandas as pd  # lazy import — only needed in this tab
    df = pd.DataFrame(samples)
    st.line_chart(df.set_index("t")[["altitude_m", "velocity_ms"]])

    # Phase summary
    phases = {}
    for s in samples:
        phases.setdefault(s["phase"], []).append(s["t"])
    st.markdown("#### Phase summary")
    for phase, ts in phases.items():
        st.markdown(f"- **{phase}** — {ts[0]:.1f}s to {ts[-1]:.1f}s "
                    f"({len(ts)} samples)")

    # Competition verdict
    avg_rate = average_descent_rate(samples)
    if avg_rate > 0:
        ok = 6.0 <= avg_rate <= 11.0
        if ok:
            st.success(f"✅ Descent rate **{avg_rate:.1f} m/s** — inside "
                       f"competition window [6, 11] m/s.")
        else:
            st.warning(f"⚠️ Descent rate **{avg_rate:.1f} m/s** — outside "
                       f"competition window [6, 11] m/s.")

    with st.expander("Raw samples (first 30)"):
        st.dataframe(samples[:30], use_container_width=True, hide_index=True)


# ---------------------------------------------------------------------------
# Tab 4 — Bill of materials
# ---------------------------------------------------------------------------

BOM_DIR = REPO / "hardware" / "bom" / "by_form_factor"

with tab_bom:
    st.subheader("Bill of materials")

    bom_files = sorted(BOM_DIR.glob("*.csv"))
    selection = st.selectbox(
        "BOM",
        options=[p.name for p in bom_files],
        index=1 if len(bom_files) > 1 else 0,
    )

    bom_path = BOM_DIR / selection
    with bom_path.open(encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)

    headers = rows[0]
    body = [r for r in rows[1:] if any(cell.strip() for cell in r) and
            not (len(r) > 0 and r[0] == "" and "TOTAL" not in " ".join(r))]

    # Split off the TOTAL row
    data_rows = [r for r in body if "TOTAL" not in " ".join(r)]
    total_row = next((r for r in body if "TOTAL" in " ".join(r)), None)

    def parse_mass(r: list[str]) -> float:
        try:
            return float(r[5]) if len(r) > 5 and r[5] else 0.0
        except ValueError:
            return 0.0

    total_mass = sum(parse_mass(r) for r in data_rows)

    c1, c2, c3 = st.columns(3)
    c1.metric("Line items", len(data_rows))
    c2.metric("Kit mass", f"{total_mass:.0f} g")
    if total_row and len(total_row) > 7:
        c3.caption(f"_{total_row[7]}_" if total_row[7] else "")

    st.dataframe(
        [{h: c for h, c in zip(headers, r)} for r in data_rows],
        use_container_width=True, hide_index=True,
    )

    # Download button
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerows(rows)
    st.download_button(
        "📥 Download raw CSV",
        data=buf.getvalue().encode("utf-8"),
        file_name=selection,
        mime="text/csv",
    )


# ---------------------------------------------------------------------------
# Tab 5 — Test runner
# ---------------------------------------------------------------------------

with tab_tests:
    st.subheader("Test runner")
    st.markdown(
        "Run the repo's quality gates from the browser. Each button "
        "shells out to `pytest` / `ruff` / `mypy` and streams the "
        "result back."
    )

    SUITES = {
        "flight-software (299)": [sys.executable, "-m", "pytest",
                                  "flight-software/tests", "-q"],
        "ground-station (94)":   [sys.executable, "-m", "pytest",
                                  "ground-station/tests", "-q",
                                  "--ignore=ground-station/tests/test_pages_smoke.py"],
        "configurator (21)":     [sys.executable, "-m", "pytest",
                                  "configurator/tests", "-q"],
        "simulation (57)":       [sys.executable, "-m", "pytest",
                                  "simulation/tests", "-q"],
        "ruff (all)":            [sys.executable, "-m", "ruff", "check",
                                  "flight-software/core",
                                  "flight-software/modules",
                                  "ground-station", "simulation",
                                  "configurator"],
        "mypy --strict":         [sys.executable, "-m", "mypy",
                                  "--config-file",
                                  "flight-software/pyproject.toml",
                                  "flight-software/core",
                                  "flight-software/modules"],
    }

    choice = st.radio("Suite", list(SUITES.keys()), horizontal=True)
    run = st.button("▶ Run", type="primary")

    if run:
        cmd = SUITES[choice]
        with st.spinner(f"Running `{ ' '.join(cmd) }` …"):
            t0 = time.time()
            proc = subprocess.run(cmd, cwd=str(REPO),
                                  capture_output=True, text=True,
                                  timeout=300)
            elapsed = time.time() - t0
        code = proc.returncode
        if code == 0:
            st.success(f"✅ `{choice}` — passed in {elapsed:.1f}s")
        else:
            st.error(f"❌ `{choice}` — exit {code} after {elapsed:.1f}s")
        st.code((proc.stdout or "") + (proc.stderr or ""), language="text")


# ---------------------------------------------------------------------------
# Tab 6 — Firmware / compile-time profiles
# ---------------------------------------------------------------------------

FW_PROFILES = [
    ("cansat_minimal",  "PROFILE_CANSAT_MINIMAL",  "make target-cansat_minimal"),
    ("cansat_standard", "PROFILE_CANSAT_STANDARD", "make target-cansat_standard"),
    ("cansat_advanced", "PROFILE_CANSAT_ADVANCED", "make target-cansat_advanced"),
    ("cubesat_1u",      "PROFILE_CUBESAT_1U",      "make target-cubesat_1u"),
    ("cubesat_1_5u",    "PROFILE_CUBESAT_1_5U",    "make target-cubesat_1_5u"),
    ("cubesat_2u",      "PROFILE_CUBESAT_2U",      "make target-cubesat_2u"),
    ("cubesat_3u",      "PROFILE_CUBESAT_3U",      "make target-cubesat_3u (default)"),
    ("cubesat_6u",      "PROFILE_CUBESAT_6U",      "make target-cubesat_6u"),
    ("cubesat_12u",     "PROFILE_CUBESAT_12U",     "make target-cubesat_12u"),
]

with tab_fw:
    st.subheader("Firmware — compile-time profiles")
    st.markdown(
        "One firmware source tree compiles into **9 separate binaries** "
        "through `-DMISSION_PROFILE_<NAME>=1`. Each row below is one "
        "binary target; the macro is mirrored in both "
        "`firmware/stm32/Core/Inc/mission_profile.h` (C) and "
        "`flight-software/core/feature_flags.py` (Python resolver)."
    )

    rows = [{
        "Profile": key,
        "Compile macro": macro,
        "Make target": cmd,
    } for key, macro, cmd in FW_PROFILES]
    st.dataframe(rows, use_container_width=True, hide_index=True)

    st.info(
        "Cross-compiling requires `arm-none-eabi-gcc` on PATH. Without "
        "it the same tree still builds as a host library + Unity tests "
        "(28 ctest targets).")

    st.markdown("#### Footprint baseline (cubesat_3u, STM32F446RE)")
    c1, c2, c3 = st.columns(3)
    c1.metric("Flash", "31.6 KB / 512 KB", delta="6 %")
    c2.metric("RAM", "36.3 KB / 128 KB", delta="28 %")
    c3.metric("ctest targets", "28", delta="100 % green")


# ---------------------------------------------------------------------------
# Sidebar — quick info
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown("### UniSat Lab")
    st.caption(f"Repo: `{REPO.name}`")
    st.caption("Version: v1.4.3")
    st.markdown("---")
    st.markdown("#### Useful links")
    st.markdown("- [`docs/README.md`](../docs/README.md)")
    st.markdown("- [`docs/ops/README.md`](../docs/ops/README.md)")
    st.markdown("- [CHANGELOG](../CHANGELOG.md)")
    st.markdown("---")
    st.caption("Runs fully locally — no data leaves your machine.")
