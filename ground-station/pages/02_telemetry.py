"""Telemetry page -- real-time sensor charts.

Generates demo sinusoidal data with noise and renders interactive Plotly
time-series for temperature, pressure, voltage, radiation and magnetic field.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import numpy as np
import plotly.graph_objects as go
import streamlit as st

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(page_title="Telemetry | UniSat GS", page_icon="📈", layout="wide")

# ---------------------------------------------------------------------------
# Demo data generation
# ---------------------------------------------------------------------------

N_POINTS = 300  # ~5 minutes at 1 Hz


def _time_axis(n: int = N_POINTS) -> list[datetime]:
    """Create a list of UTC timestamps ending at *now*.

    Args:
        n: Number of samples.

    Returns:
        List of ``datetime`` objects spaced 1 second apart.
    """
    now = datetime.now(timezone.utc)
    return [now - timedelta(seconds=n - i) for i in range(n)]


def _sinusoidal(
    n: int,
    base: float,
    amplitude: float,
    period: float = 60.0,
    noise: float = 0.0,
) -> np.ndarray:
    """Generate a sinusoidal signal with additive Gaussian noise.

    Args:
        n: Number of samples.
        base: DC offset.
        amplitude: Peak deviation from *base*.
        period: Oscillation period in samples.
        noise: Standard deviation of Gaussian noise.

    Returns:
        1-D numpy array of length *n*.
    """
    t = np.arange(n, dtype=np.float64)
    signal = base + amplitude * np.sin(2 * np.pi * t / period)
    if noise > 0:
        signal += np.random.default_rng().normal(0, noise, n)
    return signal


def _plotly_dark(fig: go.Figure) -> go.Figure:
    """Apply a consistent dark layout to a Plotly figure.

    Args:
        fig: The Plotly figure to style.

    Returns:
        The same figure, mutated in-place.
    """
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#0e1117",
        plot_bgcolor="#0e1117",
        margin=dict(l=40, r=20, t=40, b=30),
        height=280,
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    return fig


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

st.title("📈 Telemetry Monitor")
st.caption("Auto-refreshes every 5 seconds  --  demo sinusoidal data")

timestamps = _time_axis()

# ---------------------------------------------------------------------------
# Row 1: Temperature & Pressure
# ---------------------------------------------------------------------------

col1, col2 = st.columns(2)

with col1:
    st.subheader("Temperature")
    obc_temp = _sinusoidal(N_POINTS, base=25.0, amplitude=6.0, period=90, noise=0.5)
    batt_temp = _sinusoidal(N_POINTS, base=22.0, amplitude=4.0, period=90, noise=0.4)
    panel_temp = _sinusoidal(N_POINTS, base=40.0, amplitude=30.0, period=90, noise=1.0)

    fig_temp = go.Figure()
    fig_temp.add_trace(go.Scatter(x=timestamps, y=obc_temp, name="OBC", line=dict(color="#58a6ff")))
    fig_temp.add_trace(go.Scatter(x=timestamps, y=batt_temp, name="Battery", line=dict(color="#3fb950")))
    fig_temp.add_trace(go.Scatter(x=timestamps, y=panel_temp, name="Solar Panel", line=dict(color="#f0883e")))
    fig_temp.update_yaxes(title_text="°C")
    st.plotly_chart(_plotly_dark(fig_temp), use_container_width=True)

with col2:
    st.subheader("Pressure (internal)")
    pressure = _sinusoidal(N_POINTS, base=101.3, amplitude=0.4, period=120, noise=0.15)

    fig_pres = go.Figure()
    fig_pres.add_trace(go.Scatter(x=timestamps, y=pressure, name="Pressure", line=dict(color="#d2a8ff")))
    fig_pres.update_yaxes(title_text="kPa")
    st.plotly_chart(_plotly_dark(fig_pres), use_container_width=True)

# ---------------------------------------------------------------------------
# Row 2: Voltage & Radiation
# ---------------------------------------------------------------------------

col3, col4 = st.columns(2)

with col3:
    st.subheader("Bus Voltage / Battery Voltage")
    bus_v = _sinusoidal(N_POINTS, base=5.0, amplitude=0.15, period=70, noise=0.03)
    batt_v = _sinusoidal(N_POINTS, base=7.4, amplitude=0.3, period=90, noise=0.05)

    fig_v = go.Figure()
    fig_v.add_trace(go.Scatter(x=timestamps, y=bus_v, name="Bus 5V", line=dict(color="#79c0ff")))
    fig_v.add_trace(go.Scatter(x=timestamps, y=batt_v, name="Battery", line=dict(color="#ffa657")))
    fig_v.update_yaxes(title_text="V")
    st.plotly_chart(_plotly_dark(fig_v), use_container_width=True)

with col4:
    st.subheader("Radiation Dose Rate")
    radiation = _sinusoidal(N_POINTS, base=0.8, amplitude=0.5, period=150, noise=0.12)
    radiation = np.clip(radiation, 0.01, None)

    fig_rad = go.Figure()
    fig_rad.add_trace(go.Scatter(x=timestamps, y=radiation, name="SBM-20", fill="tozeroy", line=dict(color="#f85149")))
    fig_rad.update_yaxes(title_text="mSv/h")
    st.plotly_chart(_plotly_dark(fig_rad), use_container_width=True)

# ---------------------------------------------------------------------------
# Row 3: Magnetic field
# ---------------------------------------------------------------------------

st.subheader("Magnetic Field (LIS3MDL)")

mag_x = _sinusoidal(N_POINTS, base=0.0, amplitude=30.0, period=100, noise=2.0)
mag_y = _sinusoidal(N_POINTS, base=5.0, amplitude=25.0, period=110, noise=2.0)
mag_z = _sinusoidal(N_POINTS, base=-10.0, amplitude=35.0, period=95, noise=2.0)

fig_mag = go.Figure()
fig_mag.add_trace(go.Scatter(x=timestamps, y=mag_x, name="Bx", line=dict(color="#ff7b72")))
fig_mag.add_trace(go.Scatter(x=timestamps, y=mag_y, name="By", line=dict(color="#7ee787")))
fig_mag.add_trace(go.Scatter(x=timestamps, y=mag_z, name="Bz", line=dict(color="#79c0ff")))
fig_mag.update_yaxes(title_text="uT")
st.plotly_chart(_plotly_dark(fig_mag), use_container_width=True)

# ---------------------------------------------------------------------------
# Raw packet info
# ---------------------------------------------------------------------------

st.markdown("---")
st.caption(
    f"Showing {N_POINTS} samples  |  "
    f"Last update: {datetime.now(timezone.utc).strftime('%H:%M:%S UTC')}  |  "
    "Source: demo data generator"
)
