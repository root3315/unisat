"""Tests for the SafeModeHandler module."""

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.safe_mode import SafeModeHandler, SafeModeReason


class TestEnterSafeMode:
    """Tests for entering safe mode."""

    def test_enter_sets_active(self):
        h = SafeModeHandler()
        h.enter_safe_mode(SafeModeReason.COMM_LOSS)
        assert h.state.active is True

    def test_enter_sets_reason(self):
        h = SafeModeHandler()
        h.enter_safe_mode(SafeModeReason.LOW_BATTERY)
        assert h.state.reason is SafeModeReason.LOW_BATTERY

    def test_enter_resets_recovery_attempts(self):
        h = SafeModeHandler()
        h.enter_safe_mode(SafeModeReason.THERMAL_LIMIT)
        assert h.state.recovery_attempts == 0

    def test_double_enter_does_not_overwrite(self):
        h = SafeModeHandler()
        h.enter_safe_mode(SafeModeReason.COMM_LOSS)
        h.enter_safe_mode(SafeModeReason.LOW_BATTERY)
        assert h.state.reason is SafeModeReason.COMM_LOSS


class TestExitSafeMode:
    """Tests for exiting safe mode."""

    def test_exit_clears_active(self):
        h = SafeModeHandler()
        h.enter_safe_mode(SafeModeReason.MANUAL)
        h.exit_safe_mode()
        assert h.state.active is False

    def test_exit_clears_reason(self):
        h = SafeModeHandler()
        h.enter_safe_mode(SafeModeReason.MANUAL)
        h.exit_safe_mode()
        assert h.state.reason is None

    def test_exit_when_not_active_returns_true(self):
        h = SafeModeHandler()
        assert h.exit_safe_mode() is True

    def test_exit_clears_disabled_subsystems(self):
        h = SafeModeHandler()
        h.enter_safe_mode(SafeModeReason.COMM_LOSS)
        h.exit_safe_mode()
        assert h.get_disabled_subsystems() == []


class TestBeaconInterval:
    """Tests for beacon timing in safe mode."""

    def test_beacon_not_sent_when_inactive(self):
        h = SafeModeHandler()
        assert h.should_send_beacon() is False

    def test_first_beacon_sent_immediately(self):
        h = SafeModeHandler()
        h.enter_safe_mode(SafeModeReason.COMM_LOSS)
        assert h.should_send_beacon() is True
        assert h.state.beacon_count == 1

    def test_beacon_respects_30s_interval(self):
        h = SafeModeHandler()
        h.enter_safe_mode(SafeModeReason.COMM_LOSS)
        h.should_send_beacon()  # first beacon
        # Immediately after, interval has not elapsed
        assert h.should_send_beacon() is False

    @patch("modules.safe_mode.time")
    def test_beacon_sent_after_interval(self, mock_time):
        mock_time.time.side_effect = [
            1000.0,    # __init__ _last_comm_time
            1000.0,    # enter_safe_mode entered_at
            1000.0,    # should_send_beacon (first call, now)
            1031.0,    # should_send_beacon (second call, 31s later)
        ]
        h = SafeModeHandler()
        h.enter_safe_mode(SafeModeReason.COMM_LOSS)
        h.should_send_beacon()  # first
        assert h.should_send_beacon() is True
        assert h.state.beacon_count == 2


class TestRecoveryAttempts:
    """Tests for max recovery attempts."""

    def test_recovery_limit_is_five(self):
        h = SafeModeHandler()
        assert h.max_recovery_attempts == 5

    def test_recovery_attempts_increment(self):
        h = SafeModeHandler()
        h.enter_safe_mode(SafeModeReason.COMM_LOSS)
        h._attempt_recovery()
        assert h.state.recovery_attempts == 1

    def test_exceeding_max_recovery_stays_in_safe_mode(self):
        h = SafeModeHandler()
        h.enter_safe_mode(SafeModeReason.COMM_LOSS)
        for _ in range(6):
            h.enter_safe_mode.__func__  # reset for re-entry
            h._attempt_recovery()
        # After 5 successful recoveries, the 6th should be refused
        assert h.state.recovery_attempts == 6
        # Re-enter safe mode to test the guard
        h.state.active = True
        h.state.recovery_attempts = 6
        h._attempt_recovery()
        # Should still be active because max exceeded
        assert h.state.active is True


class TestCommTimeout:
    """Tests for communication timeout detection."""

    @patch("modules.safe_mode.time")
    def test_no_timeout_within_24h(self, mock_time):
        mock_time.time.side_effect = [
            1000.0,      # __init__
            1000.0 + 3600,  # check_comm_timeout
        ]
        h = SafeModeHandler()
        assert h.check_comm_timeout() is False

    @patch("modules.safe_mode.time")
    def test_timeout_after_24h(self, mock_time):
        mock_time.time.side_effect = [
            1000.0,               # __init__
            1000.0 + 86401,       # check_comm_timeout (first time.time)
            1000.0 + 86401,       # enter_safe_mode entered_at
        ]
        h = SafeModeHandler()
        assert h.check_comm_timeout() is True
        assert h.state.active is True
        assert h.state.reason is SafeModeReason.COMM_LOSS


class TestDisabledSubsystems:
    """Tests for disabled subsystem tracking."""

    def test_disabled_list_on_enter(self):
        h = SafeModeHandler()
        h.enter_safe_mode(SafeModeReason.COMM_LOSS)
        disabled = h.get_disabled_subsystems()
        assert "CAMERA" in disabled
        assert "PAYLOAD" in disabled
        assert "COMM_SBAND" in disabled
        assert "HEATER" in disabled
        assert len(disabled) == 4

    def test_disabled_list_is_copy(self):
        h = SafeModeHandler()
        h.enter_safe_mode(SafeModeReason.COMM_LOSS)
        lst = h.get_disabled_subsystems()
        lst.clear()
        assert len(h.get_disabled_subsystems()) == 4
