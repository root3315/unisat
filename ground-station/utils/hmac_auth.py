"""HMAC-SHA256 auth helpers (Track 1b) — mirror of
firmware/stm32/Drivers/Crypto/hmac_sha256.c.

Thin wrapper around the stdlib for parity with the C API so that the
ground station and flight software agree on what a tagged command
looks like on the wire.
"""

from __future__ import annotations

import hmac
import hashlib

HMAC_TAG_SIZE = 32


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
