"""Task Scheduler for UniSat CubeSat.

Manages time-based, orbit-based, and event-based task scheduling with
a priority queue and configurable triggers.
"""

from __future__ import annotations

import heapq
import time
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, Callable, Coroutine

from modules import BaseModule, ModuleStatus


class TaskPriority(IntEnum):
    """Task priority levels (lower number = higher priority)."""

    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BACKGROUND = 4


class TriggerType:
    """Constants for trigger types."""

    TIME = "time"
    ORBIT = "orbit"
    EVENT = "event"
    PERIODIC = "periodic"


@dataclass(order=True)
class ScheduledTask:
    """A scheduled task in the priority queue.

    Attributes:
        priority: Task priority (lower = higher priority).
        trigger_time: Unix timestamp when the task should execute.
        task_id: Unique task identifier.
        name: Human-readable task name.
        callback: Async callable to execute.
        trigger_type: Type of trigger (time, orbit, event, periodic).
        interval_s: Repeat interval for periodic tasks (0 = one-shot).
        orbit_number: Target orbit number for orbit-triggered tasks.
        event_name: Event name for event-triggered tasks.
        enabled: Whether the task is active.
        last_run: Timestamp of last execution.
        run_count: Total execution count.
    """

    priority: TaskPriority
    trigger_time: float
    task_id: str = field(compare=False)
    name: str = field(compare=False)
    callback: Callable[..., Coroutine[Any, Any, None]] = field(compare=False, repr=False)
    trigger_type: str = field(compare=False, default=TriggerType.TIME)
    interval_s: float = field(compare=False, default=0.0)
    orbit_number: int = field(compare=False, default=0)
    event_name: str = field(compare=False, default="")
    enabled: bool = field(compare=False, default=True)
    last_run: float = field(compare=False, default=0.0)
    run_count: int = field(compare=False, default=0)


class TaskScheduler(BaseModule):
    """Priority-based task scheduler with multiple trigger types.

    Attributes:
        tasks: Dictionary of all registered tasks by ID.
        current_orbit: Current orbit number (updated externally).
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        """Initialize the task scheduler.

        Args:
            config: Optional configuration dict.
        """
        super().__init__("scheduler", config)
        self.tasks: dict[str, ScheduledTask] = {}
        self._queue: list[ScheduledTask] = []
        self._event_listeners: dict[str, list[str]] = {}
        self.current_orbit: int = 0
        self._running: bool = False
        self._executed_count: int = 0

    async def initialize(self) -> bool:
        """Initialize the scheduler.

        Returns:
            Always True.
        """
        self.status = ModuleStatus.READY
        self.logger.info("Task scheduler initialized")
        return True

    async def start(self) -> None:
        """Start the scheduler execution loop."""
        self._running = True
        self.status = ModuleStatus.RUNNING
        self.logger.info("Task scheduler started")

    async def stop(self) -> None:
        """Stop the scheduler."""
        self._running = False
        self.status = ModuleStatus.STOPPED
        self.logger.info("Scheduler stopped, %d tasks executed total", self._executed_count)

    async def get_status(self) -> dict[str, Any]:
        """Return scheduler status.

        Returns:
            Dict with task counts and scheduler state.
        """
        return {
            "status": self.status.name,
            "total_tasks": len(self.tasks),
            "pending_in_queue": len(self._queue),
            "executed_count": self._executed_count,
            "current_orbit": self.current_orbit,
            "error_count": self._error_count,
        }

    def add_time_task(self, task_id: str, name: str,
                      callback: Callable[..., Coroutine[Any, Any, None]],
                      trigger_time: float,
                      priority: TaskPriority = TaskPriority.NORMAL) -> None:
        """Schedule a one-shot task at a specific time.

        Args:
            task_id: Unique identifier.
            name: Human-readable name.
            callback: Async function to call.
            trigger_time: Unix timestamp to execute at.
            priority: Task priority.
        """
        task = ScheduledTask(
            priority=priority, trigger_time=trigger_time,
            task_id=task_id, name=name, callback=callback,
            trigger_type=TriggerType.TIME,
        )
        self.tasks[task_id] = task
        heapq.heappush(self._queue, task)
        self.logger.info("Added time task: %s at %.1f", name, trigger_time)

    def add_periodic_task(self, task_id: str, name: str,
                          callback: Callable[..., Coroutine[Any, Any, None]],
                          interval_s: float,
                          priority: TaskPriority = TaskPriority.NORMAL) -> None:
        """Schedule a repeating periodic task.

        Args:
            task_id: Unique identifier.
            name: Human-readable name.
            callback: Async function to call.
            interval_s: Repeat interval in seconds.
            priority: Task priority.
        """
        task = ScheduledTask(
            priority=priority, trigger_time=time.time() + interval_s,
            task_id=task_id, name=name, callback=callback,
            trigger_type=TriggerType.PERIODIC, interval_s=interval_s,
        )
        self.tasks[task_id] = task
        heapq.heappush(self._queue, task)
        self.logger.info("Added periodic task: %s every %.1fs", name, interval_s)

    def add_orbit_task(self, task_id: str, name: str,
                       callback: Callable[..., Coroutine[Any, Any, None]],
                       orbit_number: int,
                       priority: TaskPriority = TaskPriority.NORMAL) -> None:
        """Schedule a task to execute at a specific orbit.

        Args:
            task_id: Unique identifier.
            name: Human-readable name.
            callback: Async function to call.
            orbit_number: Orbit number to trigger at.
            priority: Task priority.
        """
        task = ScheduledTask(
            priority=priority, trigger_time=0.0,
            task_id=task_id, name=name, callback=callback,
            trigger_type=TriggerType.ORBIT, orbit_number=orbit_number,
        )
        self.tasks[task_id] = task
        self.logger.info("Added orbit task: %s at orbit %d", name, orbit_number)

    def add_event_task(self, task_id: str, name: str,
                       callback: Callable[..., Coroutine[Any, Any, None]],
                       event_name: str,
                       priority: TaskPriority = TaskPriority.HIGH) -> None:
        """Schedule a task triggered by a named event.

        Args:
            task_id: Unique identifier.
            name: Human-readable name.
            callback: Async function to call.
            event_name: Name of the event that triggers this task.
            priority: Task priority.
        """
        task = ScheduledTask(
            priority=priority, trigger_time=0.0,
            task_id=task_id, name=name, callback=callback,
            trigger_type=TriggerType.EVENT, event_name=event_name,
        )
        self.tasks[task_id] = task
        self._event_listeners.setdefault(event_name, []).append(task_id)
        self.logger.info("Added event task: %s on '%s'", name, event_name)

    async def fire_event(self, event_name: str) -> int:
        """Fire a named event, executing all registered listeners.

        Args:
            event_name: The event name to fire.

        Returns:
            Number of tasks executed.
        """
        task_ids = self._event_listeners.get(event_name, [])
        count = 0
        for tid in task_ids:
            task = self.tasks.get(tid)
            if task and task.enabled:
                await self._execute_task(task)
                count += 1
        return count

    async def tick(self) -> int:
        """Process all tasks that are due for execution.

        Should be called periodically from the main loop.

        Returns:
            Number of tasks executed this tick.
        """
        now = time.time()
        executed = 0
        orbit_tasks = [t for t in self.tasks.values()
                       if t.trigger_type == TriggerType.ORBIT
                       and t.orbit_number == self.current_orbit
                       and t.enabled and t.run_count == 0]
        for task in orbit_tasks:
            await self._execute_task(task)
            executed += 1
        while self._queue:
            if self._queue[0].trigger_time > now:
                break
            task = heapq.heappop(self._queue)
            if not task.enabled:
                continue
            await self._execute_task(task)
            executed += 1
            if task.trigger_type == TriggerType.PERIODIC and task.enabled:
                task.trigger_time = now + task.interval_s
                heapq.heappush(self._queue, task)
        return executed

    async def _execute_task(self, task: ScheduledTask) -> None:
        """Execute a single scheduled task.

        Args:
            task: The task to execute.
        """
        try:
            await task.callback()
            task.last_run = time.time()
            task.run_count += 1
            self._executed_count += 1
            self.logger.debug("Executed task: %s (#%d)", task.name, task.run_count)
        except Exception as exc:
            self.record_error(f"Task '{task.name}' failed: {exc}")

    def remove_task(self, task_id: str) -> bool:
        """Remove a task by ID.

        Args:
            task_id: The task identifier to remove.

        Returns:
            True if the task was found and removed.
        """
        task = self.tasks.pop(task_id, None)
        if task:
            task.enabled = False
            self.logger.info("Removed task: %s", task.name)
            return True
        return False
