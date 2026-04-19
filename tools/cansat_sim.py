"""Pure-Python CanSat flight simulator.

Extracted from ``playground.py`` so it can be imported and tested
without pulling Streamlit in. Mirrors the dynamics model in
``flight-software/run_cansat.py``.
"""

from __future__ import annotations

import random


def simulate_cansat_flight(
    max_altitude_m: float,
    target_descent_rate_ms: float,
    dt: float = 0.1,
) -> list[dict]:
    """Run a minimal SITL flight and return a plottable trajectory.

    Produces samples of the form
    ``{"t": float, "altitude_m": float, "velocity_ms": float,
    "phase": str}``. Phases go through ``ascent → apogee → descent →
    landed`` just like the full flight controller.

    Args:
        max_altitude_m: Peak altitude the vehicle reaches (m).
        target_descent_rate_ms: Parachute descent rate (m/s).
        dt: Integration step (s). Smaller = more samples.

    Returns:
        Ordered list of trajectory samples.
    """
    samples: list[dict] = []
    t = 0.0
    altitude = 0.0
    velocity = 0.0
    # Rough boost accel that reaches max_alt in ~5 s
    ascent_a = max_altitude_m / 25.0
    descent_v = -target_descent_rate_ms

    # Ascent
    phase = "ascent"
    while altitude < max_altitude_m:
        velocity += ascent_a * dt
        altitude += velocity * dt - 0.5 * 9.81 * dt * dt
        if velocity <= 0:
            break
        samples.append({
            "t": round(t, 2),
            "altitude_m": round(altitude, 2),
            "velocity_ms": round(velocity, 2),
            "phase": phase,
        })
        t += dt

    # Apogee
    phase = "apogee"
    samples.append({
        "t": round(t, 2),
        "altitude_m": round(altitude, 2),
        "velocity_ms": 0.0,
        "phase": phase,
    })
    t += 0.5

    # Parachute descent at target rate (with light jitter)
    phase = "descent"
    while altitude > 0:
        altitude += descent_v * dt
        samples.append({
            "t": round(t, 2),
            "altitude_m": round(max(altitude, 0), 2),
            "velocity_ms": descent_v + random.uniform(-0.3, 0.3),
            "phase": phase,
        })
        t += dt

    samples.append({
        "t": round(t, 2),
        "altitude_m": 0.0,
        "velocity_ms": 0.0,
        "phase": "landed",
    })
    return samples


def average_descent_rate(samples: list[dict]) -> float:
    """Mean |vertical velocity| across the descent phase."""
    rows = [s for s in samples if s["phase"] == "descent"][:-1]
    if not rows:
        return 0.0
    return abs(sum(s["velocity_ms"] for s in rows) / len(rows))
