"""Orbit Predictor for UniSat CubeSat.

Uses the SGP4 propagation model to predict satellite position, ground station
pass windows, and eclipse/sunlight periods from Two-Line Element sets.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sgp4.api import Satrec, jday
from sgp4.earth_gravity import wgs72

from modules import BaseModule, ModuleStatus

EARTH_RADIUS_KM = 6371.0
EARTH_MU = 398600.4418
J2000_EPOCH = datetime(2000, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


@dataclass
class SatellitePosition:
    """Satellite position and velocity in ECI frame.

    Attributes:
        timestamp: UTC datetime of the position.
        x_km, y_km, z_km: ECI position components in km.
        vx_kms, vy_kms, vz_kms: ECI velocity components in km/s.
        latitude: Subsatellite geodetic latitude in degrees.
        longitude: Subsatellite longitude in degrees.
        altitude_km: Altitude above WGS84 ellipsoid in km.
    """

    timestamp: datetime
    x_km: float
    y_km: float
    z_km: float
    vx_kms: float
    vy_kms: float
    vz_kms: float
    latitude: float
    longitude: float
    altitude_km: float


@dataclass
class PassPrediction:
    """Ground station pass prediction.

    Attributes:
        aos: Acquisition of signal time (UTC).
        los: Loss of signal time (UTC).
        max_elevation_deg: Maximum elevation angle in degrees.
        duration_s: Pass duration in seconds.
    """

    aos: datetime
    los: datetime
    max_elevation_deg: float
    duration_s: float


class OrbitPredictor(BaseModule):
    """SGP4-based orbit predictor with pass and eclipse computations.

    Attributes:
        satellite: SGP4 Satrec object.
        ground_station: Dict with lat, lon, alt_km of the ground station.
        tle_line1: TLE line 1 string.
        tle_line2: TLE line 2 string.
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        """Initialize the orbit predictor.

        Args:
            config: Configuration with 'tle_line1', 'tle_line2', and 'ground_station'.
        """
        super().__init__("orbit_predictor", config)
        self.tle_line1: str = self.config.get("tle_line1", "")
        self.tle_line2: str = self.config.get("tle_line2", "")
        self.satellite: Satrec | None = None
        gs = self.config.get("ground_station", {})
        self.ground_station: dict[str, float] = {
            "lat": gs.get("latitude", 41.2995),
            "lon": gs.get("longitude", 69.2401),
            "alt_km": gs.get("altitude_m", 455) / 1000.0,
        }

    async def initialize(self) -> bool:
        """Parse TLE and initialize the SGP4 propagator.

        Returns:
            True if TLE was parsed successfully or a default orbit was set.
        """
        if self.tle_line1 and self.tle_line2:
            self.satellite = Satrec.twoline2rv(self.tle_line1, self.tle_line2)
        else:
            self.satellite = Satrec()
            self.satellite.sgp4init(
                wgs72, "i", 99999, _epoch_days_from_now(),
                0.0, 0.0, 0.0, 0.001, math.radians(97.6),
                0.0, math.radians(0.0), 0.0, _mean_motion_from_alt(550.0),
            )
            self.logger.warning("No TLE provided, using default 550km SSO orbit")
        self.status = ModuleStatus.READY
        self.logger.info("Orbit predictor initialized")
        return True

    async def start(self) -> None:
        """Start the orbit predictor."""
        self.status = ModuleStatus.RUNNING

    async def stop(self) -> None:
        """Stop the orbit predictor."""
        self.status = ModuleStatus.STOPPED

    async def get_status(self) -> dict[str, Any]:
        """Return orbit predictor status.

        Returns:
            Dict with current position summary and predictor state.
        """
        pos = self.get_position()
        return {
            "status": self.status.name,
            "has_tle": bool(self.tle_line1),
            "latitude": round(pos.latitude, 4) if pos else None,
            "longitude": round(pos.longitude, 4) if pos else None,
            "altitude_km": round(pos.altitude_km, 2) if pos else None,
            "error_count": self._error_count,
        }

    def get_position(self, dt: datetime | None = None) -> SatellitePosition | None:
        """Compute satellite position at a given time.

        Args:
            dt: UTC datetime. Defaults to now.

        Returns:
            SatellitePosition or None on propagation error.
        """
        if not self.satellite:
            return None
        dt = dt or datetime.now(timezone.utc)
        jd, fr = jday(dt.year, dt.month, dt.day, dt.hour, dt.minute,
                       dt.second + dt.microsecond / 1e6)
        error, r, v = self.satellite.sgp4(jd, fr)
        if error != 0:
            self.record_error(f"SGP4 error code {error}")
            return None
        x, y, z = r
        vx, vy, vz = v
        lat, lon, alt = _eci_to_geodetic(x, y, z, jd + fr)
        return SatellitePosition(
            timestamp=dt, x_km=x, y_km=y, z_km=z,
            vx_kms=vx, vy_kms=vy, vz_kms=vz,
            latitude=lat, longitude=lon, altitude_km=alt,
        )

    def predict_passes(self, hours: float = 24.0, min_elevation: float = 5.0,
                       step_s: float = 30.0) -> list[PassPrediction]:
        """Predict ground station passes over a time window.

        Args:
            hours: Look-ahead window in hours.
            min_elevation: Minimum elevation angle in degrees.
            step_s: Time step in seconds for the sweep.

        Returns:
            List of PassPrediction objects sorted by AOS time.
        """
        now = datetime.now(timezone.utc)
        passes: list[PassPrediction] = []
        in_pass = False
        aos_time = now
        max_el = 0.0
        total_steps = int(hours * 3600 / step_s)
        for i in range(total_steps):
            dt = datetime.fromtimestamp(now.timestamp() + i * step_s, tz=timezone.utc)
            pos = self.get_position(dt)
            if not pos:
                continue
            el = self._elevation_angle(pos)
            if el >= min_elevation and not in_pass:
                in_pass = True
                aos_time = dt
                max_el = el
            elif el >= min_elevation and in_pass:
                max_el = max(max_el, el)
            elif el < min_elevation and in_pass:
                in_pass = False
                duration = (dt.timestamp() - aos_time.timestamp())
                passes.append(PassPrediction(
                    aos=aos_time, los=dt, max_elevation_deg=round(max_el, 2),
                    duration_s=round(duration, 1),
                ))
        return passes

    def is_in_sunlight(self, dt: datetime | None = None) -> bool:
        """Determine if the satellite is in sunlight (not eclipsed).

        Uses a cylindrical shadow model for simplicity.

        Args:
            dt: UTC datetime. Defaults to now.

        Returns:
            True if the satellite is illuminated by the Sun.
        """
        pos = self.get_position(dt)
        if not pos:
            return True
        sat_dist = math.sqrt(pos.x_km**2 + pos.y_km**2 + pos.z_km**2)
        dt = dt or datetime.now(timezone.utc)
        day_of_year = dt.timetuple().tm_yday
        sun_lon = math.radians((day_of_year - 80) * 360 / 365.25)
        sun_x = math.cos(sun_lon)
        sun_y = math.sin(sun_lon)
        dot = (pos.x_km * sun_x + pos.y_km * sun_y) / sat_dist
        if dot > 0:
            return True
        perp_dist = math.sqrt(sat_dist**2 - (dot * sat_dist)**2)
        return perp_dist > EARTH_RADIUS_KM

    def _elevation_angle(self, pos: SatellitePosition) -> float:
        """Compute elevation angle from the ground station to the satellite.

        Args:
            pos: Satellite position in ECI.

        Returns:
            Elevation angle in degrees.
        """
        gs_lat = math.radians(self.ground_station["lat"])
        gs_lon = math.radians(self.ground_station["lon"])
        gs_alt = self.ground_station["alt_km"]
        gs_r = EARTH_RADIUS_KM + gs_alt
        gs_x = gs_r * math.cos(gs_lat) * math.cos(gs_lon)
        gs_y = gs_r * math.cos(gs_lat) * math.sin(gs_lon)
        gs_z = gs_r * math.sin(gs_lat)
        dx = pos.x_km - gs_x
        dy = pos.y_km - gs_y
        dz = pos.z_km - gs_z
        slant_range = math.sqrt(dx**2 + dy**2 + dz**2)
        if slant_range < 1e-6:
            return 90.0
        dot = (dx * gs_x + dy * gs_y + dz * gs_z) / (slant_range * gs_r)
        elevation = math.degrees(math.asin(max(-1.0, min(1.0, dot))))
        return elevation


def _eci_to_geodetic(x: float, y: float, z: float, jd_utc: float) -> tuple[float, float, float]:
    """Convert ECI coordinates to geodetic (lat, lon, alt).

    Args:
        x, y, z: ECI position in km.
        jd_utc: Julian date (UTC).

    Returns:
        Tuple of (latitude_deg, longitude_deg, altitude_km).
    """
    r = math.sqrt(x**2 + y**2 + z**2)
    lat = math.degrees(math.asin(z / r)) if r > 0 else 0.0
    gmst = _greenwich_sidereal_time(jd_utc)
    lon_eci = math.degrees(math.atan2(y, x))
    lon = (lon_eci - gmst + 180) % 360 - 180
    alt = r - EARTH_RADIUS_KM
    return lat, lon, alt


def _greenwich_sidereal_time(jd: float) -> float:
    """Compute Greenwich Mean Sidereal Time in degrees.

    Args:
        jd: Julian date.

    Returns:
        GMST in degrees.
    """
    t = (jd - 2451545.0) / 36525.0
    gmst = 280.46061837 + 360.98564736629 * (jd - 2451545.0) + t**2 * 0.000387933
    return gmst % 360


def _epoch_days_from_now() -> float:
    """Compute SGP4 epoch as days since 1949-12-31.

    Returns:
        Days since epoch.
    """
    now = datetime.now(timezone.utc)
    ref = datetime(1949, 12, 31, 0, 0, 0, tzinfo=timezone.utc)
    return (now - ref).total_seconds() / 86400.0


def _mean_motion_from_alt(alt_km: float) -> float:
    """Compute mean motion in radians/minute from altitude.

    Args:
        alt_km: Orbital altitude in km.

    Returns:
        Mean motion in radians/minute.
    """
    a = EARTH_RADIUS_KM + alt_km
    period_s = 2 * math.pi * math.sqrt(a**3 / EARTH_MU)
    return 2 * math.pi / (period_s / 60.0)
