"""AX.25 v2.2 link layer — Python reference implementation.

Mirrors firmware/stm32/Drivers/AX25/ax25.c. All interop is verified
against shared golden-vector fixtures in tests/golden/ax25_vectors.json.

See docs/superpowers/specs/2026-04-17-track1-ax25-design.md for design.
"""

from __future__ import annotations


def fcs_crc16(data: bytes) -> int:
    """CRC-16/X.25 per REQ-AX25-006, REQ-AX25-022.

    Parameters:
      poly=0x1021 (reflected: 0x8408), init=0xFFFF,
      refin=True, refout=True, xorout=0xFFFF.

    Oracle (asserted in tests):
      fcs_crc16(b"123456789") == 0x906E.
    """
    crc = 0xFFFF
    for b in data:
        crc ^= b
        for _ in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ 0x8408
            else:
                crc >>= 1
    return (~crc) & 0xFFFF


# ---------------------------------------------------------------------------
# Exception hierarchy for decode failures (REQ-AX25 §5.2).
# ---------------------------------------------------------------------------


class AX25Error(Exception):
    """Base for AX.25 encode/decode failures."""


class StuffingViolation(AX25Error):
    """Six consecutive 1-bits found inside a stuffed stream."""


class FrameOverflow(AX25Error):
    """Frame exceeds the configured size limit."""


class FcsMismatch(AX25Error):
    """CRC-16/X.25 did not match the wire value."""


class InvalidAddress(AX25Error):
    """Callsign or SSID byte violates AX.25 v2.2 §3.12."""


class InvalidControl(AX25Error):
    """Control field is not 0x03 (UI frame)."""


class InvalidPid(AX25Error):
    """PID is not 0xF0 (no layer 3)."""


# ---------------------------------------------------------------------------
# Bit-level stuffing (REQ-AX25-007 / REQ-AX25-016).
# ---------------------------------------------------------------------------


def _bits_lsb_first(data: bytes):
    for byte in data:
        for shift in range(8):
            yield (byte >> shift) & 1


def _pack_bits_lsb_first(bits) -> bytes:
    out = bytearray()
    accum = 0
    n = 0
    for bit in bits:
        accum |= (bit & 1) << n
        n += 1
        if n == 8:
            out.append(accum)
            accum = 0
            n = 0
    if n > 0:
        out.append(accum)
    return bytes(out)


def bit_stuff(data: bytes) -> bytes:
    """Insert a 0-bit after every five consecutive 1-bits.

    Operates at bit level across byte boundaries — byte-wise stuffing
    is explicitly incorrect.
    """
    def gen():
        ones = 0
        for bit in _bits_lsb_first(data):
            yield bit
            if bit == 1:
                ones += 1
                if ones == 5:
                    yield 0
                    ones = 0
            else:
                ones = 0
    return _pack_bits_lsb_first(gen())


def bit_unstuff(data: bytes) -> bytes:
    """Inverse of bit_stuff. Raises StuffingViolation on six ones."""
    def gen():
        ones = 0
        for bit in _bits_lsb_first(data):
            if ones == 5:
                if bit == 0:
                    ones = 0
                    continue
                raise StuffingViolation("six consecutive 1-bits")
            yield bit
            ones = ones + 1 if bit == 1 else 0
    return _pack_bits_lsb_first(gen())
