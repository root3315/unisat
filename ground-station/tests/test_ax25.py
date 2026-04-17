"""AX.25 link layer tests.

Mirrors firmware/tests/test_ax25_*.c. Verified against the same
golden-vector fixtures in tests/golden/ax25_vectors.json.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from utils.ax25 import (
    fcs_crc16, bit_stuff, bit_unstuff, StuffingViolation,
    Address, encode_address, decode_address, InvalidAddress,
)


class TestFcs:
    def test_reference_vector_123456789(self):
        """REQ-AX25-022: canonical CRC-16/X.25 oracle."""
        assert fcs_crc16(b"123456789") == 0x906E

    def test_empty_input(self):
        assert fcs_crc16(b"") == 0x0000

    def test_single_zero_byte(self):
        assert fcs_crc16(b"\x00") == 0xF078


class TestBitStuff:
    def test_all_ones_byte_inserts_one_zero(self):
        # 0xFF LSB-first bits 1,1,1,1,1,1,1,1 -> stuff 0 after 5 ones.
        # Result 9 bits: 1,1,1,1,1,0,1,1,1 packed LSB-first = 0xDF, 0x01.
        assert bit_stuff(b"\xFF") == bytes([0xDF, 0x01])

    def test_no_ones_unchanged(self):
        assert bit_stuff(b"\x00\x00") == b"\x00\x00"

    def test_across_byte_boundary(self):
        # REQ-AX25-016: 0x1F,0xF8 -> 0x1F,0xF0,0x01 after two stuffs.
        assert bit_stuff(b"\x1F\xF8") == bytes([0x1F, 0xF0, 0x01])

    def test_unstuff_recovers_original_prefix(self):
        # Byte roundtrip may gain a trailing zero-pad byte; the first
        # len(original) bytes MUST match.
        original = b"\x12\xFF\x34"
        recovered = bit_unstuff(bit_stuff(original))
        assert recovered[:len(original)] == original

    def test_six_ones_rejected(self):
        # 0x3F LSB-first = 1,1,1,1,1,1,0,0 — six 1s = violation.
        with pytest.raises(StuffingViolation):
            bit_unstuff(b"\x3F")


class TestAddress:
    def test_encode_simple(self):
        enc = encode_address(Address("UN8SAT", 1), is_last=False)
        assert enc[:6] == bytes([c << 1 for c in b"UN8SAT"])
        assert enc[6] == 0x62

    def test_encode_padded_short_callsign(self):
        enc = encode_address(Address("CQ", 0), is_last=False)
        assert enc[:6] == bytes([
            ord("C") << 1, ord("Q") << 1,
            ord(" ") << 1, ord(" ") << 1, ord(" ") << 1, ord(" ") << 1,
        ])
        assert enc[6] == 0x60

    def test_encode_last_sets_h_bit(self):
        enc = encode_address(Address("UN8SAT", 1), is_last=True)
        assert enc[6] == 0x63

    def test_round_trip(self):
        addr = Address("UN8SAT", 1)
        enc = encode_address(addr, is_last=True)
        got, is_last = decode_address(enc)
        assert got == addr
        assert is_last is True

    def test_decode_trims_padding(self):
        enc = encode_address(Address("CQ", 0), is_last=False)
        got, is_last = decode_address(enc)
        assert got == Address("CQ", 0)
        assert is_last is False

    def test_decode_rejects_lowercase(self):
        # 0xC2 = 'a' << 1 — lowercase invalid.
        bad = bytes([0xC2, 0x40, 0x40, 0x40, 0x40, 0x40, 0x63])
        with pytest.raises(InvalidAddress):
            decode_address(bad)

    def test_encode_rejects_bad_ssid(self):
        with pytest.raises(InvalidAddress):
            encode_address(Address("UN8SAT", 16), is_last=False)

    def test_encode_rejects_long_callsign(self):
        with pytest.raises(InvalidAddress):
            encode_address(Address("TOOLONG", 0), is_last=False)
