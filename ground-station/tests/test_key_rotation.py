"""Tests for the ground-side HMAC key-rotation policy."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

_GS_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_GS_ROOT))

from utils.key_rotation import (  # noqa: E402
    COUNTER_SPACE,
    KeyEpochState,
    KeyRotationPolicy,
)


def _policy_at(counter_used: int = 0, age_days: int = 0) -> KeyRotationPolicy:
    now = datetime.now(timezone.utc)
    epoch = KeyEpochState(
        generation=1,
        activated_at=now - timedelta(days=age_days),
        counter_used=counter_used,
    )
    return KeyRotationPolicy(epoch)


def test_fresh_key_is_ok():
    decision = _policy_at(counter_used=0).check_before_send()
    assert decision.allowed is True
    assert decision.urgency == "ok"


def test_warning_at_50_percent():
    used = int(COUNTER_SPACE * 0.55)
    decision = _policy_at(counter_used=used).check_before_send()
    assert decision.allowed is True
    assert decision.urgency == "warn"
    assert "50" not in decision.reason  # percent shown as 55.x


def test_rotate_now_at_80_percent():
    used = int(COUNTER_SPACE * 0.81)
    decision = _policy_at(counter_used=used).check_before_send()
    assert decision.allowed is False
    assert decision.urgency == "rotate_now"
    assert "rotate" in decision.reason.lower()


def test_age_triggers_rotate_even_with_low_counter():
    decision = _policy_at(counter_used=10, age_days=400).check_before_send()
    assert decision.allowed is False
    assert decision.urgency == "rotate_now"


def test_age_disabled_with_zero_max_lifetime():
    now = datetime.now(timezone.utc)
    epoch = KeyEpochState(
        generation=1,
        activated_at=now - timedelta(days=5000),
        counter_used=10,
    )
    policy = KeyRotationPolicy(epoch, max_lifetime_days=0)
    decision = policy.check_before_send()
    assert decision.allowed is True


def test_record_sent_increments_counter():
    policy = _policy_at()
    policy.record_sent(1)
    policy.record_sent(4)
    assert policy.counter_used == 5


def test_rotate_resets_counter_and_bumps_generation():
    policy = _policy_at(counter_used=100)
    retired = policy.rotate(new_generation=2)
    assert policy.generation == 2
    assert policy.counter_used == 0
    assert retired.generation == 1
    assert retired.counter_used == 100


def test_rotate_rejects_stale_generation():
    policy = _policy_at()
    with pytest.raises(ValueError):
        policy.rotate(new_generation=0)
    with pytest.raises(ValueError):
        policy.rotate(new_generation=1)  # same as current


def test_record_sent_rejects_negative():
    with pytest.raises(ValueError):
        _policy_at().record_sent(-1)


def test_save_and_load_roundtrip(tmp_path):
    policy = _policy_at(counter_used=1234)
    path = tmp_path / "state.json"
    policy.save(path)

    loaded = KeyRotationPolicy.load(path)
    assert loaded.generation == policy.generation
    assert loaded.counter_used == policy.counter_used


def test_load_preserves_thresholds(tmp_path):
    epoch = KeyEpochState(
        generation=7,
        activated_at=datetime.now(timezone.utc),
    )
    policy = KeyRotationPolicy(
        epoch,
        warn_threshold_pct=40,
        rotate_threshold_pct=70,
        max_lifetime_days=180,
    )
    path = tmp_path / "state.json"
    policy.save(path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["warn_threshold_pct"] == 40
    assert payload["rotate_threshold_pct"] == 70
    assert payload["max_lifetime_days"] == 180


def test_invalid_threshold_ordering_rejected():
    epoch = KeyEpochState(
        generation=1,
        activated_at=datetime.now(timezone.utc),
    )
    with pytest.raises(ValueError):
        KeyRotationPolicy(epoch, warn_threshold_pct=90,
                           rotate_threshold_pct=80)
