"""AX.25 link layer tests.

Mirrors firmware/tests/test_ax25_*.c. Verified against the same
golden-vector fixtures in tests/golden/ax25_vectors.json.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))



import pytest
from hypothesis import given, strategies as st, settings

from utils.ax25 import (
    fcs_crc16, bit_stuff, bit_unstuff, StuffingViolation,
    Address, encode_address, decode_address, InvalidAddress,
    UiFrame, encode_ui_frame, decode_ui_frame,
    FcsMismatch, InvalidControl, InvalidPid, FrameOverflow,
    Ax25Decoder, AX25Error,
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


class TestUiFrame:
    def test_round_trip(self):
        dst = Address("CQ", 0)
        src = Address("UN8SAT", 1)
        frame_bytes = encode_ui_frame(dst, src, 0xF0, b"Hi")
        assert frame_bytes[0] == 0x7E
        assert frame_bytes[-1] == 0x7E

        # Strip flags, unstuff to get the body back.
        body = bit_unstuff(frame_bytes[1:-1])
        decoded = decode_ui_frame(body)
        assert decoded.dst == dst
        assert decoded.src == src
        assert decoded.control == 0x03
        assert decoded.pid == 0xF0
        assert decoded.info == b"Hi"
        assert decoded.fcs_valid is True

    def test_encode_rejects_info_too_long(self):
        with pytest.raises(FrameOverflow):
            encode_ui_frame(
                Address("CQ", 0), Address("UN8SAT", 1),
                0xF0, b"\x00" * 257,
            )

    def test_decode_rejects_digipeater_path(self):
        """REQ-AX25-018: third address field must be rejected."""
        d = encode_address(Address("CQ", 0), is_last=False)
        s = encode_address(Address("UN8SAT", 1), is_last=False)  # H=0
        r = encode_address(Address("REPEAT", 0), is_last=True)
        body = d + s + r + b"\x03\xF0X"
        body += fcs_crc16(body).to_bytes(2, "little")
        with pytest.raises(InvalidAddress):
            decode_ui_frame(body)

    def test_decode_rejects_bad_fcs(self):
        d = encode_address(Address("CQ", 0), is_last=False)
        s = encode_address(Address("UN8SAT", 1), is_last=True)
        body = d + s + b"\x03\xF0Hi\xDE\xAD"
        with pytest.raises(FcsMismatch):
            decode_ui_frame(body)

    def test_decode_rejects_bad_control(self):
        d = encode_address(Address("CQ", 0), is_last=False)
        s = encode_address(Address("UN8SAT", 1), is_last=True)
        body = d + s + b"\x99\xF0"
        body += fcs_crc16(body).to_bytes(2, "little")
        with pytest.raises(InvalidControl):
            decode_ui_frame(body)

    def test_decode_rejects_bad_pid(self):
        d = encode_address(Address("CQ", 0), is_last=False)
        s = encode_address(Address("UN8SAT", 1), is_last=True)
        body = d + s + b"\x03\xEE"
        body += fcs_crc16(body).to_bytes(2, "little")
        with pytest.raises(InvalidPid):
            decode_ui_frame(body)


class TestGoldenVectors:
    """REQ-AX25-015: C + Python MUST produce bit-identical output
    against the shared fixture set."""

    @pytest.fixture(scope="class")
    def vectors(self):
        import json
        path = (Path(__file__).resolve().parents[2]
                / "tests" / "golden" / "ax25_vectors.json")
        return json.loads(path.read_text())

    def test_vector_file_has_at_least_28_entries(self, vectors):
        assert len(vectors) >= 28

    def test_encode_vectors_match_generator_output(self, vectors):
        """Sanity: Python regenerates the same bytes it recorded."""
        checked = 0
        for v in vectors:
            if v["kind"] != "encode":
                continue
            frame = encode_ui_frame(
                Address(v["dst_callsign"], v["dst_ssid"]),
                Address(v["src_callsign"], v["src_ssid"]),
                v["pid"],
                bytes.fromhex(v["info_hex"]),
            )
            assert frame.hex() == v["encoded_hex"], v["description"]
            checked += 1
        assert checked >= 20

    _STATUS_TO_EXC = {
        "AX25_ERR_ADDRESS_INVALID": InvalidAddress,
        "AX25_ERR_FCS_MISMATCH":    FcsMismatch,
        "AX25_ERR_CONTROL_INVALID": InvalidControl,
        "AX25_ERR_PID_INVALID":     InvalidPid,
    }

    def test_decode_raw_vectors(self, vectors):
        checked = 0
        for v in vectors:
            if v["kind"] != "decode_raw":
                continue
            expected_exc = self._STATUS_TO_EXC[v["expected_status"]]
            with pytest.raises(expected_exc):
                decode_ui_frame(bytes.fromhex(v["raw_body_hex"]))
            checked += 1
        assert checked >= 4


class TestStreamingDecoder:
    def test_single_frame(self):
        dst = Address("CQ", 0)
        src = Address("UN8SAT", 1)
        frame = encode_ui_frame(dst, src, 0xF0, b"Hi")
        dec = Ax25Decoder()
        frames = [f for b in frame if (f := dec.push_byte(b)) is not None]
        assert len(frames) == 1
        assert frames[0].info == b"Hi"
        assert dec.frames_ok == 1

    def test_idle_flags_ignored(self):
        dec = Ax25Decoder()
        for _ in range(10):
            assert dec.push_byte(0x7E) is None
        assert dec.frames_ok == 0
        assert dec.frames_other_err == 0

    def test_back_to_back_frames(self):
        dst = Address("CQ", 0); src = Address("UN8SAT", 1)
        a = encode_ui_frame(dst, src, 0xF0, b"A")
        b = encode_ui_frame(dst, src, 0xF0, b"B")
        dec = Ax25Decoder()
        infos = []
        for byte in a + b:
            f = dec.push_byte(byte)
            if f:
                infos.append(f.info)
        assert infos == [b"A", b"B"]
        assert dec.frames_ok == 2

    def test_recovers_after_garbage(self):
        dec = Ax25Decoder()
        dec.push_byte(0x7E)
        for _ in range(50):
            dec.push_byte(0xFF)
        # After garbage, decoder MUST be usable again.
        dst = Address("CQ", 0); src = Address("UN8SAT", 1)
        frame = encode_ui_frame(dst, src, 0xF0, b"X")
        good = [f for b in frame if (f := dec.push_byte(b)) is not None]
        assert len(good) == 1
        assert good[0].info == b"X"


class TestHypothesis:
    """REQ-AX25-014: decoder never raises uncaught exceptions."""

    @given(
        dst_call=st.text(
            alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
            min_size=1, max_size=6),
        src_call=st.text(
            alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
            min_size=1, max_size=6),
        dst_ssid=st.integers(0, 15),
        src_ssid=st.integers(0, 15),
        info=st.binary(max_size=200),
    )
    @settings(max_examples=200, deadline=None)
    def test_encode_decode_round_trip_property(
        self, dst_call, src_call, dst_ssid, src_ssid, info,
    ):
        """Encode -> stream through Ax25Decoder -> must recover the
        original frame. We use the streaming decoder (not raw unstuff)
        because bit-level stuffing may add a non-byte-aligned pad at
        the end; the 0x7E flag boundary resolves that."""
        dst = Address(dst_call, dst_ssid)
        src = Address(src_call, src_ssid)
        frame = encode_ui_frame(dst, src, 0xF0, info)
        dec = Ax25Decoder()
        frames = [f for b in frame if (f := dec.push_byte(b)) is not None]
        assert len(frames) == 1
        assert frames[0].dst == dst
        assert frames[0].src == src
        assert frames[0].info == info

    @given(stream=st.binary(max_size=2048))
    @settings(max_examples=500, deadline=None)
    def test_decoder_never_crashes_on_garbage(self, stream):
        dec = Ax25Decoder()
        try:
            for b in stream:
                dec.push_byte(b)
        except AX25Error:
            pytest.fail("push_byte must not raise — errors are counted")


class TestHmac:
    """Cross-verify Python HMAC-SHA256 against RFC 4231 test vectors.
    The C-side (firmware/stm32/Drivers/Crypto/hmac_sha256.c) asserts
    the same vectors — if both pass, the implementations agree."""

    def test_rfc4231_case1(self):
        from utils.hmac_auth import hmac_sha256
        key = b"\x0b" * 20
        tag = hmac_sha256(key, b"Hi There")
        assert tag.hex() == (
            "b0344c61d8db38535ca8afceaf0bf12b"
            "881dc200c9833da726e9376c2e32cff7"
        )

    def test_rfc4231_case2(self):
        from utils.hmac_auth import hmac_sha256
        tag = hmac_sha256(b"Jefe", b"what do ya want for nothing?")
        assert tag.hex() == (
            "5bdcc146bf60754e6a042426089575c7"
            "5a003f089d2739839dec58b964ec3843"
        )

    def test_verify_constant_time(self):
        from utils.hmac_auth import verify, HMAC_TAG_SIZE
        a = b"\x00" * HMAC_TAG_SIZE
        b = b"\x00" * HMAC_TAG_SIZE
        assert verify(a, b) is True
        b = b"\x00" * (HMAC_TAG_SIZE - 1) + b"\x01"
        assert verify(a, b) is False
