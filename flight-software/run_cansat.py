#!/usr/bin/env python3
"""UniSat CanSat Test Runner — Full flight simulation in one command.

Simulates a complete CanSat flight: pre-launch → launch → ascent →
apogee → parachute descent → landing. Uses simulated IMU and barometer
data with realistic flight dynamics.

Usage:
    python run_cansat.py                        # default config
    python run_cansat.py --config my_config.json
    python run_cansat.py --max-altitude 800 --descent-rate 8.5
"""

import argparse
import asyncio
import json
import logging
import math
import random
import sys
import time
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from core.mission_types import get_mission_profile
from core.event_bus import EventBus, Event
from core.state_machine import StateMachine
from core.module_registry import ModuleRegistry

logger = logging.getLogger("unisat.cansat_runner")


class CanSatFlightSimulator:
    """Simulates realistic CanSat flight dynamics for testing.

    Generates IMU and barometer data matching a real flight:
    ground → rocket ascent → ejection → parachute descent → landing.
    """

    def __init__(
        self,
        max_altitude_m: float = 800.0,
        ascent_time_s: float = 15.0,
        descent_rate_m_s: float = 8.0,
        ground_altitude_m: float = 0.0,
    ) -> None:
        self.max_altitude_m = max_altitude_m
        self.ascent_time_s = ascent_time_s
        self.descent_rate_m_s = descent_rate_m_s
        self.ground_altitude_m = ground_altitude_m

        self._start_time: float = 0.0
        self._launch_time: float = 0.0
        self._phase = "ground"
        self._landed = False

    def start(self, launch_delay_s: float = 3.0) -> None:
        """Start the simulation clock."""
        self._start_time = time.time()
        self._launch_time = self._start_time + launch_delay_s
        self._phase = "ground"
        logger.info(
            "Simulation started: max_alt=%.0fm, descent=%.1fm/s, launch in %.0fs",
            self.max_altitude_m, self.descent_rate_m_s, launch_delay_s,
        )

    def get_flight_data(self) -> dict:
        """Get current simulated flight data.

        Returns dict with: altitude_m, vertical_speed_m_s, accel_g,
        pressure_pa, temperature_c, phase, elapsed_s
        """
        now = time.time()
        t_since_start = now - self._start_time
        t_since_launch = now - self._launch_time

        if t_since_launch < 0:
            # Pre-launch: on the ground
            self._phase = "ground"
            return self._ground_data(t_since_start)

        # Calculate altitude based on flight phase
        # Ascent: parabolic acceleration
        if t_since_launch <= self.ascent_time_s:
            self._phase = "ascent"
            frac = t_since_launch / self.ascent_time_s
            altitude = self.max_altitude_m * (2 * frac - frac ** 2)
            v_speed = (2 * self.max_altitude_m / self.ascent_time_s) * (1 - frac)
            # High acceleration during boost
            accel_g = 5.0 + random.gauss(0, 0.3)
            if frac > 0.7:
                # Coast phase near end of ascent
                accel_g = 0.2 + random.gauss(0, 0.1)

        else:
            # Descent phase
            t_descent = t_since_launch - self.ascent_time_s
            descent_distance = self.descent_rate_m_s * t_descent
            altitude = self.max_altitude_m - descent_distance

            if altitude <= self.ground_altitude_m:
                altitude = self.ground_altitude_m
                self._phase = "landed"
                self._landed = True
                return self._landed_data(t_since_start)

            # Brief apogee detection window
            if t_descent < 2.0:
                self._phase = "apogee"
                v_speed = -self.descent_rate_m_s * (t_descent / 2.0)
                accel_g = 0.1 + random.gauss(0, 0.05)  # near-freefall
            else:
                self._phase = "descent"
                v_speed = -self.descent_rate_m_s
                accel_g = 1.0 + random.gauss(0, 0.05)  # parachute = ~1g

        # Convert altitude to pressure (ISA model)
        pressure = 101325.0 * (1 - 0.0000225577 * (altitude + self.ground_altitude_m)) ** 5.25588
        temperature = 15.0 - 0.0065 * altitude + random.gauss(0, 0.2)

        return {
            "altitude_m": round(altitude + self.ground_altitude_m, 2),
            "altitude_agl_m": round(altitude, 2),
            "vertical_speed_m_s": round(v_speed, 2),
            "accel_g": round(abs(accel_g), 3),
            "accel_x_g": round(random.gauss(0, 0.1), 3),
            "accel_y_g": round(random.gauss(0, 0.1), 3),
            "accel_z_g": round(-accel_g + random.gauss(0, 0.05), 3),
            "pressure_pa": round(pressure, 1),
            "temperature_c": round(temperature, 2),
            "phase": self._phase,
            "elapsed_s": round(t_since_start, 2),
        }

    def _ground_data(self, elapsed: float) -> dict:
        return {
            "altitude_m": self.ground_altitude_m,
            "altitude_agl_m": 0.0,
            "vertical_speed_m_s": 0.0,
            "accel_g": 1.0 + random.gauss(0, 0.02),
            "accel_x_g": random.gauss(0, 0.02),
            "accel_y_g": random.gauss(0, 0.02),
            "accel_z_g": round(-1.0 + random.gauss(0, 0.02), 3),
            "pressure_pa": 101325.0 + random.gauss(0, 5),
            "temperature_c": 20.0 + random.gauss(0, 0.2),
            "phase": "ground",
            "elapsed_s": round(elapsed, 2),
        }

    def _landed_data(self, elapsed: float) -> dict:
        return {
            "altitude_m": self.ground_altitude_m,
            "altitude_agl_m": 0.0,
            "vertical_speed_m_s": 0.0,
            "accel_g": 1.0 + random.gauss(0, 0.01),
            "accel_x_g": random.gauss(0, 0.01),
            "accel_y_g": random.gauss(0, 0.01),
            "accel_z_g": round(-1.0 + random.gauss(0, 0.01), 3),
            "pressure_pa": 101325.0 + random.gauss(0, 3),
            "temperature_c": 20.0 + random.gauss(0, 0.1),
            "phase": "landed",
            "elapsed_s": round(elapsed, 2),
        }

    @property
    def is_landed(self) -> bool:
        return self._landed


async def run_cansat_test(
    config_path: str | None = None,
    max_altitude: float = 800.0,
    descent_rate: float = 8.0,
    launch_delay: float = 3.0,
) -> dict:
    """Run a complete CanSat flight test simulation.

    Args:
        config_path: Path to mission config (defaults to cansat template).
        max_altitude: Simulated max altitude in meters.
        descent_rate: Descent rate in m/s.
        launch_delay: Seconds before simulated launch.

    Returns:
        Dict with test results and competition validation.
    """
    # Setup logging
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    ))
    root = logging.getLogger("unisat")
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.INFO)

    # Load config
    if config_path and Path(config_path).exists():
        with open(config_path) as f:
            config = json.load(f)
    else:
        template_path = Path(__file__).parent.parent / "mission_templates" / "cansat_standard.json"
        if template_path.exists():
            with open(template_path) as f:
                config = json.load(f)
        else:
            config = {
                "mission": {"name": "CanSat Test", "mission_type": "cansat_standard"},
                "subsystems": {
                    "imu": {"enabled": True, "simulate": True},
                    "barometer": {"enabled": True, "simulate": True},
                    "descent_controller": {"enabled": True},
                    "gnss": {"enabled": True, "simulate": True},
                },
            }

    # Initialize flight systems
    from core.mission_types import build_profile_from_config
    profile = build_profile_from_config(config)
    event_bus = EventBus()
    state_machine = StateMachine(profile)
    registry = ModuleRegistry(event_bus)

    logger.info("=" * 60)
    logger.info("  UNISAT CANSAT FLIGHT TEST")
    logger.info("  Max altitude: %.0f m | Descent rate: %.1f m/s", max_altitude, descent_rate)
    logger.info("  Capsule: 64mm dia x 80mm | Max mass: 500g")
    logger.info("=" * 60)

    # Load modules
    registry.load_modules_from_config(
        config,
        core_modules=profile.core_modules,
        optional_modules=profile.optional_modules,
    )
    await registry.initialize_all()
    await registry.start_all()

    logger.info("Modules loaded: %s", list(registry.modules.keys()))
    logger.info("Initial phase: %s", state_machine.phase_name)

    # Create flight simulator
    sim = CanSatFlightSimulator(
        max_altitude_m=max_altitude,
        descent_rate_m_s=descent_rate,
    )
    sim.start(launch_delay_s=launch_delay)

    # Get modules
    imu = registry.get_module("imu")
    baro = registry.get_module("barometer")
    dc = registry.get_module("descent_controller")
    data_logger = registry.get_module("data_logger")

    # Arm descent controller
    if dc and hasattr(dc, "arm"):
        dc.arm()

    # Flight data collection
    telemetry_log: list[dict] = []
    phase_log: list[dict] = []
    sample_count = 0
    flight_start = time.time()

    logger.info("")
    logger.info("--- FLIGHT SIMULATION STARTING (launch in %.0fs) ---", launch_delay)
    logger.info("")

    last_phase = ""

    # Main simulation loop
    while not sim.is_landed:
        data = sim.get_flight_data()

        # Inject simulated data into IMU
        if imu:
            # Override simulated reading with flight data
            from modules.imu_sensor import IMUReading
            reading = IMUReading(
                timestamp=time.time(),
                accel_x_g=data["accel_x_g"],
                accel_y_g=data["accel_y_g"],
                accel_z_g=data["accel_z_g"],
                gyro_x_dps=random.gauss(0, 2),
                gyro_y_dps=random.gauss(0, 2),
                gyro_z_dps=random.gauss(0, 2),
            )
            imu._readings.append(reading)
            if len(imu._readings) > imu._max_readings:
                imu._readings = imu._readings[-imu._max_readings:]
            imu._sample_count += 1

        # Inject simulated data into barometer
        if baro:
            from modules.barometric_altimeter import BaroReading
            baro_reading = BaroReading(
                timestamp=time.time(),
                pressure_pa=data["pressure_pa"],
                temperature_c=data["temperature_c"],
                altitude_m=data["altitude_m"],
            )
            # Calculate vertical speed
            if baro._readings:
                prev = baro._readings[-1]
                dt = baro_reading.timestamp - prev.timestamp
                if dt > 0:
                    baro_reading.vertical_speed_m_s = (
                        baro_reading.altitude_m - prev.altitude_m
                    ) / dt

            baro._readings.append(baro_reading)
            if len(baro._readings) > baro._max_readings:
                baro._readings = baro._readings[-baro._max_readings:]
            baro._sample_count += 1

            # Track max altitude
            agl = data["altitude_agl_m"]
            if agl > baro._max_altitude_m:
                baro._max_altitude_m = agl

        # Update descent controller
        if dc and hasattr(dc, "update"):
            dc.update(
                altitude_agl_m=data["altitude_agl_m"],
                descent_rate_m_s=abs(data["vertical_speed_m_s"]),
                accel_g=data["accel_g"],
            )

        # Check sensor-driven phase transitions
        phase = state_machine.phase_name
        sensor_target = None

        if phase == "pre_launch":
            if imu and imu.detect_launch(threshold_g=3.0):
                sensor_target = ("launch_detect", "launch_detected")
        elif phase == "launch_detect":
            # Immediately transition to ascent once launch confirmed
            sensor_target = ("ascent", "launch_confirmed")
        elif phase == "ascent":
            if baro and baro.detect_apogee(window=8):
                sensor_target = ("apogee", "apogee_detected")
        elif phase == "apogee":
            # Auto-transition to descent
            if state_machine.get_elapsed() > 1.0:
                sensor_target = ("descent", "descent_start")
        elif phase == "descent":
            # Landing = stable 1g AND altitude near ground
            alt_agl = data["altitude_agl_m"] if baro else 999
            if alt_agl < 5.0 and imu and imu.detect_landing(window=20, threshold_g=0.15):
                sensor_target = ("landed", "landing_detected")

        # Timeout-based transitions
        if not sensor_target:
            auto = state_machine.check_timeout()
            if auto:
                sensor_target = (auto, "timeout")

        # Apply transition
        if sensor_target:
            await state_machine.transition_to(sensor_target[0], reason=sensor_target[1])

        # Log phase changes
        if state_machine.phase_name != last_phase:
            last_phase = state_machine.phase_name
            phase_entry = {
                "phase": last_phase,
                "time_s": round(time.time() - flight_start, 2),
                "altitude_m": data["altitude_agl_m"],
                "reason": sensor_target[1] if sensor_target else "initial",
            }
            phase_log.append(phase_entry)
            logger.info(
                ">> PHASE: %-15s | alt=%7.1fm | speed=%6.1fm/s | accel=%.1fg | t=%.1fs",
                last_phase.upper(),
                data["altitude_agl_m"],
                data["vertical_speed_m_s"],
                data["accel_g"],
                phase_entry["time_s"],
            )

        # Collect telemetry sample
        sample = {
            "time_s": round(time.time() - flight_start, 3),
            "phase": state_machine.phase_name,
            **data,
        }
        telemetry_log.append(sample)
        sample_count += 1

        # Print periodic status
        if sample_count % 50 == 0:
            logger.info(
                "   t=%6.1fs | alt=%7.1fm | v=%6.1fm/s | a=%.2fg | phase=%s | samples=%d",
                data["elapsed_s"], data["altitude_agl_m"],
                data["vertical_speed_m_s"], data["accel_g"],
                state_machine.phase_name, sample_count,
            )

        await asyncio.sleep(0.05)  # 20 Hz simulation

    # Flight complete
    flight_duration = time.time() - flight_start
    logger.info("")
    logger.info("=" * 60)
    logger.info("  FLIGHT COMPLETE")
    logger.info("=" * 60)

    # Validate competition requirements
    competition_result = None
    if dc and hasattr(dc, "validate_competition"):
        competition_result = dc.validate_competition()

    # Build results
    altitudes = [s["altitude_agl_m"] for s in telemetry_log]
    descent_samples = [s for s in telemetry_log if s["phase"] == "descent"]
    descent_rates = [abs(s["vertical_speed_m_s"]) for s in descent_samples] if descent_samples else [0]

    results = {
        "flight_duration_s": round(flight_duration, 1),
        "total_samples": sample_count,
        "max_altitude_m": round(max(altitudes), 1),
        "avg_descent_rate_m_s": round(sum(descent_rates) / max(len(descent_rates), 1), 2),
        "phases": phase_log,
        "phase_count": len(phase_log),
    }

    if competition_result:
        results["competition"] = {
            "valid": competition_result.valid,
            "descent_rate_avg": competition_result.descent_rate_avg_m_s,
            "descent_rate_min": competition_result.descent_rate_min_m_s,
            "descent_rate_max": competition_result.descent_rate_max_m_s,
            "landing_velocity": competition_result.landing_velocity_m_s,
            "telemetry_count": competition_result.telemetry_count,
            "issues": competition_result.issues,
        }

    # Print summary
    logger.info("")
    logger.info("--- FLIGHT SUMMARY ---")
    logger.info("  Duration:        %.1f s", results["flight_duration_s"])
    logger.info("  Telemetry:       %d samples", results["total_samples"])
    logger.info("  Max altitude:    %.1f m AGL", results["max_altitude_m"])
    logger.info("  Avg descent:     %.2f m/s", results["avg_descent_rate_m_s"])
    logger.info("  Phases:          %s", " -> ".join(p["phase"] for p in phase_log))

    if competition_result:
        logger.info("")
        if competition_result.valid:
            logger.info("  COMPETITION:     PASS")
        else:
            logger.info("  COMPETITION:     FAIL")
            for issue in competition_result.issues:
                logger.info("    - %s", issue)

    logger.info("")

    # Stop modules
    await registry.stop_all()

    return results


def main():
    parser = argparse.ArgumentParser(description="UniSat CanSat Flight Test Runner")
    parser.add_argument("--config", type=str, default=None,
                        help="Path to mission_config.json")
    parser.add_argument("--max-altitude", type=float, default=800.0,
                        help="Simulated max altitude in meters (default: 800)")
    parser.add_argument("--descent-rate", type=float, default=8.0,
                        help="Descent rate in m/s (default: 8.0)")
    parser.add_argument("--launch-delay", type=float, default=3.0,
                        help="Seconds before simulated launch (default: 3.0)")
    args = parser.parse_args()

    results = asyncio.run(run_cansat_test(
        config_path=args.config,
        max_altitude=args.max_altitude,
        descent_rate=args.descent_rate,
        launch_delay=args.launch_delay,
    ))

    # Exit with 0 if competition passed, 1 if failed
    comp = results.get("competition", {})
    sys.exit(0 if comp.get("valid", True) else 1)


if __name__ == "__main__":
    main()
