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


# ---------------------------------------------------------------------------
# Address encode/decode (REQ-AX25-002, AX.25 v2.2 §3.12).
# ---------------------------------------------------------------------------

from dataclasses import dataclass


@dataclass(frozen=True)
class Address:
    callsign: str
    ssid: int


def _valid_callsign_char(c: str) -> bool:
    return ("A" <= c <= "Z") or ("0" <= c <= "9") or c == " "


def encode_address(addr: Address, is_last: bool) -> bytes:
    """Encode a 7-byte AX.25 address field per §3.12."""
    if not 0 <= addr.ssid <= 15:
        raise InvalidAddress(f"ssid {addr.ssid} out of range (0..15)")
    if len(addr.callsign) > 6:
        raise InvalidAddress(f"callsign {addr.callsign!r} > 6 chars")
    padded = addr.callsign.ljust(6)
    for c in padded:
        if not _valid_callsign_char(c):
            raise InvalidAddress(f"illegal callsign char {c!r}")
    out = bytearray(ord(c) << 1 for c in padded)
    ssid_byte = 0x60 | ((addr.ssid & 0x0F) << 1) | (1 if is_last else 0)
    out.append(ssid_byte)
    return bytes(out)


def decode_address(data: bytes) -> tuple[Address, bool]:
    """Decode a 7-byte address field. Returns (Address, is_last)."""
    if len(data) != 7:
        raise InvalidAddress("address field must be exactly 7 bytes")
    chars = []
    for b in data[:6]:
        c = chr(b >> 1)
        if not _valid_callsign_char(c):
            raise InvalidAddress(f"illegal encoded char 0x{b:02X}")
        chars.append(c)
    callsign = "".join(chars).rstrip()
    ssid_byte = data[6]
    if (ssid_byte & 0x60) != 0x60:
        raise InvalidAddress(
            f"reserved RR bits not set in ssid byte 0x{ssid_byte:02X}"
        )
    ssid = (ssid_byte >> 1) & 0x0F
    is_last = bool(ssid_byte & 1)
    return Address(callsign, ssid), is_last
