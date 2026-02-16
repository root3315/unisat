"""Visualize — Generate Plotly charts from simulation results."""

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from orbit_simulator import elements_from_config, propagate
from power_simulator import simulate_power
from thermal_simulator import simulate_thermal


def plot_ground_track() -> go.Figure:
    """Plot satellite ground track on world map."""
    elements = elements_from_config(550, 97.6)
    track = propagate(elements, 6000, dt_s=30)

    fig = go.Figure(go.Scattergeo(
        lat=[s.lat for s in track],
        lon=[s.lon for s in track],
        mode="lines", line=dict(color="#00d2ff", width=2),
    ))
    fig.update_geos(
        projection_type="natural earth",
        showland=True, landcolor="#1a1a2e",
        showocean=True, oceancolor="#0a0a1a",
        showcoastlines=True, coastlinecolor="#30475e",
    )
    fig.update_layout(template="plotly_dark", title="Ground Track (1.5 orbits)")
    return fig


def plot_power_budget() -> go.Figure:
    """Plot power budget over multiple orbits."""
    profile = simulate_power()

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                        subplot_titles=["Power (W)", "Battery SOC (%)"])

    time_min = [p.time_s / 60 for p in profile]

    fig.add_trace(go.Scatter(
        x=time_min, y=[p.solar_power_w for p in profile],
        name="Solar", fill="tozeroy", line=dict(color="#f9ca24"),
    ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=time_min, y=[p.consumption_w for p in profile],
        name="Consumption", line=dict(color="#ff6b6b", dash="dash"),
    ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=time_min, y=[p.battery_soc_pct for p in profile],
        name="SOC", line=dict(color="#4ecdc4"),
    ), row=2, col=1)

    fig.update_layout(template="plotly_dark", title="Power Budget Simulation")
    fig.update_xaxes(title_text="Time (minutes)", row=2, col=1)
    return fig


def plot_thermal() -> go.Figure:
    """Plot thermal analysis results."""
    states = simulate_thermal()
    time_min = [s.time_s / 60 for s in states]
    face_names = ["+X", "-X", "+Y", "-Y", "+Z", "-Z"]

    fig = go.Figure()
    colors = ["#ff6b6b", "#fd79a8", "#4ecdc4", "#74b9ff", "#f9ca24", "#a29bfe"]

    for i, (name, color) in enumerate(zip(face_names, colors)):
        temps = [s.face_temps_c[i] for s in states]
        fig.add_trace(go.Scatter(x=time_min, y=temps, name=name,
                                  line=dict(color=color)))

    fig.add_trace(go.Scatter(
        x=time_min, y=[s.internal_temp_c for s in states],
        name="Internal", line=dict(color="white", width=3),
    ))

    fig.update_layout(
        template="plotly_dark", title="Thermal Analysis",
        xaxis_title="Time (minutes)", yaxis_title="Temperature (°C)",
    )
    return fig


if __name__ == "__main__":
    print("Generating plots...")
    fig1 = plot_ground_track()
    fig1.write_html("output_ground_track.html")
    fig2 = plot_power_budget()
    fig2.write_html("output_power_budget.html")
    fig3 = plot_thermal()
    fig3.write_html("output_thermal.html")
    print("Plots saved as HTML files")
