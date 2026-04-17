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
