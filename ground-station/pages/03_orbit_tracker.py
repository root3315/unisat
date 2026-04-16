"""Orbit Tracker — 3D visualization of satellite position."""

import numpy as np
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Orbit Tracker", layout="wide")
st.title("🌍 Orbit Tracker")

# Generate ISS-like ground track (SSO ~97.6° inclination, 550 km)
n_points = 100
t = np.linspace(0, 2 * np.pi * 1.5, n_points)  # 1.5 orbits
inclination = np.radians(97.6)
omega_earth = 2 * np.pi / 86400  # Earth rotation rate

lats = np.degrees(np.arcsin(np.sin(inclination) * np.sin(t)))
lons = np.degrees(np.arctan2(
    np.cos(inclination) * np.sin(t),
    np.cos(t)
)) - np.degrees(omega_earth * np.linspace(0, 5560 * 1.5, n_points))
lons = ((lons + 180) % 360) - 180

# Current position (last point)
sat_lat = lats[-1]
sat_lon = lons[-1]

# Ground station
gs_lat, gs_lon = 41.2995, 69.2401

fig = go.Figure()

# Ground track
fig.add_trace(go.Scattergeo(
    lat=lats, lon=lons, mode="lines",
    line=dict(color="#00d2ff", width=2),
    name="Ground Track"
))

# Satellite position
fig.add_trace(go.Scattergeo(
    lat=[sat_lat], lon=[sat_lon], mode="markers+text",
    marker=dict(size=12, color="#ff6b6b", symbol="star"),
    text=["UniSat-1"], textposition="top right",
    name="Satellite"
))

# Ground station
fig.add_trace(go.Scattergeo(
    lat=[gs_lat], lon=[gs_lon], mode="markers+text",
    marker=dict(size=10, color="#2ecc71", symbol="triangle-up"),
    text=["Tashkent GS"], textposition="top right",
    name="Ground Station"
))

fig.update_geos(
    projection_type="orthographic",
    projection_rotation=dict(lon=sat_lon, lat=sat_lat),
    showland=True, landcolor="#1a1a2e",
    showocean=True, oceancolor="#0a0a1a",
    showcoastlines=True, coastlinecolor="#30475e",
    showlakes=False,
    bgcolor="#0E1117",
)
fig.update_layout(
    template="plotly_dark", height=600,
    margin=dict(l=0, r=0, t=30, b=0),
    title="Real-time Orbit Visualization"
)

st.plotly_chart(fig, use_container_width=True)

# Orbit info
col1, col2, col3, col4 = st.columns(4)
col1.metric("Latitude", f"{sat_lat:.2f}°")
col2.metric("Longitude", f"{sat_lon:.2f}°")
col3.metric("Altitude", "550.0 km")
col4.metric("Velocity", "7.59 km/s")
