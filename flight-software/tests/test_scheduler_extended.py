"""Extended scheduler coverage — add_*_task + tick + remove paths."""

from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.scheduler import TaskScheduler as Scheduler, TaskPriority, TriggerType


@pytest.fixture
def scheduler() -> Scheduler:
    return Scheduler()


async def _noop() -> None:
    return None


@pytest.mark.asyncio
async def test_initialize_and_start_cycle(scheduler: Scheduler) -> None:
    assert await scheduler.initialize() is True
    await scheduler.start()
    await scheduler.stop()


@pytest.mark.asyncio
async def test_get_status_keys(scheduler: Scheduler) -> None:
    await scheduler.initialize()
    status = await scheduler.get_status()
    assert "status" in status


@pytest.mark.asyncio
async def test_add_time_task(scheduler: Scheduler) -> None:
    await scheduler.initialize()
    future = time.time() + 60.0
    scheduler.add_time_task(
        task_id="t1",
        name="test",
        trigger_time=future,
        callback=_noop,
        priority=TaskPriority.NORMAL,
    )
    assert "t1" in scheduler.tasks


@pytest.mark.asyncio
async def test_add_periodic_task(scheduler: Scheduler) -> None:
    await scheduler.initialize()
    scheduler.add_periodic_task(
        task_id="p1",
        name="periodic",
        interval_s=10.0,
        callback=_noop,
    )
    assert "p1" in scheduler.tasks


@pytest.mark.asyncio
async def test_add_orbit_task(scheduler: Scheduler) -> None:
    await scheduler.initialize()
    scheduler.add_orbit_task(
        task_id="o1",
        name="orbit",
        orbit_number=100,
        callback=_noop,
    )
    assert "o1" in scheduler.tasks


@pytest.mark.asyncio
async def test_add_event_task(scheduler: Scheduler) -> None:
    await scheduler.initialize()
    scheduler.add_event_task(
        task_id="e1",
        name="event",
        event_name="SUNRISE",
        callback=_noop,
    )
    assert "e1" in scheduler.tasks


@pytest.mark.asyncio
async def test_remove_task_returns_true_if_present(scheduler: Scheduler) -> None:
    await scheduler.initialize()
    scheduler.add_periodic_task(
        task_id="r1",
        name="to-remove",
        interval_s=1.0,
        callback=_noop,
    )
    assert scheduler.remove_task("r1") is True


@pytest.mark.asyncio
async def test_remove_task_returns_false_if_absent(scheduler: Scheduler) -> None:
    await scheduler.initialize()
    assert scheduler.remove_task("never-added") is False


@pytest.mark.asyncio
async def test_tick_fires_due_tasks(scheduler: Scheduler) -> None:
    """A task whose trigger_time is in the past must execute on tick."""
    await scheduler.initialize()
    scheduler.add_time_task(
        task_id="fire",
        name="fire-now",
        trigger_time=time.time() - 1.0,   # already due
        callback=_noop,
    )
    executed = await scheduler.tick()
    assert executed >= 1


@pytest.mark.asyncio
async def test_tick_does_not_fire_future_tasks(scheduler: Scheduler) -> None:
    """A task whose trigger_time is in the future stays queued."""
    await scheduler.initialize()
    scheduler.add_time_task(
        task_id="future",
        name="wait",
        trigger_time=time.time() + 3600.0,
        callback=_noop,
    )
    executed = await scheduler.tick()
    assert executed == 0


@pytest.mark.asyncio
async def test_fire_event_delivers_to_subscribers(scheduler: Scheduler) -> None:
    await scheduler.initialize()
    fired_count = {"n": 0}

    async def on_event() -> None:
        fired_count["n"] += 1

    scheduler.add_event_task(
        task_id="sub",
        name="subscriber",
        event_name="TEST_EVENT",
        callback=on_event,
    )
    n = await scheduler.fire_event("TEST_EVENT")
    assert n >= 1
    assert fired_count["n"] >= 1


@pytest.mark.asyncio
async def test_fire_unknown_event_zero(scheduler: Scheduler) -> None:
    await scheduler.initialize()
    n = await scheduler.fire_event("NO_SUBSCRIBERS")
    assert n == 0


def test_task_priority_ordering() -> None:
    assert TaskPriority.CRITICAL < TaskPriority.HIGH
    assert TaskPriority.HIGH < TaskPriority.NORMAL
    assert TaskPriority.NORMAL < TaskPriority.LOW


def test_trigger_type_constants_exist() -> None:
    assert TriggerType.TIME == "time"
    assert TriggerType.PERIODIC == "periodic"
    assert TriggerType.ORBIT == "orbit"
    assert TriggerType.EVENT == "event"
