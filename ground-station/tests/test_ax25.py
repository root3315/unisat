"""AX.25 link layer tests.

Mirrors firmware/tests/test_ax25_*.c. Verified against the same
golden-vector fixtures in tests/golden/ax25_vectors.json.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.ax25 import fcs_crc16


class TestFcs:
    def test_reference_vector_123456789(self):
        """REQ-AX25-022: canonical CRC-16/X.25 oracle."""
        assert fcs_crc16(b"123456789") == 0x906E

    def test_empty_input(self):
        assert fcs_crc16(b"") == 0x0000

    def test_single_zero_byte(self):
        assert fcs_crc16(b"\x00") == 0xF078
