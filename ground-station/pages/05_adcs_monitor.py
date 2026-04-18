"""ADCS Monitor — Attitude visualization and pointing status."""

import numpy as np
import plotly.graph_objects as go
import streamlit as st

from utils.profile_gate import page_applies

st.set_page_config(page_title="ADCS Monitor", layout="wide")

page_applies(
    platforms=("cubesat", "drone"),
    features=("adcs",),
    page_label="ADCS Monitor",
)

st.title("🧭 ADCS Monitor")

# Current attitude (demo)
quat = [0.924, 0.123, -0.362, 0.045]
euler_deg = [14.2, -42.1, 5.3]  # roll, pitch, yaw
angular_rate = [0.15, -0.08, 0.03]  # deg/s

col1, col2, col3 = st.columns(3)
col1.metric("Mode", "SUN POINTING")
col2.metric("Pointing Error", "1.8°")
col3.metric("Angular Rate", f"{np.linalg.norm(angular_rate):.3f} °/s")

st.markdown("---")

# Quaternion & Euler
col1, col2 = st.columns(2)
with col1:
    st.markdown("### Quaternion")
    st.markdown(f"**w:** {quat[0]:.4f}")
    st.markdown(f"**x:** {quat[1]:.4f}")
    st.markdown(f"**y:** {quat[2]:.4f}")
    st.markdown(f"**z:** {quat[3]:.4f}")

with col2:
    st.markdown("### Euler Angles")
    st.markdown(f"**Roll:** {euler_deg[0]:.2f}°")
    st.markdown(f"**Pitch:** {euler_deg[1]:.2f}°")
    st.markdown(f"**Yaw:** {euler_deg[2]:.2f}°")

st.markdown("---")

# Pointing error history
n = 200
t = np.arange(n)
error = 10 * np.exp(-t / 50) + np.random.normal(0, 0.3, n)
error = np.maximum(error, 0)

fig = go.Figure()
fig.add_trace(go.Scatter(y=error, name="Pointing Error", line=dict(color="#fd79a8")))
fig.add_hline(y=1.0, line_dash="dash", line_color="green", annotation_text="Target: 1°")
fig.update_layout(title="Pointing Error History (°)", template="plotly_dark", height=300)
st.plotly_chart(fig, use_container_width=True)

# Reaction wheel speeds
st.markdown("### Reaction Wheel Status")
wheel_cols = st.columns(3)
wheel_speeds = [1250, -890, 340]
for i, (col, speed) in enumerate(zip(wheel_cols, wheel_speeds)):
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=speed,
        title={"text": f"Wheel {i+1} (RPM)"},
        gauge={
            "axis": {"range": [-6000, 6000]},
            "bar": {"color": "#4ecdc4"},
            "bgcolor": "#1a1a2e",
            "steps": [
                {"range": [-6000, -5000], "color": "#ff6b6b"},
                {"range": [5000, 6000], "color": "#ff6b6b"},
            ],
        }
    ))
    fig.update_layout(template="plotly_dark", height=250, margin=dict(t=50, b=10))
    col.plotly_chart(fig, use_container_width=True)
