"""Event Bus — Async publish/subscribe for inter-module communication.

Modules publish events (state changes, sensor triggers, errors) and other
modules subscribe to those events. This decouples modules from each other
and enables mission-phase-driven behaviour without hard dependencies.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine

logger = logging.getLogger("unisat.events")

# Type alias for event handlers
EventHandler = Callable[["Event"], Coroutine[Any, Any, None]]


@dataclass
class Event:
    """A single event on the bus.

    Attributes:
        name: Dot-separated event name (e.g. "phase.ascent.enter").
        data: Arbitrary payload dict.
        source: Name of the module that published the event.
        timestamp: Unix timestamp of event creation.
        priority: Lower = higher priority (0 = critical).
    """

    name: str
    data: dict[str, Any] = field(default_factory=dict)
    source: str = ""
    timestamp: float = field(default_factory=time.time)
    priority: int = 5


class EventBus:
    """Async event bus with wildcard subscriptions and history.

    Supports:
    - Exact match: ``"phase.ascent.enter"``
    - Wildcard: ``"phase.*"`` matches any event starting with ``phase.``
    - Global: ``"*"`` matches everything
    """

    def __init__(self, history_size: int = 500) -> None:
        self._handlers: dict[str, list[EventHandler]] = {}
        self._history: list[Event] = []
        self._history_size = history_size
        self._event_counts: dict[str, int] = {}

    def subscribe(self, pattern: str, handler: EventHandler) -> None:
        """Subscribe a handler to events matching a pattern.

        Args:
            pattern: Event name or wildcard pattern.
            handler: Async callable receiving an Event.
        """
        self._handlers.setdefault(pattern, []).append(handler)
        logger.debug("Subscribed to '%s': %s", pattern, handler.__qualname__)

    def unsubscribe(self, pattern: str, handler: EventHandler) -> None:
        """Remove a specific handler from a pattern.

        Args:
            pattern: The pattern originally subscribed to.
            handler: The handler to remove.
        """
        handlers = self._handlers.get(pattern, [])
        if handler in handlers:
            handlers.remove(handler)

    async def publish(self, event: Event) -> int:
        """Publish an event, calling all matching handlers.

        Args:
            event: The event to publish.

        Returns:
            Number of handlers invoked.
        """
        self._history.append(event)
        if len(self._history) > self._history_size:
            self._history = self._history[-self._history_size:]
        self._event_counts[event.name] = self._event_counts.get(event.name, 0) + 1

        handlers = self._matching_handlers(event.name)
        count = 0
        for handler in handlers:
            try:
                await handler(event)
                count += 1
            except Exception as exc:
                logger.error(
                    "Handler %s failed for event '%s': %s",
                    handler.__qualname__, event.name, exc,
                )
        logger.debug("Published '%s' -> %d handlers", event.name, count)
        return count

    async def emit(self, name: str, data: dict[str, Any] | None = None,
                   source: str = "", priority: int = 5) -> int:
        """Convenience method to create and publish an event in one call.

        Args:
            name: Event name.
            data: Optional payload dict.
            source: Source module name.
            priority: Event priority.

        Returns:
            Number of handlers invoked.
        """
        event = Event(name=name, data=data or {}, source=source, priority=priority)
        return await self.publish(event)

    def _matching_handlers(self, event_name: str) -> list[EventHandler]:
        """Find all handlers whose pattern matches an event name."""
        matched: list[EventHandler] = []
        for pattern, handlers in self._handlers.items():
            if self._pattern_matches(pattern, event_name):
                matched.extend(handlers)
        return matched

    @staticmethod
    def _pattern_matches(pattern: str, event_name: str) -> bool:
        """Check if a subscription pattern matches an event name.

        Rules:
        - ``"*"`` matches everything.
        - ``"foo.*"`` matches ``"foo.bar"``, ``"foo.bar.baz"``, etc.
        - ``"foo.bar"`` matches only ``"foo.bar"`` exactly.
        """
        if pattern == "*":
            return True
        if pattern.endswith(".*"):
            prefix = pattern[:-2]
            return event_name == prefix or event_name.startswith(prefix + ".")
        return pattern == event_name

    def get_history(self, pattern: str | None = None, limit: int = 50) -> list[Event]:
        """Return recent events, optionally filtered by pattern.

        Args:
            pattern: Optional filter pattern.
            limit: Max number of events to return.

        Returns:
            List of matching events, newest first.
        """
        events = self._history
        if pattern:
            events = [e for e in events if self._pattern_matches(pattern, e.name)]
        return list(reversed(events[-limit:]))

    def get_stats(self) -> dict[str, Any]:
        """Return event bus statistics."""
        return {
            "total_events": sum(self._event_counts.values()),
            "unique_events": len(self._event_counts),
            "subscriber_patterns": len(self._handlers),
            "history_size": len(self._history),
            "top_events": dict(
                sorted(self._event_counts.items(), key=lambda x: -x[1])[:10]
            ),
        }
