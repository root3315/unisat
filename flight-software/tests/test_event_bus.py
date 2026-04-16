"""Tests for the EventBus — async pub/sub system."""

import asyncio
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.event_bus import EventBus, Event


@pytest.fixture
def bus():
    return EventBus(history_size=100)


@pytest.mark.asyncio
async def test_exact_match(bus):
    """Events are delivered to exact-match subscribers."""
    received = []

    async def handler(event: Event):
        received.append(event)

    bus.subscribe("test.event", handler)
    await bus.emit("test.event", data={"key": "value"})

    assert len(received) == 1
    assert received[0].name == "test.event"
    assert received[0].data["key"] == "value"


@pytest.mark.asyncio
async def test_wildcard_match(bus):
    """Wildcard patterns match all child events."""
    received = []

    async def handler(event: Event):
        received.append(event.name)

    bus.subscribe("phase.*", handler)
    await bus.emit("phase.ascent.enter")
    await bus.emit("phase.descent.enter")
    await bus.emit("system.init")  # should NOT match

    assert received == ["phase.ascent.enter", "phase.descent.enter"]


@pytest.mark.asyncio
async def test_global_wildcard(bus):
    """Global wildcard '*' matches everything."""
    received = []

    async def handler(event: Event):
        received.append(event.name)

    bus.subscribe("*", handler)
    await bus.emit("a.b.c")
    await bus.emit("x")

    assert len(received) == 2


@pytest.mark.asyncio
async def test_no_match(bus):
    """Events with no matching subscribers are silently ignored."""
    count = await bus.emit("unsubscribed.event")
    assert count == 0


@pytest.mark.asyncio
async def test_handler_error_does_not_propagate(bus):
    """A failing handler doesn't break other handlers."""
    results = []

    async def bad_handler(event: Event):
        raise ValueError("boom")

    async def good_handler(event: Event):
        results.append("ok")

    bus.subscribe("test", bad_handler)
    bus.subscribe("test", good_handler)

    count = await bus.emit("test")
    assert count == 1  # only good_handler succeeded
    assert results == ["ok"]


@pytest.mark.asyncio
async def test_history(bus):
    """Event history is maintained up to the configured size."""
    for i in range(10):
        await bus.emit(f"event.{i}")

    history = bus.get_history(limit=5)
    assert len(history) == 5
    assert history[0].name == "event.9"  # newest first


@pytest.mark.asyncio
async def test_history_filtered(bus):
    """History can be filtered by pattern."""
    await bus.emit("phase.ascent")
    await bus.emit("system.init")
    await bus.emit("phase.descent")

    phase_events = bus.get_history(pattern="phase.*")
    assert len(phase_events) == 2


@pytest.mark.asyncio
async def test_unsubscribe(bus):
    """Unsubscribed handlers stop receiving events."""
    received = []

    async def handler(event: Event):
        received.append(event.name)

    bus.subscribe("test", handler)
    await bus.emit("test")
    assert len(received) == 1

    bus.unsubscribe("test", handler)
    await bus.emit("test")
    assert len(received) == 1  # no new events


@pytest.mark.asyncio
async def test_stats(bus):
    """Event stats track counts correctly."""
    await bus.emit("a")
    await bus.emit("a")
    await bus.emit("b")

    stats = bus.get_stats()
    assert stats["total_events"] == 3
    assert stats["unique_events"] == 2


@pytest.mark.asyncio
async def test_event_data_and_source(bus):
    """Events carry data and source metadata."""
    received = []

    async def handler(event: Event):
        received.append(event)

    bus.subscribe("test", handler)
    await bus.emit("test", data={"x": 42}, source="my_module", priority=1)

    assert received[0].data["x"] == 42
    assert received[0].source == "my_module"
    assert received[0].priority == 1
