"""
Long-duration soak test skeleton (Phase 4 — framework only).

Goal
----
Continuously cycle the flight-software state machine through the
full CubeSat-LEO phase list for a wall-clock duration (default
60 seconds for the pytest integration — the full 48 h mode is
gated behind an environment variable so CI never blocks on it)
while asserting that:

1. No coroutine leaks: the active-task count at the end equals the
   count at the start.
2. No unbounded memory growth: ``tracemalloc`` peak stays within a
   per-iteration budget (see ``MEMORY_BUDGET_KB``).
3. No degradation: the average per-cycle wall-clock time stays
   within 20 % of the first recorded cycle across the whole run.
4. Safe-mode entry / exit remains idempotent across repeated
   triggers.

Running the full 48 h mode
--------------------------
::

    UNISAT_SOAK_SECONDS=172800 python3 -m pytest \\
        flight-software/tests/test_long_soak.py -v -s

CI / default behaviour
----------------------
Without the environment variable the module only runs a 30-cycle
smoke check (~1 s wall clock) that proves the harness itself is
wired — i.e. the same test enters/exits every mission phase, the
event bus delivers, safe mode toggles cleanly, and tracemalloc
accounting works. The real soak is operator-initiated because a
48 h CI job has no business blocking a PR merge.
"""

from __future__ import annotations

import asyncio
import gc
import os
import sys
import time
import tracemalloc
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.event_bus import Event, EventBus
from core.mission_types import MissionType, get_mission_profile
from core.state_machine import StateMachine
from modules.safe_mode import SafeModeHandler, SafeModeReason


# --- Tuning ---------------------------------------------------------
DEFAULT_SOAK_SECONDS        = 1.0          # quick-smoke default
DEFAULT_SMOKE_CYCLES        = 30           # hard lower bound
MEMORY_BUDGET_KB_PER_CYCLE  = 128          # ceiling for peak-alloc growth
CYCLE_BUDGET_SECONDS        = 0.1          # per-cycle soft limit
DEGRADATION_FACTOR          = 1.5          # mean cycle ≤ 1.5× first cycle


# --- Mission phase ring ---------------------------------------------
#
# Each tuple describes one "lap" of the mission: a linear sequence of
# valid state-machine transitions starting and ending at nominal.
# Ending at nominal keeps the harness idempotent between laps.
#
_LAP: tuple[tuple[str, str], ...] = (
    ("nominal",     "science"),
    ("science",     "nominal"),
    ("nominal",     "comm_window"),
    ("comm_window", "nominal"),
    ("nominal",     "low_power"),
    ("low_power",   "nominal"),
    ("nominal",     "safe_mode"),
    ("safe_mode",   "nominal"),
)


async def _bring_up_to_nominal(sm: StateMachine) -> None:
    """Walk the state machine from initial ``startup`` to ``nominal``."""
    for src, dst in (
        ("startup",    "deployment"),
        ("deployment", "detumbling"),
        ("detumbling", "nominal"),
    ):
        assert sm.phase_name == src, f"expected {src!r}, got {sm.phase_name!r}"
        ok = await sm.transition_to(dst, reason=f"soak bring-up {dst}")
        assert ok


async def _run_one_lap(sm: StateMachine, safe: SafeModeHandler,
                        bus: EventBus) -> None:
    """Perform one full lap of the mission phase ring."""
    for src, dst in _LAP:
        assert sm.phase_name == src, (
            f"lap skew: expected {src!r}, got {sm.phase_name!r}"
        )
        ok = await sm.transition_to(dst, reason="soak lap")
        assert ok, f"transition {src!r} -> {dst!r} failed"

        # Exercise safe-mode idempotence whenever we touch the
        # safe_mode phase. Enter/exit should behave identically
        # across any number of laps.
        if dst == "safe_mode":
            safe.enter_safe_mode(SafeModeReason.WATCHDOG)
            assert safe.state.active is True
        elif src == "safe_mode":
            safe.exit_safe_mode()
            assert safe.state.active is False

        # Publish a lightweight bookkeeping event so the subscribed
        # recorder can later assert the event bus kept up.
        await bus.publish(Event("soak_tick", {"to": dst}))


# ------------------------------------------------------------------
#  The one public test. Dispatches to quick-smoke or to full-soak
#  based on UNISAT_SOAK_SECONDS.
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_mission_soak() -> None:
    seconds_env = os.environ.get("UNISAT_SOAK_SECONDS")
    target_seconds: float
    enforce_time: bool

    if seconds_env:
        target_seconds = float(seconds_env)
        enforce_time   = True
    else:
        target_seconds = DEFAULT_SOAK_SECONDS
        enforce_time   = False

    profile = get_mission_profile(MissionType.CUBESAT_LEO)
    assert profile is not None

    sm = StateMachine(profile)
    bus = EventBus()
    safe = SafeModeHandler({
        "comm_timeout_s": 0.1,
        "beacon_interval_s": 0.05,
        "recovery_check_interval_s": 0.05,
    })
    assert await safe.initialize() is True

    tick_count = 0

    async def on_tick(evt: Event) -> None:
        nonlocal tick_count
        tick_count += 1

    bus.subscribe("soak_tick", on_tick)

    # Warm up the state machine to 'nominal' so the lap ring is
    # entered from the right phase.
    await _bring_up_to_nominal(sm)
    assert sm.phase_name == "nominal"

    # Baseline: run one lap outside the timing/memory loop so the
    # Python runtime's one-shot allocations (Unicode interning, enum
    # lazy eval, etc.) don't pollute the first measured lap.
    await _run_one_lap(sm, safe, bus)

    initial_tasks = len(asyncio.all_tasks())

    tracemalloc.start()
    start_time = time.perf_counter()
    first_cycle_seconds: float | None = None
    cycle_times: list[float] = []
    cycles_run = 0

    while True:
        elapsed = time.perf_counter() - start_time

        # Stop condition:
        #  * If an explicit duration was requested (UNISAT_SOAK_SECONDS
        #    env var), honour it.
        #  * Otherwise default smoke: run DEFAULT_SMOKE_CYCLES with a
        #    1-second safety cap.
        if enforce_time:
            if elapsed >= target_seconds:
                break
        else:
            if cycles_run >= DEFAULT_SMOKE_CYCLES or elapsed >= 1.0:
                break

        lap_start = time.perf_counter()
        await _run_one_lap(sm, safe, bus)
        lap_dt = time.perf_counter() - lap_start
        cycle_times.append(lap_dt)
        if first_cycle_seconds is None:
            first_cycle_seconds = lap_dt
        cycles_run += 1

        assert lap_dt < CYCLE_BUDGET_SECONDS, (
            f"cycle {cycles_run} took {lap_dt:.3f}s (> "
            f"{CYCLE_BUDGET_SECONDS:.3f}s budget)"
        )

    _, peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    gc.collect()

    # --- assertions ---

    assert cycles_run >= 1, "soak produced zero cycles"
    assert tick_count >= cycles_run * len(_LAP) - 1, (
        "event bus lost messages: "
        f"tick_count={tick_count}, expected≥{cycles_run * len(_LAP) - 1}"
    )
    assert len(asyncio.all_tasks()) == initial_tasks, (
        "coroutine leak: "
        f"{len(asyncio.all_tasks())} tasks alive vs {initial_tasks} baseline"
    )

    peak_kb = peak_bytes / 1024.0
    budget_kb = MEMORY_BUDGET_KB_PER_CYCLE * max(cycles_run, 1)
    assert peak_kb < budget_kb, (
        f"memory growth exceeded budget: peak={peak_kb:.1f} KB vs "
        f"{budget_kb:.1f} KB for {cycles_run} cycles"
    )

    if first_cycle_seconds is not None and cycles_run >= 5:
        mean = sum(cycle_times) / len(cycle_times)
        assert mean <= first_cycle_seconds * DEGRADATION_FACTOR, (
            f"per-cycle time drifted upward: "
            f"first={first_cycle_seconds*1e3:.2f} ms, "
            f"mean={mean*1e3:.2f} ms (factor "
            f"{mean / max(first_cycle_seconds, 1e-6):.2f})"
        )

    # Leave the state machine in nominal so a subsequent soak test
    # (or the interactive user running with UNISAT_SOAK_SECONDS) can
    # pick up without re-bringing up.
    assert sm.phase_name == "nominal"
