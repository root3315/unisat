"""Map Renderer — Render ground track and markers on world map."""

from typing import Any

import plotly.graph_objects as go


def create_ground_track_figure(
    track_lats: list[float],
    track_lons: list[float],
    sat_lat: float,
    sat_lon: float,
    gs_lat: float = 41.2995,
    gs_lon: float = 69.2401,
    gs_name: str = "Tashkent GS",
) -> go.Figure:
    """Create a Plotly globe figure with ground track and markers."""
    fig = go.Figure()

    # Ground track
    fig.add_trace(go.Scattergeo(
        lat=track_lats, lon=track_lons, mode="lines",
        line=dict(color="#00d2ff", width=2), name="Ground Track",
    ))

    # Satellite position
    fig.add_trace(go.Scattergeo(
        lat=[sat_lat], lon=[sat_lon], mode="markers+text",
        marker=dict(size=12, color="#ff6b6b", symbol="star"),
        text=["UniSat-1"], textposition="top right", name="Satellite",
    ))

    # Ground station
    fig.add_trace(go.Scattergeo(
        lat=[gs_lat], lon=[gs_lon], mode="markers+text",
        marker=dict(size=10, color="#2ecc71", symbol="triangle-up"),
        text=[gs_name], textposition="top right", name="Ground Station",
    ))

    fig.update_geos(
        projection_type="orthographic",
        projection_rotation=dict(lon=sat_lon, lat=sat_lat),
        showland=True, landcolor="#1a1a2e",
        showocean=True, oceancolor="#0a0a1a",
        showcoastlines=True, coastlinecolor="#30475e",
        showlakes=False, bgcolor="#0E1117",
    )

    fig.update_layout(
        template="plotly_dark", height=600,
        margin=dict(l=0, r=0, t=30, b=0),
    )

    return fig


def create_2d_map(
    track_lats: list[float],
    track_lons: list[float],
    markers: list[dict[str, Any]] | None = None,
) -> go.Figure:
    """Create a 2D map projection with ground track."""
    fig = go.Figure()

    fig.add_trace(go.Scattergeo(
        lat=track_lats, lon=track_lons, mode="lines",
        line=dict(color="#00d2ff", width=1.5), name="Track",
    ))

    if markers:
        for m in markers:
            fig.add_trace(go.Scattergeo(
                lat=[m["lat"]], lon=[m["lon"]], mode="markers+text",
                marker=dict(size=m.get("size", 8), color=m.get("color", "red")),
                text=[m.get("name", "")], textposition="top right",
                name=m.get("name", "Marker"),
            ))

    fig.update_geos(
        projection_type="natural earth",
        showland=True, landcolor="#1a1a2e",
        showocean=True, oceancolor="#0a0a1a",
        showcoastlines=True, coastlinecolor="#30475e",
        bgcolor="#0E1117",
    )

    fig.update_layout(template="plotly_dark", height=400,
                      margin=dict(l=0, r=0, t=0, b=0))
    return fig
