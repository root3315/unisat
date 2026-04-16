"""
Safe Mode Handler — Emergency autonomous operation.

Activates when communication is lost for a configurable timeout or when
critical system failures are detected. Disables non-essential subsystems
and enters beacon-only mode. Timeout and parameters are configurable
per mission type.
"""

import time
from dataclasses import dataclass
from enum import Enum
from typing import Any

from modules import BaseModule, ModuleStatus


class SafeModeReason(Enum):
    """Reasons for entering safe mode."""

    COMM_LOSS = "communication_loss"
    LOW_BATTERY = "low_battery"
    THERMAL_LIMIT = "thermal_limit"
    WATCHDOG = "watchdog_timeout"
    MANUAL = "manual_command"


@dataclass
class SafeModeState:
    """Current safe mode status.

    Attributes:
        active: Whether safe mode is currently active.
        reason: Reason safe mode was entered.
        entered_at: Unix timestamp when safe mode started.
        duration_s: Time spent in safe mode.
        beacon_count: Number of beacons transmitted.
        recovery_attempts: Number of recovery attempts made.
    """

    active: bool = False
    reason: SafeModeReason | None = None
    entered_at: float = 0.0
    duration_s: float = 0.0
    beacon_count: int = 0
    recovery_attempts: int = 0


class SafeModeHandler(BaseModule):
    """Manages satellite safe mode transitions and recovery.

    Attributes:
        state: Current safe mode state.
        comm_timeout_s: Seconds without comms before entering safe mode.
        beacon_interval_s: Seconds between beacon transmissions.
        max_recovery_attempts: Max attempts before giving up recovery.
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        """Initialize safe mode handler.

        Args:
            config: Configuration with optional timeout and beacon overrides.
        """
        super().__init__("safe_mode", config)
        self.comm_timeout_s: float = self.config.get("comm_timeout_s", 86400)
        self.beacon_interval_s: float = self.config.get("beacon_interval_s", 30)
        self.max_recovery_attempts: int = self.config.get("max_recovery_attempts", 5)
        self._recovery_check_interval_s: float = self.config.get(
            "recovery_check_interval_s", 3600
        )
        self.state = SafeModeState()
        self._last_comm_time = time.time()
        self._last_beacon_time = 0.0
        self._last_recovery_check = 0.0
        self._disabled_subsystems: list[str] = []

    async def initialize(self) -> bool:
        """Initialize the safe mode handler.

        Returns:
            True on success.
        """
        self._last_comm_time = time.time()
        self.logger.info(
            "Safe mode initialized: comm_timeout=%ds, beacon=%ds",
            int(self.comm_timeout_s),
            int(self.beacon_interval_s),
        )
        self.status = ModuleStatus.READY
        return True

    async def start(self) -> None:
        """Start the safe mode handler."""
        self.status = ModuleStatus.RUNNING

    async def stop(self) -> None:
        """Stop the safe mode handler."""
        self.status = ModuleStatus.STOPPED

    async def get_status(self) -> dict[str, Any]:
        """Return safe mode handler status.

        Returns:
            Dict with safe mode state and configuration.
        """
        return {
            "status": self.status.name,
            "safe_mode_active": self.state.active,
            "reason": self.state.reason.value if self.state.reason else None,
            "duration_s": round(self.state.duration_s, 1),
            "beacon_count": self.state.beacon_count,
            "recovery_attempts": self.state.recovery_attempts,
            "disabled_subsystems": list(self._disabled_subsystems),
            "error_count": self._error_count,
        }

    def update_comm_timestamp(self) -> None:
        """Call when valid communication is received."""
        self._last_comm_time = time.time()
        if self.state.active and self.state.reason == SafeModeReason.COMM_LOSS:
            self.logger.info("Communication restored — attempting recovery")
            self._attempt_recovery()

    def check_comm_timeout(self) -> bool:
        """Check if communication has been lost too long.

        Returns:
            True if safe mode was entered due to comm timeout.
        """
        elapsed = time.time() - self._last_comm_time
        if elapsed > self.comm_timeout_s and not self.state.active:
            self.enter_safe_mode(SafeModeReason.COMM_LOSS)
            return True
        return False

    def enter_safe_mode(self, reason: SafeModeReason) -> None:
        """Transition to safe mode.

        Args:
            reason: The reason for entering safe mode.
        """
        if self.state.active:
            self.logger.warning("Already in safe mode (reason: %s)", self.state.reason)
            return

        self.state.active = True
        self.state.reason = reason
        self.state.entered_at = time.time()
        self.state.recovery_attempts = 0

        self.logger.critical("ENTERING SAFE MODE — reason: %s", reason.value)

        self._disabled_subsystems = [
            "CAMERA", "PAYLOAD", "COMM_SBAND", "HEATER",
        ]
        self.logger.info(
            "Disabled subsystems: %s",
            ", ".join(self._disabled_subsystems),
        )

    def exit_safe_mode(self) -> bool:
        """Attempt to exit safe mode and restore normal operation.

        Returns:
            True if safe mode was exited successfully.
        """
        if not self.state.active:
            return True

        self.logger.info(
            "Exiting safe mode after %.1f hours",
            self.state.duration_s / 3600,
        )

        self.state.active = False
        self.state.reason = None

        for subsystem in self._disabled_subsystems:
            self.logger.info("Re-enabling: %s", subsystem)
        self._disabled_subsystems.clear()

        return True

    def should_send_beacon(self) -> bool:
        """Check if it's time to send a beacon packet.

        Returns:
            True if a beacon should be transmitted.
        """
        if not self.state.active:
            return False
        now = time.time()
        if now - self._last_beacon_time >= self.beacon_interval_s:
            self._last_beacon_time = now
            self.state.beacon_count += 1
            return True
        return False

    def _attempt_recovery(self) -> None:
        """Try to exit safe mode with checks."""
        self.state.recovery_attempts += 1
        if self.state.recovery_attempts > self.max_recovery_attempts:
            self.logger.error("Max recovery attempts reached — staying in safe mode")
            return
        self.logger.info(
            "Recovery attempt %d/%d",
            self.state.recovery_attempts,
            self.max_recovery_attempts,
        )
        self.exit_safe_mode()

    def update(self) -> SafeModeState:
        """Periodic update — check timeouts, manage beacons.

        Returns:
            Current SafeModeState.
        """
        self.check_comm_timeout()

        if self.state.active:
            self.state.duration_s = time.time() - self.state.entered_at

            now = time.time()
            if now - self._last_recovery_check > self._recovery_check_interval_s:
                self._last_recovery_check = now
                if self.state.reason == SafeModeReason.COMM_LOSS:
                    self.logger.info(
                        "Safe mode duration: %.1f hours",
                        self.state.duration_s / 3600,
                    )

        return self.state

    def get_disabled_subsystems(self) -> list[str]:
        """Return list of subsystems disabled by safe mode."""
        return list(self._disabled_subsystems)

    def is_active(self) -> bool:
        """Check if safe mode is currently active."""
        return self.state.active
