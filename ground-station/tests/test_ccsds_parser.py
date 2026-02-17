"""Tests for CCSDS parser."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.ccsds_parser import crc16_ccitt, build_packet, parse_packet


def test_crc16_deterministic():
    data = b"hello"
    crc1 = crc16_ccitt(data)
    crc2 = crc16_ccitt(data)
    assert crc1 == crc2
    assert crc1 != 0


def test_crc16_different_data():
    assert crc16_ccitt(b"abc") != crc16_ccitt(b"xyz")


def test_build_and_parse_roundtrip():
    payload = b"\x01\x02\x03\x04\x05"
    raw = build_packet(apid=0x001, subsystem=0, data=payload)
    assert len(raw) > 0

    packet = parse_packet(raw)
    assert packet is not None
    assert packet.apid == 0x001
    assert packet.crc_valid is True
    assert packet.payload == payload


def test_parse_short_data():
    result = parse_packet(b"\x00\x01\x02")
    assert result is None


def test_corrupted_crc():
    raw = build_packet(apid=0x002, subsystem=1, data=b"\xAA")
    corrupted = bytearray(raw)
    corrupted[-1] ^= 0xFF
    packet = parse_packet(bytes(corrupted))
    if packet is not None:
        assert packet.crc_valid is False
