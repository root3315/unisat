"""Orbit Visualizer — SGP4 propagation and Plotly figure builders."""

import math
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass

import numpy as np

# Default ISS-like TLE for UniSat demo
DEFAULT_TLE = (
    "1 99999U 26010A   26045.50000000  .00000500  00000-0  25000-4 0  9990",
    "2 99999  97.6000 120.0000 0001000  90.0000 270.0000 15.05000000    10",
)


@dataclass
class SatPosition:
    """Satellite position at a given time."""
    latitude: float
    longitude: float
    altitude_km: float
    timestamp: datetime


def propagate_ground_track(n_points: int = 200, hours: float = 2.5) -> list[SatPosition]:
    """Generate ground track points using simplified Keplerian model."""
    positions = []
    alt_km = 550.0
    inclination = math.radians(97.6)
    period_s = 2 * math.pi * math.sqrt((6371 + alt_km) ** 3 / 398600.4418)
    omega_earth = 2 * math.pi / 86400

    now = datetime.now(timezone.utc)
    total_seconds = hours * 3600

    for i in range(n_points):
        t = (i / n_points) * total_seconds
        mean_anomaly = 2 * math.pi * t / period_s

        lat = math.degrees(math.asin(math.sin(inclination) * math.sin(mean_anomaly)))
        lon_inertial = math.degrees(math.atan2(
            math.cos(inclination) * math.sin(mean_anomaly),
            math.cos(mean_anomaly)
        ))
        lon = lon_inertial - math.degrees(omega_earth * t)
        lon = ((lon + 180) % 360) - 180

        positions.append(SatPosition(
            latitude=lat, longitude=lon, altitude_km=alt_km,
            timestamp=now + timedelta(seconds=t),
        ))

    return positions


def predict_passes(gs_lat: float, gs_lon: float, min_elevation: float = 5.0,
                   hours: float = 48.0) -> list[dict]:
    """Predict ground station passes."""
    track = propagate_ground_track(n_points=1000, hours=hours)
    passes = []
    in_pass = False
    pass_start = None

    for pos in track:
        # Simplified: pass when satellite is within ~2500 km of GS
        dlat = math.radians(pos.latitude - gs_lat)
        dlon = math.radians(pos.longitude - gs_lon)
        a = math.sin(dlat / 2) ** 2 + \
            math.cos(math.radians(gs_lat)) * math.cos(math.radians(pos.latitude)) * \
            math.sin(dlon / 2) ** 2
        dist_km = 2 * 6371 * math.asin(math.sqrt(a))

        max_range = 2500  # ~5° elevation at 550 km
        if dist_km < max_range:
            if not in_pass:
                in_pass = True
                pass_start = pos.timestamp
        else:
            if in_pass:
                in_pass = False
                duration = (pos.timestamp - pass_start).total_seconds()
                elevation = max(5.0, 90.0 - (dist_km / max_range) * 85.0)
                passes.append({
                    "aos": pass_start.strftime("%Y-%m-%d %H:%M:%S"),
                    "los": pos.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                    "duration_s": round(duration),
                    "max_elevation_deg": round(elevation, 1),
                })

    return passes


def is_in_eclipse(lat: float, lon: float, timestamp: datetime) -> bool:
    """Simplified eclipse check based on sun position."""
    day_of_year = timestamp.timetuple().tm_yday
    hour = timestamp.hour + timestamp.minute / 60.0

    # Solar declination (simplified)
    declination = -23.45 * math.cos(math.radians(360 / 365 * (day_of_year + 10)))
    hour_angle = 15 * (hour - 12)  # degrees

    # Solar elevation at satellite sub-point
    solar_elev = math.degrees(math.asin(
        math.sin(math.radians(lat)) * math.sin(math.radians(declination)) +
        math.cos(math.radians(lat)) * math.cos(math.radians(declination)) *
        math.cos(math.radians(hour_angle))
    ))

    return solar_elev < -18  # Below horizon = eclipse
