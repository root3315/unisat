"""Tests for FlightController."""

from flight_controller import FlightController


def test_flight_controller_init(tmp_path):
    config = tmp_path / "mission_config.json"
    config.write_text(
        '{"mission":{"name":"Test","version":"1.0","mission_type":"cubesat_leo"},"subsystems":{}}'
    )
    fc = FlightController(str(config))
    assert fc.config["mission"]["name"] == "Test"
    assert fc.state_machine.phase_name == "startup"


def test_flight_controller_cansat(tmp_path):
    config = tmp_path / "mission_config.json"
    config.write_text(
        '{"mission":{"name":"CanSat","version":"1.0","mission_type":"cansat_standard"},"subsystems":{}}'
    )
    fc = FlightController(str(config))
    assert fc.profile.platform.value == "cansat"
    assert fc.state_machine.phase_name == "pre_launch"


def test_flight_controller_system_status(tmp_path):
    config = tmp_path / "mission_config.json"
    config.write_text(
        '{"mission":{"name":"Test","version":"1.0","mission_type":"cubesat_leo"},"subsystems":{}}'
    )
    fc = FlightController(str(config))
    status = fc.get_system_status()
    assert "mission_type" in status
    assert "phase" in status
    assert "modules" in status
    assert "events" in status
