"""Tests for the PowerManager module."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.power_manager import PowerManager, PowerPriority, SubsystemPower


class TestPowerManagerInit:
    """Tests for PowerManager initialization."""

    def test_default_subsystems_present(self):
        pm = PowerManager()
        expected = {"OBC", "COMM_UHF", "ADCS", "GNSS", "CAMERA", "PAYLOAD", "HEATER", "COMM_SBAND"}
        assert set(pm.budget.subsystems.keys()) == expected

    def test_all_subsystems_enabled_by_default(self):
        pm = PowerManager()
        for name, sub in pm.budget.subsystems.items():
            assert sub.enabled is True, f"{name} should be enabled by default"

    def test_obc_has_highest_priority(self):
        pm = PowerManager()
        obc = pm.budget.subsystems["OBC"]
        for name, sub in pm.budget.subsystems.items():
            if name != "OBC":
                assert obc.priority > sub.priority, f"OBC priority should exceed {name}"


class TestLoadShedding:
    """Tests for load shedding at low SOC."""

    def test_load_shed_disables_low_priority_below_30_pct(self):
        pm = PowerManager()
        pm.update(solar_w=3.0, battery_soc=25.0)
        # Subsystems below GNSS priority (6) should be disabled
        assert pm.budget.subsystems["CAMERA"].enabled is False
        assert pm.budget.subsystems["COMM_SBAND"].enabled is False

    def test_load_shed_keeps_high_priority_enabled(self):
        pm = PowerManager()
        pm.update(solar_w=3.0, battery_soc=25.0)
        assert pm.budget.subsystems["OBC"].enabled is True
        assert pm.budget.subsystems["COMM_UHF"].enabled is True
        assert pm.budget.subsystems["ADCS"].enabled is True
        assert pm.budget.subsystems["GNSS"].enabled is True

    def test_emergency_shed_below_15_pct(self):
        pm = PowerManager()
        pm.update(solar_w=1.0, battery_soc=10.0)
        # Only OBC and COMM_UHF should remain (priority >= COMM)
        assert pm.budget.subsystems["OBC"].enabled is True
        assert pm.budget.subsystems["COMM_UHF"].enabled is True
        assert pm.budget.subsystems["ADCS"].enabled is False
        assert pm.budget.subsystems["GNSS"].enabled is False
        assert pm.budget.subsystems["CAMERA"].enabled is False
        assert pm.budget.subsystems["PAYLOAD"].enabled is False
        assert pm.budget.subsystems["HEATER"].enabled is False
        assert pm.budget.subsystems["COMM_SBAND"].enabled is False

    def test_obc_never_disabled_by_emergency_shed(self):
        pm = PowerManager()
        pm.update(solar_w=0.0, battery_soc=1.0)
        assert pm.budget.subsystems["OBC"].enabled is True


class TestEnableDisable:
    """Tests for manual enable/disable."""

    def test_disable_subsystem_returns_true(self):
        pm = PowerManager()
        assert pm.disable_subsystem("CAMERA") is True
        assert pm.budget.subsystems["CAMERA"].enabled is False

    def test_disable_obc_is_refused(self):
        pm = PowerManager()
        assert pm.disable_subsystem("OBC") is False
        assert pm.budget.subsystems["OBC"].enabled is True

    def test_enable_subsystem_returns_true(self):
        pm = PowerManager()
        pm.disable_subsystem("CAMERA")
        assert pm.enable_subsystem("CAMERA") is True
        assert pm.budget.subsystems["CAMERA"].enabled is True

    def test_disable_unknown_returns_false(self):
        pm = PowerManager()
        assert pm.disable_subsystem("NONEXISTENT") is False

    def test_enable_unknown_returns_false(self):
        pm = PowerManager()
        assert pm.enable_subsystem("NONEXISTENT") is False


class TestConsumption:
    """Tests for power consumption calculation."""

    def test_total_consumption_all_enabled(self):
        pm = PowerManager()
        total = pm.get_consumption()
        expected = sum(s.nominal_w for s in pm.budget.subsystems.values())
        assert total == expected

    def test_consumption_decreases_when_subsystem_disabled(self):
        pm = PowerManager()
        full = pm.get_consumption()
        pm.disable_subsystem("CAMERA")
        reduced = pm.get_consumption()
        assert reduced < full
        assert abs(reduced - (full - 2.0)) < 0.001  # CAMERA nominal is 2.0 W

    def test_update_sets_net_power(self):
        pm = PowerManager()
        budget = pm.update(solar_w=10.0, battery_soc=80.0)
        assert budget.net_power_w == 10.0 - budget.total_consumption_w
