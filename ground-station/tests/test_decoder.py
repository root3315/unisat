"""Tests for telemetry decoder."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.telemetry_decoder import decode_obc, decode_beacon, APID_MAP
import struct


def test_apid_map_has_entries():
    assert 0x001 in APID_MAP
    assert APID_MAP[0x001] == "OBC"
    assert APID_MAP[0x0FF] == "Beacon"


def test_decode_obc_valid():
    data = struct.pack("<IIfI", 86400, 2, 35.5, 65536)
    data += bytes([1])  # state
    data += struct.pack("<H", 5)  # errors
    result = decode_obc(data)
    assert result["uptime_s"] == 86400
    assert result["reset_count"] == 2
    assert abs(result["cpu_temp_c"] - 35.5) < 0.01


def test_decode_obc_short_data():
    result = decode_obc(b"\x00" * 5)
    assert result == {}


def test_decode_beacon_valid():
    data = bytes([1])  # state
    data += struct.pack("<I", 3600)  # uptime
    data += struct.pack("<f", 14.2)  # battery_v
    data += struct.pack("<f", 78.5)  # soc
    result = decode_beacon(data)
    assert result["state"] == 1
    assert result["uptime_s"] == 3600
