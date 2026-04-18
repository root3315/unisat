"""Configurable State Machine — Mission-phase management.

Unlike the old hardcoded 4-state enum, this state machine loads phase
definitions from a MissionProfile and supports:
- Validated transitions (only allowed next-phases)
- Timeout-based auto-transitions
- Event-driven transitions via the EventBus
- Per-phase module enable/disable
- Transition guards (async callables that can veto a transition)
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine

from core.mission_types import MissionProfile, PhaseDefinition

logger = logging.getLogger("unisat.state_machine")

# Transition guard: async callable returning True to allow transition
TransitionGuard = Callable[[str, str], Coroutine[Any, Any, bool]]


@dataclass
class MissionPhase:
    """Runtime state for the current mission phase.

    Attributes:
        definition: The phase definition from the mission profile.
        entered_at: Unix timestamp when this phase was entered.
        transition_count: How many times we've entered this phase.
    """

    definition: PhaseDefinition
    entered_at: float = field(default_factory=time.time)
    transition_count: int = 0


@dataclass
class TransitionRecord:
    """Record of a state transition for logging/telemetry."""

    from_phase: str
    to_phase: str
    timestamp: float
    reason: str = ""


class StateMachine:
    """Configurable mission state machine.

    Loads phases from a MissionProfile, validates transitions, and emits
    events on the EventBus when phases change.

    Attributes:
        current: The current MissionPhase.
        profile: The active mission profile.
        history: List of transition records.
    """

    def __init__(self, profile: MissionProfile) -> None:
        """Initialize from a mission profile.

        Args:
            profile: The mission profile defining phases and transitions.
        """
        self.profile = profile
        self._phases: dict[str, PhaseDefinition] = {
            p.name: p for p in profile.phases
        }
        self._guards: list[TransitionGuard] = []
        self.history: list[TransitionRecord] = []

        initial = self._phases.get(profile.initial_phase)
        if not initial:
            raise ValueError(
                f"Initial phase '{profile.initial_phase}' not found in profile. "
                f"Available: {list(self._phases.keys())}"
            )
        self.current = MissionPhase(definition=initial)
        logger.info("State machine initialized, phase: %s", self.current.definition.name)

    @property
    def phase_name(self) -> str:
        """Current phase name."""
        return self.current.definition.name

    @property
    def phase_display(self) -> str:
        """Current phase display name."""
        return self.current.definition.display_name

    def add_guard(self, guard: TransitionGuard) -> None:
        """Register a transition guard.

        Args:
            guard: Async callable(from_phase, to_phase) -> bool.
        """
        self._guards.append(guard)

    async def transition_to(self, target_phase: str, reason: str = "") -> bool:
        """Attempt to transition to a new phase.

        Args:
            target_phase: Name of the target phase.
            reason: Human-readable reason for the transition.

        Returns:
            True if the transition succeeded.
        """
        current_name = self.current.definition.name

        if target_phase == current_name:
            return True

        if target_phase not in self._phases:
            logger.error("Unknown phase: '%s'", target_phase)
            return False

        allowed = self.current.definition.transitions_to
        if allowed and target_phase not in allowed:
            logger.warning(
                "Transition %s -> %s not allowed (allowed: %s)",
                current_name, target_phase, allowed,
            )
            return False

        # Run guards
        for guard in self._guards:
            try:
                ok = await guard(current_name, target_phase)
                if not ok:
                    logger.info("Guard vetoed transition %s -> %s", current_name, target_phase)
                    return False
            except Exception as exc:
                logger.error("Guard error: %s", exc)
                return False

        # Perform transition
        target_def = self._phases[target_phase]
        record = TransitionRecord(
            from_phase=current_name,
            to_phase=target_phase,
            timestamp=time.time(),
            reason=reason,
        )
        self.history.append(record)

        old_phase = self.current
        self.current = MissionPhase(
            definition=target_def,
            transition_count=old_phase.transition_count + 1,
        )

        logger.info(
            "Phase transition: %s -> %s (reason: %s)",
            current_name, target_phase, reason or "manual",
        )
        return True

    def check_timeout(self) -> str | None:
        """Check if the current phase has timed out.

        Returns:
            The auto-next phase name if timed out, None otherwise.
        """
        defn = self.current.definition
        if defn.timeout_s <= 0 or not defn.auto_next:
            return None
        elapsed = time.time() - self.current.entered_at
        if elapsed >= defn.timeout_s:
            return defn.auto_next
        return None

    def get_elapsed(self) -> float:
        """Seconds spent in the current phase."""
        return time.time() - self.current.entered_at

    def get_available_transitions(self) -> list[str]:
        """Return list of phases the current phase can transition to."""
        return list(self.current.definition.transitions_to)

    def get_phase_info(self) -> dict[str, Any]:
        """Return a telemetry-friendly dict of current state."""
        return {
            "phase": self.current.definition.name,
            "display_name": self.current.definition.display_name,
            "elapsed_s": round(self.get_elapsed(), 1),
            "transitions_to": self.current.definition.transitions_to,
            "timeout_s": self.current.definition.timeout_s,
            "auto_next": self.current.definition.auto_next,
            "transition_count": self.current.transition_count,
            "required_modules": self.current.definition.required_modules,
            "disabled_modules": self.current.definition.disabled_modules,
        }

    def list_phases(self) -> list[dict[str, Any]]:
        """Return summary of all defined phases."""
        return [
            {
                "name": p.name,
                "display_name": p.display_name,
                "transitions_to": p.transitions_to,
                "timeout_s": p.timeout_s,
            }
            for p in self.profile.phases
        ]
