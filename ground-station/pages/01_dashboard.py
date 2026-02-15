"""Dashboard page -- mission overview with subsystem health indicators.

Displays mission uptime, satellite state, subsystem health cards and key
metrics (battery SOC, temperature, radiation dose).
"""

from __future__ import annotations

import random
from datetime import datetime, timezone

import streamlit as st

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(page_title="Dashboard | UniSat GS", page_icon="📊", layout="wide")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

LAUNCH_DATE = datetime(2026, 1, 1, tzinfo=timezone.utc)

SUBSYSTEMS: list[dict[str, str]] = [
    {"name": "OBC", "icon": "🖥️", "desc": "On-Board Computer"},
    {"name": "EPS", "icon": "🔋", "desc": "Electrical Power System"},
    {"name": "COMM", "icon": "📡", "desc": "Communications"},
    {"name": "ADCS", "icon": "🎯", "desc": "Attitude Determination & Control"},
    {"name": "Camera", "icon": "📷", "desc": "Earth Observation Payload"},
    {"name": "GNSS", "icon": "🌐", "desc": "Navigation Receiver"},
    {"name": "Thermal", "icon": "🌡️", "desc": "Thermal Control"},
    {"name": "Payload", "icon": "☢️", "desc": "Radiation Monitor"},
]


def _health_color() -> str:
    """Return a random health status weighted toward nominal.

    Returns:
        A CSS colour string: green, orange or red.
    """
    roll = random.random()
    if roll < 0.78:
        return "green"
    if roll < 0.94:
        return "orange"
    return "red"


def _health_label(color: str) -> str:
    """Map colour to a human-readable status label.

    Args:
        color: One of ``'green'``, ``'orange'`` or ``'red'``.

    Returns:
        Status string.
    """
    return {"green": "NOMINAL", "orange": "WARNING", "red": "CRITICAL"}.get(color, "UNKNOWN")


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

st.title("📊 Mission Dashboard")

now_utc = datetime.now(timezone.utc)
uptime = now_utc - LAUNCH_DATE
days = uptime.days
hours, remainder = divmod(uptime.seconds, 3600)
minutes, _ = divmod(remainder, 60)

header_cols = st.columns(4)
header_cols[0].metric("Mission Uptime", f"{days}d {hours}h {minutes}m")
header_cols[1].metric("Satellite State", "NOMINAL ✅")
header_cols[2].metric("Last Contact", f"{random.randint(1, 12)} min ago")
header_cols[3].metric("Orbit #", f"{days * 15 + random.randint(0, 14)}")

st.markdown("---")

# ---------------------------------------------------------------------------
# Subsystem health cards
# ---------------------------------------------------------------------------

st.subheader("Subsystem Health")

# Fix the random seed per session so cards don't flicker on rerun
if "health_seed" not in st.session_state:
    st.session_state["health_seed"] = random.randint(0, 100_000)
random.seed(st.session_state["health_seed"])

rows = [SUBSYSTEMS[:4], SUBSYSTEMS[4:]]
for row in rows:
    cols = st.columns(len(row))
    for col, sub in zip(cols, row):
        color = _health_color()
        label = _health_label(color)
        with col:
            st.markdown(
                f"""
                <div style="
                    border: 2px solid {color};
                    border-radius: 12px;
                    padding: 16px;
                    text-align: center;
                    background: #161b22;
                ">
                    <div style="font-size:2rem;">{sub['icon']}</div>
                    <div style="font-weight:700; color:#e6edf3; margin-top:4px;">{sub['name']}</div>
                    <div style="font-size:0.8rem; color:#8b949e;">{sub['desc']}</div>
                    <div style="
                        margin-top:8px;
                        font-weight:700;
                        color:{color};
                    ">{label}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

# Restore true randomness for metrics below
random.seed()

st.markdown("---")

# ---------------------------------------------------------------------------
# Key metrics
# ---------------------------------------------------------------------------

st.subheader("Key Metrics")

m1, m2, m3, m4, m5 = st.columns(5)

battery_soc = round(random.uniform(62.0, 98.0), 1)
m1.metric("Battery SOC", f"{battery_soc}%", delta=f"{random.uniform(-2, 2):.1f}%")

obc_temp = round(random.uniform(18.0, 35.0), 1)
m2.metric("OBC Temp", f"{obc_temp} °C", delta=f"{random.uniform(-1, 1):.1f} °C")

radiation = round(random.uniform(0.1, 2.5), 2)
m3.metric("Radiation", f"{radiation} mSv/h")

signal = round(random.uniform(-110, -85), 1)
m4.metric("Signal (RSSI)", f"{signal} dBm")

data_stored = round(random.uniform(1.2, 28.0), 1)
m5.metric("Stored Data", f"{data_stored} GB")

# ---------------------------------------------------------------------------
# Recent events log
# ---------------------------------------------------------------------------

st.markdown("---")
st.subheader("Recent Events")

events = [
    ("2026-04-15 09:12:33 UTC", "INFO", "Telemetry frame received (seq 48201)"),
    ("2026-04-15 09:10:05 UTC", "INFO", "Pass AOS -- elevation 24.7 deg"),
    ("2026-04-15 09:05:18 UTC", "WARN", "Battery voltage dropped below 7.2 V"),
    ("2026-04-15 08:55:42 UTC", "INFO", "Image capture completed (ID IMG-0437)"),
    ("2026-04-15 08:50:11 UTC", "INFO", "ADCS mode transition: sun_pointing -> nadir_pointing"),
    ("2026-04-15 08:44:09 UTC", "INFO", "Orbit determination update -- semi-major axis 6928.1 km"),
]

for ts, level, msg in events:
    color = {"INFO": "#58a6ff", "WARN": "#d29922", "ERROR": "#f85149"}.get(level, "#8b949e")
    st.markdown(
        f'<span style="color:#8b949e">{ts}</span> '
        f'<span style="color:{color}; font-weight:700">[{level}]</span> {msg}',
        unsafe_allow_html=True,
    )
