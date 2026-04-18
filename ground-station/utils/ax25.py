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

from dataclasses import dataclass  # noqa: E402


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


# ---------------------------------------------------------------------------
# UI frame encode / pure decode (REQ-AX25-001..015, 018).
# ---------------------------------------------------------------------------

AX25_MAX_INFO_LEN = 256
AX25_MAX_FRAME_BYTES = 400


@dataclass(frozen=True)
class UiFrame:
    dst: Address
    src: Address
    control: int
    pid: int
    info: bytes
    fcs: int
    fcs_valid: bool


def encode_ui_frame(
    dst: Address, src: Address, pid: int, info: bytes,
) -> bytes:
    """Encode a full AX.25 UI frame: flags + body + FCS, bit-stuffed."""
    if len(info) > AX25_MAX_INFO_LEN:
        raise FrameOverflow(f"info {len(info)} > {AX25_MAX_INFO_LEN}")
    body = bytearray()
    body += encode_address(dst, is_last=False)
    body += encode_address(src, is_last=True)
    body.append(0x03)
    body.append(pid & 0xFF)
    body += info
    fcs = fcs_crc16(bytes(body))
    body += fcs.to_bytes(2, "little")
    stuffed = bit_stuff(bytes(body))
    frame = b"\x7E" + stuffed + b"\x7E"
    if len(frame) > AX25_MAX_FRAME_BYTES:
        raise FrameOverflow(
            f"stuffed frame {len(frame)} > {AX25_MAX_FRAME_BYTES}"
        )
    return frame


def decode_ui_frame(body: bytes) -> UiFrame:
    """Decode an UNSTUFFED frame body (no flags). Used by the streaming
    decoder once it has extracted the candidate between two flags."""
    if len(body) < 18:
        raise FrameOverflow(f"body {len(body)} < 18 (minimum UI frame)")

    dst, dst_last = decode_address(body[0:7])
    if dst_last:
        raise InvalidAddress("destination has H-bit set")

    src, src_last = decode_address(body[7:14])
    if not src_last:
        # REQ-AX25-018: a third address would mean a digipeater path.
        raise InvalidAddress(
            "digipeater path not supported (REQ-AX25-018)"
        )

    ctrl = body[14]
    pid = body[15]
    if ctrl != 0x03:
        raise InvalidControl(f"control 0x{ctrl:02X} != 0x03")
    if pid != 0xF0:
        raise InvalidPid(f"pid 0x{pid:02X} != 0xF0")

    info = bytes(body[16:-2])
    if len(info) > AX25_MAX_INFO_LEN:
        raise FrameOverflow(f"info {len(info)} > {AX25_MAX_INFO_LEN}")

    wanted = fcs_crc16(body[:-2])
    got = int.from_bytes(body[-2:], "little")
    fcs_valid = wanted == got
    if not fcs_valid:
        raise FcsMismatch(
            f"expected fcs 0x{wanted:04X}, got 0x{got:04X}"
        )
    return UiFrame(dst, src, ctrl, pid, info, got, fcs_valid)


# ---------------------------------------------------------------------------
# Streaming decoder (REQ-AX25-017/021/023/024).
# Mirrors firmware/stm32/Drivers/AX25/ax25_decoder.c.
# ---------------------------------------------------------------------------


class _State:
    HUNT = 0
    FRAME = 1


class Ax25Decoder:
    """Byte-by-byte AX.25 UI-frame assembler.

    Mirrors firmware/stm32/Drivers/AX25/ax25_decoder.c one-for-one.
    Not thread-safe — one instance per RX stream.
    """

    def __init__(self) -> None:
        self.reset_all()

    def reset_all(self) -> None:
        """Zero per-frame state AND counters. Called on init."""
        self._state = _State.HUNT
        self._buf = bytearray()
        self._shift = 0
        self._bit_count = 0
        self._ones = 0
        self.frames_ok = 0
        self.frames_fcs_err = 0
        self.frames_overflow = 0
        self.frames_stuffing_err = 0
        self.frames_other_err = 0

    def _reset_frame(self) -> None:
        """Reset only the per-frame state; keep counters."""
        self._state = _State.HUNT
        self._buf = bytearray()
        self._shift = 0
        self._bit_count = 0
        self._ones = 0

    def _append_bit(self, bit: int) -> bool:
        self._shift |= (bit & 1) << self._bit_count
        self._bit_count += 1
        if self._bit_count == 8:
            if len(self._buf) >= AX25_MAX_FRAME_BYTES:
                self.frames_overflow += 1
                self._reset_frame()
                return False
            self._buf.append(self._shift & 0xFF)
            self._shift = 0
            self._bit_count = 0
        return True

    def _emit(self):
        self._shift = 0
        self._bit_count = 0
        if len(self._buf) < 18:
            self._reset_frame()
            return None
        try:
            frame = decode_ui_frame(bytes(self._buf))
            self.frames_ok += 1
        except FcsMismatch:
            self.frames_fcs_err += 1
            frame = None
        except AX25Error:
            self.frames_other_err += 1
            frame = None
        self._reset_frame()
        return frame

    def push_byte(self, byte: int):
        """Returns a UiFrame when a valid frame is assembled, else None.

        Malformed frames are counted, the decoder resets to HUNT, but
        NO exception is raised — this must be robust to noisy RF.
        """
        byte &= 0xFF
        if byte == 0x7E:
            if self._state == _State.HUNT:
                # Opening flag.
                self._state = _State.FRAME
                self._buf = bytearray()
                self._shift = 0
                self._bit_count = 0
                self._ones = 0
                return None
            # Closing flag -> emit, then stay open for next frame.
            frame = self._emit()
            self._state = _State.FRAME
            self._buf = bytearray()
            self._shift = 0
            self._bit_count = 0
            self._ones = 0
            return frame

        if self._state == _State.HUNT:
            return None

        # Inside FRAME: consume 8 bits LSB-first with de-stuffing.
        for b in range(8):
            bit = (byte >> b) & 1
            if self._ones == 5:
                if bit == 0:
                    self._ones = 0
                    continue
                # Six consecutive ones — REQ-AX25-024.
                self.frames_stuffing_err += 1
                self._reset_frame()
                return None
            if not self._append_bit(bit):
                return None
            self._ones = self._ones + 1 if bit == 1 else 0
        return None
