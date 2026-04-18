"""HMAC key-rotation policy — ground-side scheduler.

Rotation on the firmware side is already fully implemented: the A/B
flash slots in :mod:`key_store` accept a rotate command that carries
``new_gen + new_key`` and atomically switches slots, rejecting any
stale generation replay.  What this module adds is the *policy*:
the decision of when a human operator should actually run that
rotation.

The policy is driven by the per-frame counter that ground ships in
the AX.25 authenticated frame (see ``ground-station/utils/
hmac_auth.py``).  Every frame consumes one counter value; once the
counter approaches the 32-bit ceiling, the same key MUST NOT be
used to sign any more frames — a second rotation with a fresh key
bumps the firmware's generation counter and resets the on-wire
counter back to 1.

Policy knobs
------------
``WARN_THRESHOLD_PCT``
    Operator-visible warning (orange chip in the configurator UI).
    Defaults to 50 % of counter space consumed: 2 147 483 648 frames.
``ROTATE_THRESHOLD_PCT``
    Hard rotation threshold.  The policy refuses to sign further
    frames past this limit so the counter can never exhaust.
    Defaults to 80 % of counter space: 3 435 973 836 frames.
``MAX_LIFETIME_DAYS``
    Calendar-based rotation ceiling.  Even a lightly-loaded key
    that has not burnt through its counter budget is rotated once
    a year to bound the blast radius of key compromise.  Set to 0
    to disable the time-based leg.
"""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

COUNTER_SPACE = 0xFFFFFFFF  # 2**32 - 1

WARN_THRESHOLD_PCT = 50
ROTATE_THRESHOLD_PCT = 80
MAX_LIFETIME_DAYS = 365


class KeyRotationError(RuntimeError):
    """Raised when the policy refuses to issue any more counter values."""


@dataclass
class KeyEpochState:
    """Per-key-generation bookkeeping.

    Attributes
    ----------
    generation
        The ``key_store`` generation integer.  Strictly increasing
        across rotations so a replayed rotation command cannot
        re-install an earlier key.
    activated_at
        UTC timestamp of the rotation that installed this key.
    counter_used
        How many authenticated frames have been signed with this
        key in the current session.  Persisted between operator
        sessions through :meth:`save` / :meth:`load`.
    """

    generation: int
    activated_at: datetime
    counter_used: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RotationDecision:
    """Answer to "can I sign another frame?".

    Attributes
    ----------
    allowed
        False means the caller must abort without sending.
    urgency
        ``"ok"``, ``"warn"``, or ``"rotate_now"``.
    reason
        Human-readable summary the ground console can display.
    """

    allowed: bool
    urgency: str
    reason: str


class KeyRotationPolicy:
    """Thread-safe policy that tracks counter usage and age.

    Typical use
    -----------

    .. code-block:: python

        policy = KeyRotationPolicy.load(Path("ground/state.json"))
        decision = policy.check_before_send()
        if not decision.allowed:
            raise KeyRotationError(decision.reason)
        frame = sender.seal(KEY, body)
        policy.record_sent(1)
        policy.save(Path("ground/state.json"))
    """

    def __init__(
        self,
        epoch: KeyEpochState,
        warn_threshold_pct: int = WARN_THRESHOLD_PCT,
        rotate_threshold_pct: int = ROTATE_THRESHOLD_PCT,
        max_lifetime_days: int = MAX_LIFETIME_DAYS,
    ) -> None:
        if not 0 < warn_threshold_pct < rotate_threshold_pct <= 100:
            raise ValueError(
                "thresholds must satisfy 0 < warn < rotate <= 100"
            )
        self._epoch = epoch
        self._warn = warn_threshold_pct
        self._rotate = rotate_threshold_pct
        self._max_days = max_lifetime_days
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    #  Introspection
    # ------------------------------------------------------------------

    @property
    def generation(self) -> int:
        return self._epoch.generation

    @property
    def counter_used(self) -> int:
        return self._epoch.counter_used

    @property
    def counter_pct(self) -> float:
        return self._epoch.counter_used * 100.0 / COUNTER_SPACE

    def age(self, now: datetime | None = None) -> timedelta:
        return (now or datetime.now(timezone.utc)) - self._epoch.activated_at

    # ------------------------------------------------------------------
    #  Decisions
    # ------------------------------------------------------------------

    def check_before_send(self, now: datetime | None = None) -> RotationDecision:
        """Decide whether the caller may sign another frame."""
        with self._lock:
            pct = self.counter_pct
            age_days = self.age(now).days

            if pct >= self._rotate:
                return RotationDecision(
                    allowed=False,
                    urgency="rotate_now",
                    reason=(
                        f"key generation {self.generation} has used "
                        f"{self._epoch.counter_used} / {COUNTER_SPACE} "
                        f"counter values ({pct:.2f} %) — rotate the key "
                        f"before sending any further frames"
                    ),
                )
            if self._max_days and age_days >= self._max_days:
                return RotationDecision(
                    allowed=False,
                    urgency="rotate_now",
                    reason=(
                        f"key generation {self.generation} was installed "
                        f"{age_days} days ago (max {self._max_days}); "
                        f"rotate to bound key compromise blast radius"
                    ),
                )
            if pct >= self._warn:
                return RotationDecision(
                    allowed=True,
                    urgency="warn",
                    reason=(
                        f"key generation {self.generation} is at "
                        f"{pct:.1f} % of counter space — schedule a "
                        f"rotation window"
                    ),
                )
            return RotationDecision(
                allowed=True,
                urgency="ok",
                reason=(
                    f"key generation {self.generation}: "
                    f"{self._epoch.counter_used} frames, {pct:.2f} %"
                ),
            )

    # ------------------------------------------------------------------
    #  Mutations
    # ------------------------------------------------------------------

    def record_sent(self, frames: int = 1) -> None:
        """Account ``frames`` counter values as consumed."""
        if frames < 0:
            raise ValueError(f"frames must be non-negative, got {frames}")
        with self._lock:
            self._epoch.counter_used += frames

    def rotate(
        self,
        new_generation: int,
        now: datetime | None = None,
    ) -> KeyEpochState:
        """Record a successful key rotation.

        Call after ``key_store_rotate`` on the firmware has acked the
        rotation. Returns the retired epoch state for audit logging.

        Raises
        ------
        ValueError
            If ``new_generation`` is not strictly greater than the
            current generation — matching the firmware's contract.
        """
        with self._lock:
            if new_generation <= self._epoch.generation:
                raise ValueError(
                    f"new generation {new_generation} must exceed current "
                    f"{self._epoch.generation}"
                )
            retired = KeyEpochState(
                generation=self._epoch.generation,
                activated_at=self._epoch.activated_at,
                counter_used=self._epoch.counter_used,
                metadata=dict(self._epoch.metadata),
            )
            self._epoch = KeyEpochState(
                generation=new_generation,
                activated_at=now or datetime.now(timezone.utc),
                counter_used=0,
            )
            return retired

    # ------------------------------------------------------------------
    #  Persistence
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        return {
            "generation": self._epoch.generation,
            "activated_at": self._epoch.activated_at.isoformat(),
            "counter_used": self._epoch.counter_used,
            "metadata": dict(self._epoch.metadata),
            "warn_threshold_pct": self._warn,
            "rotate_threshold_pct": self._rotate,
            "max_lifetime_days": self._max_days,
        }

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> KeyRotationPolicy:
        epoch = KeyEpochState(
            generation=int(payload["generation"]),
            activated_at=datetime.fromisoformat(payload["activated_at"]),
            counter_used=int(payload.get("counter_used", 0)),
            metadata=dict(payload.get("metadata") or {}),
        )
        return cls(
            epoch,
            warn_threshold_pct=int(
                payload.get("warn_threshold_pct", WARN_THRESHOLD_PCT)
            ),
            rotate_threshold_pct=int(
                payload.get("rotate_threshold_pct", ROTATE_THRESHOLD_PCT)
            ),
            max_lifetime_days=int(
                payload.get("max_lifetime_days", MAX_LIFETIME_DAYS)
            ),
        )

    @classmethod
    def load(cls, path: Path) -> KeyRotationPolicy:
        return cls.from_dict(json.loads(path.read_text(encoding="utf-8")))
