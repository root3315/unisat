"""Power Monitor — Energy generation and consumption tracking."""

import numpy as np
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Power Monitor", layout="wide")
st.title("⚡ Power Monitor")

# Battery SOC gauge
col1, col2 = st.columns([1, 2])

with col1:
    soc = 78.5
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=soc,
        delta={"reference": 80},
        title={"text": "Battery SOC (%)"},
        gauge={
            "axis": {"range": [0, 100]},
            "bar": {"color": "#2ecc71"},
            "bgcolor": "#1a1a2e",
            "steps": [
                {"range": [0, 20], "color": "#e74c3c"},
                {"range": [20, 50], "color": "#f39c12"},
                {"range": [50, 100], "color": "#1a1a2e"},
            ],
            "threshold": {
                "line": {"color": "red", "width": 2},
                "thickness": 0.75,
                "value": 20,
            },
        },
    ))
    fig.update_layout(template="plotly_dark", height=300, margin=dict(t=50, b=10))
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.markdown("### Battery Status")
    c1, c2, c3 = st.columns(3)
    c1.metric("Voltage", "14.2 V")
    c2.metric("Current", "-0.35 A", "Discharging")
    c3.metric("Temperature", "22.1 °C")
    st.markdown("**State:** Nominal | **Cycles:** 847 | **Energy:** 23.6 Wh")

st.markdown("---")

# Solar vs consumption over orbit
n = 200
t = np.linspace(0, 2 * np.pi * 1.5, n)
solar = np.maximum(0, 5.5 * np.sin(t) + np.random.normal(0, 0.2, n))
consumption = 3.0 + 0.5 * np.random.randn(n)

fig = go.Figure()
fig.add_trace(go.Scatter(y=solar, name="Solar Generation", fill="tozeroy",
                          line=dict(color="#f9ca24")))
fig.add_trace(go.Scatter(y=consumption, name="Consumption",
                          line=dict(color="#ff6b6b", dash="dash")))
fig.update_layout(title="Power Budget Over Orbit (W)", template="plotly_dark", height=300,
                  yaxis_title="Power (W)")
st.plotly_chart(fig, use_container_width=True)

# Per-subsystem breakdown
st.markdown("### Subsystem Power Breakdown")
subsystems = ["OBC", "COMM_UHF", "ADCS", "GNSS", "Camera", "Payload", "Heater"]
power_w = [0.5, 1.0, 0.8, 0.3, 0.0, 0.5, 0.0]
colors = ["#4ecdc4", "#ff6b6b", "#74b9ff", "#a29bfe", "#6c5ce7", "#fd79a8", "#ffeaa7"]

fig = go.Figure(go.Bar(x=subsystems, y=power_w, marker_color=colors))
fig.update_layout(title="Current Consumption by Subsystem (W)",
                  template="plotly_dark", height=300)
st.plotly_chart(fig, use_container_width=True)
