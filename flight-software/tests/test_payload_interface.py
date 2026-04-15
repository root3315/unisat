"""Tests for the PayloadInterface module."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.payload_interface import (
    NullPayload,
    PayloadSample,
    PayloadStatus,
    RadiationPayload,
)


class TestRadiationPayloadLifecycle:
    """Tests for RadiationPayload init, start, collect, stop."""

    def test_init_inactive(self):
        p = RadiationPayload()
        assert p.status.active is False
        assert p.status.payload_type == "radiation_monitor"

    def test_start_activates(self):
        p = RadiationPayload()
        assert p.start() is True
        assert p.status.active is True

    def test_collect_returns_sample(self):
        p = RadiationPayload()
        p.start()
        sample = p.collect()
        assert sample is not None
        assert sample.payload_type == "radiation_monitor"
        assert "cps" in sample.data
        assert "dose_rate_usv_h" in sample.data

    def test_stop_deactivates(self):
        p = RadiationPayload()
        p.start()
        p.stop()
        assert p.status.active is False


class TestNullPayload:
    """Tests for NullPayload returns valid data."""

    def test_null_payload_type(self):
        p = NullPayload()
        assert p.status.payload_type == "null"

    def test_null_collect_returns_valid_sample(self):
        p = NullPayload()
        p.start()
        sample = p.collect()
        assert sample is not None
        assert sample.data == {"status": "ok"}

    def test_null_start_and_stop(self):
        p = NullPayload()
        assert p.start() is True
        p.stop()
        assert p.status.active is False


class TestPayloadStatusTracking:
    """Tests for PayloadStatus updates during collection."""

    def test_samples_collected_increments(self):
        p = NullPayload()
        p.start()
        p.collect()
        p.collect()
        p.collect()
        assert p.status.samples_collected == 3

    def test_last_sample_time_updated(self):
        p = NullPayload()
        p.start()
        p.collect()
        assert p.status.last_sample_time > 0.0

    def test_errors_start_at_zero(self):
        p = NullPayload()
        assert p.status.errors == 0


class TestSequenceNumbering:
    """Tests for sample sequence number assignment."""

    def test_sequence_starts_at_one(self):
        p = NullPayload()
        p.start()
        s1 = p.collect()
        assert s1.sequence_num == 1

    def test_sequence_increments(self):
        p = NullPayload()
        p.start()
        s1 = p.collect()
        s2 = p.collect()
        s3 = p.collect()
        assert s1.sequence_num == 1
        assert s2.sequence_num == 2
        assert s3.sequence_num == 3


class TestCollectWhenInactive:
    """Tests for collecting when payload is not active."""

    def test_collect_without_start_returns_none(self):
        p = NullPayload()
        result = p.collect()
        assert result is None

    def test_collect_after_stop_returns_none(self):
        p = NullPayload()
        p.start()
        p.stop()
        result = p.collect()
        assert result is None
