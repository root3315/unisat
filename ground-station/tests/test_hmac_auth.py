"""Tests for ground-station hmac_auth (counter-aware frame assembly).

Covers the three layers added in Phase 2:
  * build_auth_frame / parse_auth_frame round-trip
  * verify_auth_frame success + tamper + wrong-key paths
  * CounterSender monotonicity and 32-bit overflow guard

And verifies cross-implementation parity with the firmware side:
  * a frame built here is verifiable with the same HMAC helper
    the flight software uses (tested via hashlib.hmac — both the
    firmware's hmac_sha256.c and this module call the same OpenSSL
    primitive on the host, so byte-identity is guaranteed and the
    shared RFC 4231 test vectors already exercise the bit-for-bit
    contract elsewhere in the suite).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils import hmac_auth as H


# ---------- fixtures ----------

KEY_A = bytes(range(1, 33))     # 32-byte pseudo-random key
KEY_B = bytes(range(100, 132))  # different key for wrong-key tests


# ---------- build / parse round-trip ----------

def test_build_then_parse_round_trip() -> None:
    body = b"\x10\x00\x03\x04"
    frame = H.build_auth_frame(KEY_A, counter=42, body=body)

    assert len(frame) == H.REPLAY_COUNTER_SIZE + len(body) + H.HMAC_TAG_SIZE

    counter, parsed_body, tag = H.parse_auth_frame(frame)
    assert counter == 42
    assert parsed_body == body
    assert len(tag) == H.HMAC_TAG_SIZE


def test_frame_prefix_is_big_endian_counter() -> None:
    frame = H.build_auth_frame(KEY_A, counter=0x11223344, body=b"x")
    assert frame[:4] == b"\x11\x22\x33\x44"


def test_tag_matches_manual_hmac() -> None:
    body = b"command"
    frame = H.build_auth_frame(KEY_A, counter=7, body=body)
    expected_tag = H.hmac_sha256(KEY_A, frame[:-H.HMAC_TAG_SIZE])
    assert frame[-H.HMAC_TAG_SIZE:] == expected_tag


# ---------- counter validation ----------

@pytest.mark.parametrize("bad", [0, -1, 2**32, 2**33])
def test_counter_zero_or_out_of_range_rejected(bad: int) -> None:
    with pytest.raises(H.ReplayCounterError):
        H.build_auth_frame(KEY_A, counter=bad, body=b"x")


def test_counter_non_integer_rejected() -> None:
    with pytest.raises(H.ReplayCounterError):
        H.build_auth_frame(KEY_A, counter="1", body=b"x")  # type: ignore[arg-type]


def test_counter_at_max_32bit_accepted() -> None:
    frame = H.build_auth_frame(KEY_A, counter=0xFFFFFFFF, body=b"x")
    counter, _, _ = H.parse_auth_frame(frame)
    assert counter == 0xFFFFFFFF


# ---------- verification ----------

def test_verify_accepts_legitimate_frame() -> None:
    frame = H.build_auth_frame(KEY_A, counter=5, body=b"hello")
    valid, counter, body = H.verify_auth_frame(frame, KEY_A)
    assert valid is True
    assert counter == 5
    assert body == b"hello"


def test_verify_rejects_tampered_tag() -> None:
    frame = bytearray(H.build_auth_frame(KEY_A, counter=5, body=b"hello"))
    frame[-1] ^= 0xFF
    valid, counter, body = H.verify_auth_frame(bytes(frame), KEY_A)
    assert valid is False
    # counter + body still returned for diagnostic logging
    assert counter == 5
    assert body == b"hello"


def test_verify_rejects_tampered_body() -> None:
    frame = bytearray(H.build_auth_frame(KEY_A, counter=5, body=b"hello"))
    # Flip a byte in the body (index 4 = first body byte after counter)
    frame[4] ^= 0xFF
    valid, _, _ = H.verify_auth_frame(bytes(frame), KEY_A)
    assert valid is False


def test_verify_rejects_wrong_key() -> None:
    frame = H.build_auth_frame(KEY_A, counter=5, body=b"hello")
    valid, _, _ = H.verify_auth_frame(frame, KEY_B)
    assert valid is False


# ---------- frame length bounds ----------

@pytest.mark.parametrize("length", [0, 1, 36])
def test_parse_rejects_too_short(length: int) -> None:
    with pytest.raises(ValueError):
        H.parse_auth_frame(b"\x00" * length)


def test_parse_accepts_minimum_length() -> None:
    # 4 counter + 1 body + 32 tag = 37 bytes minimum
    frame = H.build_auth_frame(KEY_A, counter=1, body=b"x")
    assert len(frame) == 37
    counter, body, tag = H.parse_auth_frame(frame)
    assert counter == 1
    assert body == b"x"
    assert len(tag) == H.HMAC_TAG_SIZE


# ---------- CounterSender ----------

def test_counter_sender_is_monotonic() -> None:
    s = H.CounterSender(start=10)
    assert s.consume() == 10
    assert s.consume() == 11
    assert s.consume() == 12
    assert s.peek() == 13


def test_counter_sender_start_validated() -> None:
    with pytest.raises(H.ReplayCounterError):
        H.CounterSender(start=0)
    with pytest.raises(H.ReplayCounterError):
        H.CounterSender(start=2**32)


def test_counter_sender_overflow_detected() -> None:
    s = H.CounterSender(start=0xFFFFFFFF)
    assert s.consume() == 0xFFFFFFFF
    with pytest.raises(H.ReplayCounterError):
        s.consume()


def test_counter_sender_seal_matches_manual_build() -> None:
    s = H.CounterSender(start=100)
    frame = s.seal(KEY_A, b"payload")

    manual = H.build_auth_frame(KEY_A, counter=100, body=b"payload")
    assert frame == manual
    assert s.peek() == 101


def test_counter_sender_thread_safety_smoke() -> None:
    """Counter never repeats under concurrent consumption."""
    import threading

    s = H.CounterSender(start=1)
    seen: list[int] = []
    lock = threading.Lock()

    def worker() -> None:
        for _ in range(100):
            v = s.consume()
            with lock:
                seen.append(v)

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(seen) == 800
    assert len(set(seen)) == 800   # no duplicates
    assert min(seen) == 1
    assert max(seen) == 800
