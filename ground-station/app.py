"""UniSat Ground Station -- Main Streamlit Application.

Entry point for the CubeSat ground station dashboard.  Run with::

    streamlit run app.py

The application uses a multi-page layout.  Each page lives under ``pages/``
and is auto-discovered by Streamlit.
"""

from __future__ import annotations

import json
import pathlib
from datetime import datetime, timezone

import streamlit as st

# ---------------------------------------------------------------------------
# Page configuration (must be the first Streamlit command)
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="UniSat Ground Station",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Dark space theme via custom CSS
# ---------------------------------------------------------------------------

_THEME_CSS = """
<style>
    [data-testid="stAppViewContainer"] {background-color: #0e1117;}
    [data-testid="stSidebar"] {background-color: #161b22;}
    .stMetric label {color: #8b949e !important;}
    .stMetric [data-testid="stMetricValue"] {color: #e6edf3 !important;}
    h1, h2, h3 {color: #e6edf3 !important;}
    .block-container {padding-top: 1.5rem;}
</style>
"""
st.markdown(_THEME_CSS, unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Load mission configuration
# ---------------------------------------------------------------------------

_CONFIG_PATH = pathlib.Path(__file__).resolve().parent.parent / "mission_config.json"


@st.cache_data(ttl=300)
def _load_config() -> dict:
    """Load mission configuration from the repository root."""
    if _CONFIG_PATH.exists():
        return json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
    return {}


config = _load_config()
mission = config.get("mission", {})

# ---------------------------------------------------------------------------
# Sidebar -- mission identity
# ---------------------------------------------------------------------------

with st.sidebar:
    st.image(
        "https://img.icons8.com/fluency/96/satellite-signal.png",
        width=64,
    )
    st.title(mission.get("name", "UniSat-1"))
    st.caption(mission.get("description", "Universal modular CubeSat platform"))
    st.divider()
    st.markdown(f"**Operator:** {mission.get('operator', 'N/A')}")
    st.markdown(f"**Form factor:** {config.get('satellite', {}).get('form_factor', '3U')}")
    orbit = config.get("orbit", {})
    st.markdown(f"**Orbit:** {orbit.get('type', 'SSO')} @ {orbit.get('altitude_km', 550)} km")
    st.markdown(f"**Inclination:** {orbit.get('inclination_deg', 97.6)}°")
    st.divider()
    utc_now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    st.markdown(f"🕐 **UTC:** {utc_now}")

# ---------------------------------------------------------------------------
# Welcome page
# ---------------------------------------------------------------------------

st.title("🛰️ UniSat Ground Station")
st.markdown("### Mission Control Dashboard")
st.markdown("---")

col1, col2, col3 = st.columns(3)
with col1:
    st.info("📡 **Telemetry**\n\nReal-time satellite health and sensor data.")
with col2:
    st.info("🌍 **Orbit Tracker**\n\n3-D globe with ground track and pass predictions.")
with col3:
    st.info("⚡ **Power Monitor**\n\nBattery SOC, solar generation and power budget.")

st.markdown("")

col4, col5, col6 = st.columns(3)
with col4:
    st.info("📷 **Image Viewer**\n\nBrowse captured Earth-observation imagery.")
with col5:
    st.info("🎯 **ADCS Monitor**\n\nAttitude quaternions, angular rates and pointing error.")
with col6:
    st.info("📤 **Command Center**\n\nUplink commands with HMAC authentication.")
