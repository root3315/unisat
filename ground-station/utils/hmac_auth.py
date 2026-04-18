"""HMAC-SHA256 auth helpers (Track 1b + Phase 2 replay counter).

Mirrors firmware/stm32/Drivers/Crypto/hmac_sha256.c and
firmware/stm32/Core/Src/command_dispatcher.c so the ground
station and flight software agree on what a tagged, replay-safe
command looks like on the wire.

Wire format
-----------
    [ 4-byte counter (big-endian) ][ body ][ HMAC-SHA256 tag (32 B) ]
      \\_________ authenticated ________/

Both sides compute the HMAC over the concatenation of the counter
bytes and the body. The dispatcher recomputes the tag over the
first ``len - 32`` bytes of the received frame, compares in
constant time, then extracts the counter and feeds it through the
sliding-window replay filter.

Replay-counter policy (ground)
------------------------------
Ground operators are responsible for never reusing a counter value
against the same key. The :class:`CounterSender` helper keeps a
monotonic counter that survives across serialised commands in one
operator session; a long-lived persistent counter should be stored
in a ground-side database (``last_counter`` column, per-satellite).
"""

from __future__ import annotations

import hmac
import hashlib
import struct
import threading

HMAC_TAG_SIZE = 32
REPLAY_COUNTER_SIZE = 4

# Keep the module-level names the existing tests import.

def hmac_sha256(key: bytes, msg: bytes) -> bytes:
    """Compute HMAC-SHA256 tag.

    Matches firmware/stm32/Drivers/Crypto/hmac_sha256.c byte-for-byte
    (verified by the RFC 4231 test vectors shared between the two
    implementations).
    """
    return hmac.new(key, msg, hashlib.sha256).digest()


def verify(tag_a: bytes, tag_b: bytes) -> bool:
    """Constant-time tag comparison — same semantics as the C side."""
    if len(tag_a) != HMAC_TAG_SIZE or len(tag_b) != HMAC_TAG_SIZE:
        return False
    return hmac.compare_digest(tag_a, tag_b)


# ------------------------------------------------------------------
#  Phase 2 additions: counter-aware frame assembly / parsing
# ------------------------------------------------------------------

class ReplayCounterError(ValueError):
    """Raised when a counter value is outside the 32-bit range or
    equals the reserved sentinel zero."""


def build_auth_frame(key: bytes, counter: int, body: bytes) -> bytes:
    """Assemble a wire frame the flight dispatcher will accept.

    Parameters
    ----------
    key
        Pre-shared HMAC key (16..32 bytes on UniSat; RFC 4231 allows
        any length but the C dispatcher caps at 64 B).
    counter
        Monotonic 32-bit counter. Must be > 0 (zero is the reserved
        sentinel on the firmware side — see
        ``firmware/stm32/Core/Src/command_dispatcher.c::
        replay_window_check_and_update``) and must strictly exceed
        the last counter already transmitted for this key epoch.
    body
        CCSDS Space Packet bytes (header + payload) that the ground
        operator wants the satellite to act on.

    Returns
    -------
    bytes
        ``counter_be(4) + body + hmac_sha256(key, counter||body)``
        — the exact layout CCSDS_Dispatcher_Submit expects.

    Raises
    ------
    ReplayCounterError
        If ``counter`` is zero, negative, or larger than 2**32 - 1.
    """
    if not isinstance(counter, int) or counter <= 0 or counter > 0xFFFFFFFF:
        raise ReplayCounterError(
            f"counter must satisfy 1 <= counter <= 2**32-1, got {counter!r}"
        )
    counter_be = struct.pack(">I", counter)
    auth = counter_be + body
    tag = hmac_sha256(key, auth)
    return auth + tag


def parse_auth_frame(frame: bytes) -> tuple[int, bytes, bytes]:
    """Inverse of :func:`build_auth_frame`.

    Does NOT verify the HMAC — that's the caller's job (call
    :func:`verify_auth_frame` for the full check). Used by the
    ground-side decoder to introspect an off-air frame before
    running the tag check against a candidate key.

    Returns
    -------
    (counter, body, tag)
        ``counter`` is an int 0..2**32-1; zero means a crafted
        frame that the flight side will reject regardless of
        HMAC validity.

    Raises
    ------
    ValueError
        If ``frame`` is shorter than the minimum 37 bytes.
    """
    min_len = REPLAY_COUNTER_SIZE + 1 + HMAC_TAG_SIZE
    if len(frame) < min_len:
        raise ValueError(
            f"frame too short: {len(frame)} < {min_len} (counter + 1-byte "
            f"body + HMAC)"
        )
    counter = struct.unpack(">I", frame[:REPLAY_COUNTER_SIZE])[0]
    tag = frame[-HMAC_TAG_SIZE:]
    body = frame[REPLAY_COUNTER_SIZE:-HMAC_TAG_SIZE]
    return counter, body, tag


def verify_auth_frame(frame: bytes, key: bytes) -> tuple[bool, int, bytes]:
    """Constant-time authenticity check against ``key``.

    Returns
    -------
    (valid, counter, body)
        ``valid`` is True iff the recomputed HMAC matches the trailing
        tag byte-for-byte. ``counter`` and ``body`` are returned even
        on mismatch (for diagnostic logging) — the caller must gate
        any action on ``valid``.

    Raises
    ------
    ValueError
        If ``frame`` is shorter than the minimum 37 bytes.
    """
    counter, body, tag = parse_auth_frame(frame)
    auth_span = frame[:-HMAC_TAG_SIZE]
    expected = hmac_sha256(key, auth_span)
    return verify(expected, tag), counter, body


class CounterSender:
    """Monotonic counter source for a single ground->satellite key epoch.

    Call sites typically go:

    >>> sender = CounterSender(start=1)
    >>> frame = sender.seal(KEY, b"\\x10\\x00\\x01\\x02")
    >>> frame2 = sender.seal(KEY, b"\\x10\\x00\\x03\\x04")  # counter bumps

    The counter is thread-safe so a multi-threaded operator console
    can't accidentally reuse a value.
    """

    def __init__(self, start: int = 1) -> None:
        if start <= 0 or start > 0xFFFFFFFF:
            raise ReplayCounterError(
                f"start counter must satisfy 1 <= start <= 2**32-1, "
                f"got {start!r}"
            )
        self._next = start
        self._lock = threading.Lock()

    def peek(self) -> int:
        """Return the next counter value without consuming it."""
        with self._lock:
            return self._next

    def consume(self) -> int:
        """Allocate one counter value and advance the generator.

        Raises :class:`ReplayCounterError` on 32-bit overflow — the
        operator is expected to rotate the key before this happens.
        """
        with self._lock:
            if self._next > 0xFFFFFFFF:
                raise ReplayCounterError(
                    "counter space exhausted (>2**32); rotate the key"
                )
            value = self._next
            self._next += 1
            return value

    def seal(self, key: bytes, body: bytes) -> bytes:
        """Consume one counter value and return the ready-to-ship frame."""
        return build_auth_frame(key, self.consume(), body)
