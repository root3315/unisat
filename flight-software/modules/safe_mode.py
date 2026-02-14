"""
Safe Mode Handler — Emergency autonomous operation.

Activates when communication is lost for >24 hours or when
critical system failures are detected. Disables non-essential
subsystems and enters beacon-only mode.
"""

import time
import logging
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger("unisat.safe_mode")


class SafeModeReason(Enum):
    """Reasons for entering safe mode."""
    COMM_LOSS = "communication_loss"
    LOW_BATTERY = "low_battery"
    THERMAL_LIMIT = "thermal_limit"
    WATCHDOG = "watchdog_timeout"
    MANUAL = "manual_command"


@dataclass
class SafeModeState:
    """Current safe mode status."""
    active: bool = False
    reason: SafeModeReason | None = None
    entered_at: float = 0.0
    duration_s: float = 0.0
    beacon_count: int = 0
    recovery_attempts: int = 0


class SafeModeHandler:
    """Manages satellite safe mode transitions and recovery."""

    COMM_TIMEOUT_S = 86400  # 24 hours
    BEACON_INTERVAL_S = 30
    MAX_RECOVERY_ATTEMPTS = 5
    RECOVERY_CHECK_INTERVAL_S = 3600  # 1 hour

    def __init__(self) -> None:
        self.state = SafeModeState()
        self._last_comm_time = time.time()
        self._last_beacon_time = 0.0
        self._last_recovery_check = 0.0
        self._disabled_subsystems: list[str] = []

    def update_comm_timestamp(self) -> None:
        """Call when valid communication is received."""
        self._last_comm_time = time.time()
        if self.state.active and self.state.reason == SafeModeReason.COMM_LOSS:
            logger.info("Communication restored — attempting recovery")
            self._attempt_recovery()

    def check_comm_timeout(self) -> bool:
        """Check if communication has been lost too long."""
        elapsed = time.time() - self._last_comm_time
        if elapsed > self.COMM_TIMEOUT_S and not self.state.active:
            self.enter_safe_mode(SafeModeReason.COMM_LOSS)
            return True
        return False

    def enter_safe_mode(self, reason: SafeModeReason) -> None:
        """Transition to safe mode."""
        if self.state.active:
            logger.warning("Already in safe mode (reason: %s)", self.state.reason)
            return

        self.state.active = True
        self.state.reason = reason
        self.state.entered_at = time.time()
        self.state.recovery_attempts = 0

        logger.critical("ENTERING SAFE MODE — reason: %s", reason.value)

        self._disabled_subsystems = [
            "CAMERA", "PAYLOAD", "COMM_SBAND", "HEATER"
        ]
        logger.info(
            "Disabled subsystems: %s",
            ", ".join(self._disabled_subsystems)
        )

    def exit_safe_mode(self) -> bool:
        """Attempt to exit safe mode and restore normal operation."""
        if not self.state.active:
            return True

        logger.info("Exiting safe mode after %.1f hours",
                     self.state.duration_s / 3600)

        self.state.active = False
        self.state.reason = None

        for subsystem in self._disabled_subsystems:
            logger.info("Re-enabling: %s", subsystem)
        self._disabled_subsystems.clear()

        return True

    def should_send_beacon(self) -> bool:
        """Check if it's time to send a beacon packet."""
        if not self.state.active:
            return False
        now = time.time()
        if now - self._last_beacon_time >= self.BEACON_INTERVAL_S:
            self._last_beacon_time = now
            self.state.beacon_count += 1
            return True
        return False

    def _attempt_recovery(self) -> None:
        """Try to exit safe mode with checks."""
        self.state.recovery_attempts += 1
        if self.state.recovery_attempts > self.MAX_RECOVERY_ATTEMPTS:
            logger.error("Max recovery attempts reached — staying in safe mode")
            return
        logger.info("Recovery attempt %d/%d",
                     self.state.recovery_attempts, self.MAX_RECOVERY_ATTEMPTS)
        self.exit_safe_mode()

    def update(self) -> SafeModeState:
        """Periodic update — check timeouts, manage beacons."""
        self.check_comm_timeout()

        if self.state.active:
            self.state.duration_s = time.time() - self.state.entered_at

            now = time.time()
            if now - self._last_recovery_check > self.RECOVERY_CHECK_INTERVAL_S:
                self._last_recovery_check = now
                if self.state.reason == SafeModeReason.COMM_LOSS:
                    logger.info("Safe mode duration: %.1f hours",
                                 self.state.duration_s / 3600)

        return self.state

    def get_disabled_subsystems(self) -> list[str]:
        """Return list of subsystems disabled by safe mode."""
        return list(self._disabled_subsystems)

    def is_active(self) -> bool:
        """Check if safe mode is currently active."""
        return self.state.active
