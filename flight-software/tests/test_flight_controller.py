"""Tests for FlightController."""

from flight_controller import FlightController, SatelliteState


def test_satellite_state_enum():
    assert SatelliteState.NOMINAL.value == "nominal"
    assert SatelliteState.SAFE_MODE.value == "safe_mode"


def test_flight_controller_init(tmp_path):
    config = tmp_path / "mission_config.json"
    config.write_text('{"mission":{"name":"Test","version":"1.0"},"subsystems":{}}')
    fc = FlightController(str(config))
    assert fc.state == SatelliteState.STARTUP
    assert fc.config["mission"]["name"] == "Test"
