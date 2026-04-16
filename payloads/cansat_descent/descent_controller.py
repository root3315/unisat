"""CanSat Descent Controller — Parachute deployment and descent analysis.

Implements parachute deployment logic, descent rate calculation,
and landing zone prediction for CanSat competitions.
"""

import math
import time
import logging
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("unisat.cansat")

# Physical constants
G = 9.80665  # m/s^2
RHO_SEA_LEVEL = 1.225  # kg/m^3 air density at sea level
TEMP_LAPSE_RATE = 0.0065  # K/m temperature lapse rate


class DescentPhase(Enum):
    """Descent flight phases."""
    PRE_LAUNCH = "pre_launch"
    ASCENT = "ascent"
    APOGEE = "apogee"
    FREE_FALL = "free_fall"
    PARACHUTE_DESCENT = "parachute_descent"
    LANDED = "landed"


@dataclass
class DescentConfig:
    """Parachute and descent configuration."""
    cansat_mass_kg: float = 0.350
    parachute_diameter_m: float = 0.6
    drag_coefficient: float = 1.75  # Hemispherical chute
    deploy_altitude_m: float = 400.0
    deploy_delay_s: float = 2.0
    target_descent_rate_ms: float = 8.0  # Competition: 6-11 m/s


@dataclass
class DescentTelemetry:
    """Single descent telemetry point."""
    timestamp: float
    altitude_m: float
    velocity_ms: float
    acceleration_ms2: float
    temperature_c: float
    pressure_pa: float
    phase: DescentPhase
    latitude: float = 0.0
    longitude: float = 0.0


@dataclass
class DescentResult:
    """Complete descent analysis result."""
    max_altitude_m: float = 0.0
    deploy_altitude_m: float = 0.0
    total_descent_time_s: float = 0.0
    avg_descent_rate_ms: float = 0.0
    landing_velocity_ms: float = 0.0
    telemetry: list[DescentTelemetry] = field(default_factory=list)


class DescentController:
    """Controls parachute deployment and tracks descent."""

    def __init__(self, config: DescentConfig | None = None) -> None:
        self.config = config or DescentConfig()
        self.phase = DescentPhase.PRE_LAUNCH
        self.telemetry: list[DescentTelemetry] = []
        self._deploy_triggered = False
        self._prev_altitude = 0.0
        self._prev_velocity = 0.0

    def air_density(self, altitude_m: float) -> float:
        """Calculate air density at altitude using barometric formula."""
        t0 = 288.15  # Sea level temperature (K)
        temp = t0 - TEMP_LAPSE_RATE * altitude_m
        if temp <= 0:
            temp = 1.0
        return RHO_SEA_LEVEL * (temp / t0) ** (G / (TEMP_LAPSE_RATE * 287.058) - 1)

    def parachute_area(self) -> float:
        """Calculate parachute cross-sectional area."""
        r = self.config.parachute_diameter_m / 2
        return math.pi * r * r

    def terminal_velocity(self, altitude_m: float) -> float:
        """Calculate terminal velocity at given altitude."""
        rho = self.air_density(altitude_m)
        area = self.parachute_area()
        cd = self.config.drag_coefficient
        m = self.config.cansat_mass_kg
        return math.sqrt(2 * m * G / (rho * cd * area))

    def drag_force(self, velocity_ms: float, altitude_m: float,
                   chute_deployed: bool) -> float:
        """Calculate aerodynamic drag force."""
        rho = self.air_density(altitude_m)
        if chute_deployed:
            area = self.parachute_area()
            cd = self.config.drag_coefficient
        else:
            area = 0.005  # CanSat body cross-section
            cd = 0.47  # Sphere-like
        return 0.5 * rho * cd * area * velocity_ms * velocity_ms

    def simulate_descent(self, launch_altitude_m: float = 500.0,
                         dt: float = 0.1) -> DescentResult:
        """Simulate complete descent from apogee to landing."""
        result = DescentResult()
        result.max_altitude_m = launch_altitude_m

        altitude = launch_altitude_m
        velocity = 0.0  # Starting from apogee (zero vertical velocity)
        t = 0.0
        chute_deployed = False
        deploy_time = None

        while altitude > 0:
            # Check parachute deployment
            if not chute_deployed and altitude <= self.config.deploy_altitude_m:
                if deploy_time is None:
                    deploy_time = t
                if t - deploy_time >= self.config.deploy_delay_s:
                    chute_deployed = True
                    result.deploy_altitude_m = altitude
                    logger.info("Parachute deployed at %.1f m", altitude)

            # Calculate forces — drag opposes velocity direction
            drag = self.drag_force(abs(velocity), altitude, chute_deployed)
            drag_accel = drag / self.config.cansat_mass_kg
            if velocity > 0:
                acceleration = G - drag_accel
            else:
                acceleration = G + drag_accel

            # Semi-implicit Euler for stability
            velocity += acceleration * dt
            velocity = max(velocity, 0.0)  # prevent bouncing
            altitude -= velocity * dt

            # Temperature and pressure estimate
            temp_c = 15.0 - TEMP_LAPSE_RATE * altitude * 1000
            pressure_base = max(0.0, 1.0 - 2.25577e-5 * altitude)
            pressure = 101325.0 * pressure_base ** 5.25588

            # Determine phase
            if chute_deployed:
                phase = DescentPhase.PARACHUTE_DESCENT
            else:
                phase = DescentPhase.FREE_FALL

            # Record telemetry at 10 Hz
            if int(t / 0.1) != int((t - dt) / 0.1):
                result.telemetry.append(DescentTelemetry(
                    timestamp=t, altitude_m=round(altitude, 2),
                    velocity_ms=round(velocity, 2),
                    acceleration_ms2=round(acceleration, 2),
                    temperature_c=round(temp_c, 1),
                    pressure_pa=round(pressure, 0),
                    phase=phase,
                ))

            t += dt

        result.total_descent_time_s = round(t, 1)
        result.landing_velocity_ms = round(velocity, 2)

        # Calculate average descent rate (parachute phase only)
        chute_points = [p for p in result.telemetry
                        if p.phase == DescentPhase.PARACHUTE_DESCENT]
        if chute_points:
            result.avg_descent_rate_ms = round(
                sum(p.velocity_ms for p in chute_points) / len(chute_points), 2
            )

        return result

    def validate_competition_requirements(self, result: DescentResult) -> dict:
        """Check if descent meets competition requirements."""
        checks = {
            "descent_rate_ok": 6.0 <= result.avg_descent_rate_ms <= 11.0,
            "total_time_ok": result.total_descent_time_s > 30,
            "landing_velocity_safe": result.landing_velocity_ms < 12.0,
            "parachute_deployed": result.deploy_altitude_m > 0,
            "telemetry_count": len(result.telemetry) > 100,
        }
        checks["all_passed"] = all(v for k, v in checks.items() if k != "all_passed")
        return checks


def design_parachute(mass_kg: float, target_velocity_ms: float = 8.0,
                     altitude_m: float = 0.0) -> dict:
    """Design parachute for given mass and target descent rate."""
    rho = RHO_SEA_LEVEL * (1 - 2.25577e-5 * altitude_m) ** 4.25588
    cd = 1.75  # Hemispherical canopy

    area = (2 * mass_kg * G) / (rho * cd * target_velocity_ms ** 2)
    diameter = 2 * math.sqrt(area / math.pi)

    return {
        "required_area_m2": round(area, 4),
        "diameter_m": round(diameter, 3),
        "drag_coefficient": cd,
        "terminal_velocity_ms": round(target_velocity_ms, 1),
        "canopy_type": "hemispherical",
        "material": "ripstop nylon (30 g/m²)",
        "shroud_lines": max(6, int(diameter * 10)),
    }


if __name__ == "__main__":
    # Example: design and simulate
    config = DescentConfig(cansat_mass_kg=0.350, parachute_diameter_m=0.6)
    controller = DescentController(config)
    result = controller.simulate_descent(launch_altitude_m=500)

    print(f"Max altitude: {result.max_altitude_m} m")
    print(f"Deploy altitude: {result.deploy_altitude_m:.1f} m")
    print(f"Total time: {result.total_descent_time_s} s")
    print(f"Avg descent rate: {result.avg_descent_rate_ms} m/s")
    print(f"Landing velocity: {result.landing_velocity_ms} m/s")
    print(f"Telemetry points: {len(result.telemetry)}")

    checks = controller.validate_competition_requirements(result)
    print(f"\nCompetition checks: {checks}")

    parachute = design_parachute(0.350)
    print(f"\nParachute design: {parachute}")
