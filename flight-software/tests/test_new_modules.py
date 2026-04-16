"""Tests for new modules: IMU, BarometricAltimeter, DescentController."""

import asyncio
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.imu_sensor import IMUSensor, IMUReading
from modules.barometric_altimeter import BarometricAltimeter, pressure_to_altitude
from modules.descent_controller import DescentController, DescentPhase


# ---- IMU Tests ----

class TestIMUSensor:
    @pytest.fixture
    def imu(self):
        return IMUSensor(config={"simulate": True, "sensor_type": "MPU9250"})

    @pytest.mark.asyncio
    async def test_initialize(self, imu):
        ok = await imu.initialize()
        assert ok

    @pytest.mark.asyncio
    async def test_read_returns_data(self, imu):
        await imu.initialize()
        reading = imu.read()
        assert isinstance(reading, IMUReading)
        assert reading.timestamp > 0

    @pytest.mark.asyncio
    async def test_accel_magnitude_near_1g(self, imu):
        """Simulated idle IMU should read ~1g total acceleration."""
        await imu.initialize()
        readings = [imu.read() for _ in range(100)]
        avg_mag = sum(r.accel_magnitude_g for r in readings) / len(readings)
        assert 0.8 < avg_mag < 1.2

    @pytest.mark.asyncio
    async def test_gyro_near_zero(self, imu):
        """Simulated idle IMU should have near-zero angular rates."""
        await imu.initialize()
        readings = [imu.read() for _ in range(100)]
        avg_gyro = sum(r.gyro_magnitude_dps for r in readings) / len(readings)
        assert avg_gyro < 5.0

    @pytest.mark.asyncio
    async def test_sample_count_increments(self, imu):
        await imu.initialize()
        imu.read()
        imu.read()
        imu.read()
        status = await imu.get_status()
        assert status["sample_count"] == 3

    def test_detect_freefall_no_data(self, imu):
        assert not imu.detect_freefall()

    def test_detect_landing_insufficient_data(self, imu):
        assert not imu.detect_landing()

    @pytest.mark.asyncio
    async def test_recent_readings(self, imu):
        await imu.initialize()
        for _ in range(20):
            imu.read()
        recent = imu.get_recent_readings(10)
        assert len(recent) == 10


# ---- Barometric Altimeter Tests ----

class TestBarometricAltimeter:
    @pytest.fixture
    def baro(self):
        return BarometricAltimeter(config={
            "simulate": True,
            "ref_pressure_pa": 101325,
            "ground_altitude_m": 0,
        })

    @pytest.mark.asyncio
    async def test_initialize(self, baro):
        ok = await baro.initialize()
        assert ok

    @pytest.mark.asyncio
    async def test_read_returns_data(self, baro):
        await baro.initialize()
        reading = baro.read()
        assert reading.pressure_pa > 0
        assert reading.timestamp > 0

    @pytest.mark.asyncio
    async def test_altitude_near_ground(self, baro):
        """Simulated ground-level baro should give altitude near 0."""
        await baro.initialize()
        readings = [baro.read() for _ in range(50)]
        avg_alt = sum(r.altitude_m for r in readings) / len(readings)
        assert abs(avg_alt) < 50  # within 50m of ground

    @pytest.mark.asyncio
    async def test_vertical_speed_calculated(self, baro):
        await baro.initialize()
        baro.read()
        reading = baro.read()
        # Speed should be a number (may be ~0 for ground level)
        assert isinstance(reading.vertical_speed_m_s, float)

    def test_pressure_to_altitude_sea_level(self):
        alt = pressure_to_altitude(101325.0)
        assert abs(alt) < 1.0

    def test_pressure_to_altitude_1000m(self):
        # ~89875 Pa at 1000m
        alt = pressure_to_altitude(89875.0)
        assert 900 < alt < 1100

    def test_pressure_to_altitude_zero(self):
        alt = pressure_to_altitude(0.0)
        assert alt == 0.0

    @pytest.mark.asyncio
    async def test_max_altitude_tracking(self, baro):
        await baro.initialize()
        for _ in range(10):
            baro.read()
        # max altitude should be non-negative
        assert baro.get_max_altitude_agl() >= 0

    def test_detect_apogee_insufficient_data(self, baro):
        assert not baro.detect_apogee()

    def test_detect_burst_insufficient_data(self, baro):
        assert not baro.detect_burst()


# ---- Descent Controller Tests ----

class TestDescentController:
    @pytest.fixture
    def dc(self):
        return DescentController(config={
            "deploy_altitude_m": 500,
            "target_descent_rate_m_s": 8.0,
            "min_descent_rate_m_s": 6.0,
            "max_descent_rate_m_s": 11.0,
            "min_telemetry_samples": 10,
        })

    @pytest.mark.asyncio
    async def test_initialize(self, dc):
        ok = await dc.initialize()
        assert ok

    @pytest.mark.asyncio
    async def test_initial_phase_is_idle(self, dc):
        await dc.initialize()
        assert dc.phase == DescentPhase.IDLE

    def test_arm(self, dc):
        assert dc.arm()
        assert dc.phase == DescentPhase.ARMED

    def test_cannot_arm_after_deploy(self, dc):
        dc.phase = DescentPhase.DESCENDING
        assert not dc.arm()

    def test_update_tracks_altitude(self, dc):
        dc.arm()
        tlm = dc.update(altitude_agl_m=1000, descent_rate_m_s=0.0)
        assert tlm.altitude_agl_m == 1000

    def test_low_g_triggers_deploy_ready(self, dc):
        dc.arm()
        dc.update(altitude_agl_m=1000, descent_rate_m_s=0.0, accel_g=0.2)
        assert dc.phase == DescentPhase.DEPLOY_READY

    def test_altitude_triggers_deployment(self, dc):
        dc.arm()
        dc.update(altitude_agl_m=1000, descent_rate_m_s=0.0, accel_g=0.2)
        dc.update(altitude_agl_m=400, descent_rate_m_s=-5.0, accel_g=0.8)
        assert dc.phase == DescentPhase.DEPLOYED

    def test_validate_competition_no_data(self, dc):
        result = dc.validate_competition()
        # Should fail with insufficient telemetry
        assert not result.valid
        assert any("Insufficient" in i for i in result.issues)

    def test_validate_competition_good_descent(self, dc):
        dc.arm()
        # Simulate deployment and descent
        dc.update(1000, 0, 0.2)  # apogee, low-g
        dc.update(400, -8.0, 0.8)  # below deploy altitude -> deploy
        dc.phase = DescentPhase.DESCENDING
        # Add descent rate samples
        for i in range(20):
            dc._descent_rates.append(8.0)
            dc._telemetry.append(dc.update(400 - i * 15, -8.0))

        result = dc.validate_competition()
        assert result.valid
        assert 6.0 <= result.descent_rate_avg_m_s <= 11.0

    @pytest.mark.asyncio
    async def test_get_status(self, dc):
        await dc.initialize()
        status = await dc.get_status()
        assert status["phase"] == "IDLE"
        assert "telemetry_samples" in status
