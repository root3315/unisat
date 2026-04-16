"""UniSat core framework — mission-agnostic architecture components.

Provides the event bus, state machine, module registry, and mission type
definitions that allow UniSat to support CubeSat, CanSat, rocket, HAB,
drone, and other aerospace platforms from a single codebase.
"""

from core.mission_types import MissionType, PlatformCategory
from core.event_bus import EventBus, Event
from core.state_machine import StateMachine, MissionPhase
from core.module_registry import ModuleRegistry

__all__ = [
    "MissionType",
    "PlatformCategory",
    "EventBus",
    "Event",
    "StateMachine",
    "MissionPhase",
    "ModuleRegistry",
]
