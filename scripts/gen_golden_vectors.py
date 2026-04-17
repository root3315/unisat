"""Generate tests/golden/ax25_vectors.json AND ax25_vectors.inc.

Python is the reference implementation. Both C and Python test runners
consume these fixtures; a mismatch means the C implementation diverged
from the Python one (REQ-AX25-015).

Run from repo root:
  python scripts/gen_golden_vectors.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "ground-station"))

from utils.ax25 import (
    Address, encode_ui_frame, fcs_crc16, encode_address,
)


def encodable(desc: str, reqs: list[str], dst: Address, src: Address,
               info: bytes) -> dict:
    frame = encode_ui_frame(dst, src, 0xF0, info)
    return {
        "kind": "encode",
        "description": desc,
        "reqs": reqs,
        "dst_callsign": dst.callsign,
        "dst_ssid": dst.ssid,
        "src_callsign": src.callsign,
        "src_ssid": src.ssid,
        "pid": 0xF0,
        "info_hex": info.hex(),
        "encoded_hex": frame.hex(),
    }


def raw_decode(desc: str, reqs: list[str], raw_body: bytes,
                expected_status: str) -> dict:
    return {
        "kind": "decode_raw",
        "description": desc,
        "reqs": reqs,
        "raw_body_hex": raw_body.hex(),
        "expected_status": expected_status,
    }


vectors: list[dict] = []

# Category 1: canonical.
vectors.append(encodable(
    "canonical beacon-style frame, 48 B info",
    ["REQ-AX25-001", "REQ-AX25-009"],
    Address("CQ", 0), Address("UN8SAT", 1), bytes(range(48))))
vectors.append(encodable(
    "min-size UI (0 B info)",
    ["REQ-AX25-005"],
    Address("CQ", 0), Address("UN8SAT", 1), b""))
vectors.append(encodable(
    "max-size UI (256 B info)",
    ["REQ-AX25-005"],
    Address("CQ", 0), Address("UN8SAT", 1),
    bytes([i & 0xFF for i in range(256)])))

# Category 2: bit-stuffing adversarial.
vectors.append(encodable(
    "info contains 0x7E bytes",
    ["REQ-AX25-007"],
    Address("CQ", 0), Address("UN8SAT", 1), b"\x7E\x7E\x7E"))
vectors.append(encodable(
    "info all 0xFF (worst-case stuffing growth)",
    ["REQ-AX25-007", "REQ-AX25-011"],
    Address("CQ", 0), Address("UN8SAT", 1), b"\xFF" * 64))
vectors.append(encodable(
    "info 0xFE pattern (5 ones low nibble)",
    ["REQ-AX25-007", "REQ-AX25-016"],
    Address("CQ", 0), Address("UN8SAT", 1), b"\xFE" * 8))
vectors.append(encodable(
    "byte-boundary 5-ones runs (REQ-AX25-016)",
    ["REQ-AX25-016"],
    Address("CQ", 0), Address("UN8SAT", 1), b"\x1F\xF8" * 4))
vectors.append(encodable(
    "alternating 0xFF/0x00",
    ["REQ-AX25-007"],
    Address("CQ", 0), Address("UN8SAT", 1),
    b"\xFF\x00" * 16))

# Category 3: address edge cases.
vectors.append(encodable(
    "short callsign padded with spaces",
    ["REQ-AX25-002"],
    Address("CT", 0), Address("UN", 0), b"X"))
vectors.append(encodable(
    "ssid 0 both sides",
    ["REQ-AX25-002"],
    Address("UN8SAT", 0), Address("UN8SAT", 0), b"X"))
vectors.append(encodable(
    "ssid 15 both sides",
    ["REQ-AX25-002"],
    Address("UN8SAT", 15), Address("UN8SAT", 15), b"X"))
vectors.append(encodable(
    "digits in callsign",
    ["REQ-AX25-002"],
    Address("123456", 0), Address("UN8SAT", 1), b"X"))
vectors.append(encodable(
    "single-char callsigns",
    ["REQ-AX25-002"],
    Address("A", 7), Address("B", 2), b"X"))

# Category 4: digipeater rejection (raw bodies with 3 address fields).
repeater_body = (
    encode_address(Address("CQ", 0), is_last=False)
    + encode_address(Address("UN8SAT", 1), is_last=False)  # H=0 -> more
    + encode_address(Address("REPEAT", 0), is_last=True)
    + b"\x03\xF0X"
)
repeater_body += fcs_crc16(repeater_body).to_bytes(2, "little")
vectors.append(raw_decode(
    "digipeater path MUST be rejected",
    ["REQ-AX25-018"],
    repeater_body,
    "AX25_ERR_ADDRESS_INVALID"))

# Category 5: malformed bodies.
bad_fcs_body = (
    encode_address(Address("CQ", 0), is_last=False)
    + encode_address(Address("UN8SAT", 1), is_last=True)
    + b"\x03\xF0Hi" + b"\xDE\xAD"
)
vectors.append(raw_decode(
    "bad FCS",
    ["REQ-AX25-006"],
    bad_fcs_body,
    "AX25_ERR_FCS_MISMATCH"))

bad_ctrl_body = (
    encode_address(Address("CQ", 0), is_last=False)
    + encode_address(Address("UN8SAT", 1), is_last=True)
    + b"\x99\xF0"
)
bad_ctrl_body += fcs_crc16(bad_ctrl_body).to_bytes(2, "little")
vectors.append(raw_decode(
    "control != 0x03",
    ["REQ-AX25-003"],
    bad_ctrl_body,
    "AX25_ERR_CONTROL_INVALID"))

bad_pid_body = (
    encode_address(Address("CQ", 0), is_last=False)
    + encode_address(Address("UN8SAT", 1), is_last=True)
    + b"\x03\xEE"
)
bad_pid_body += fcs_crc16(bad_pid_body).to_bytes(2, "little")
vectors.append(raw_decode(
    "pid != 0xF0",
    ["REQ-AX25-004"],
    bad_pid_body,
    "AX25_ERR_PID_INVALID"))

# More canonical coverage to reach ≥28.
for info_len in [1, 2, 4, 8, 16, 32, 64, 96, 128, 192, 200]:
    vectors.append(encodable(
        f"encode info_len={info_len}",
        ["REQ-AX25-005"],
        Address("CQ", 0), Address("UN8SAT", 1),
        bytes([(i * 13 + 7) & 0xFF for i in range(info_len)])))

# Emit JSON.
json_path = REPO / "tests" / "golden" / "ax25_vectors.json"
json_path.parent.mkdir(parents=True, exist_ok=True)
json_path.write_text(json.dumps(vectors, indent=2) + "\n")


# Emit C-compatible .inc file (no JSON parser needed in C tests).
def c_byte_array(hex_str: str) -> str:
    if not hex_str:
        return "{ 0 }"  # zero-length arrays are not C89
    bs = bytes.fromhex(hex_str)
    return "{ " + ", ".join(f"0x{b:02X}" for b in bs) + " }"


lines: list[str] = [
    "/* AUTO-GENERATED by scripts/gen_golden_vectors.py. DO NOT EDIT. */",
    "/* Regenerate:  python scripts/gen_golden_vectors.py             */",
    "",
    "#ifndef AX25_GOLDEN_VECTORS_INC",
    "#define AX25_GOLDEN_VECTORS_INC",
    "",
    "#include <stddef.h>",
    "#include <stdint.h>",
    "",
    "typedef struct {",
    "  const char *description;",
    "  int         kind;          /* 0=encode, 1=decode_raw */",
    "  const char *dst_callsign;",
    "  uint8_t     dst_ssid;",
    "  const char *src_callsign;",
    "  uint8_t     src_ssid;",
    "  const uint8_t *info;",
    "  size_t      info_len;",
    "  const uint8_t *encoded;",
    "  size_t      encoded_len;",
    "  const uint8_t *raw_body;",
    "  size_t      raw_body_len;",
    "  const char *expected_status;",
    "} ax25_golden_t;",
    "",
]

# Per-vector byte arrays.
for i, v in enumerate(vectors):
    if v["kind"] == "encode":
        lines.append(
            f"static const uint8_t GV_INFO_{i}[] = "
            f"{c_byte_array(v['info_hex'])};"
        )
        lines.append(
            f"static const uint8_t GV_ENC_{i}[] = "
            f"{c_byte_array(v['encoded_hex'])};"
        )
    else:
        lines.append(
            f"static const uint8_t GV_RAW_{i}[] = "
            f"{c_byte_array(v['raw_body_hex'])};"
        )

lines.append("")
lines.append("static const ax25_golden_t AX25_GOLDEN_VECTORS[] = {")
for i, v in enumerate(vectors):
    if v["kind"] == "encode":
        info_hex = v["info_hex"]
        info_len = len(info_hex) // 2
        enc_len = len(v["encoded_hex"]) // 2
        lines.append(
            "  { "
            f'"{v["description"]}", 0, '
            f'"{v["dst_callsign"]}", {v["dst_ssid"]}, '
            f'"{v["src_callsign"]}", {v["src_ssid"]}, '
            f"GV_INFO_{i}, {info_len}, "
            f"GV_ENC_{i}, {enc_len}, "
            "NULL, 0, NULL },"
        )
    else:
        raw_len = len(v["raw_body_hex"]) // 2
        lines.append(
            "  { "
            f'"{v["description"]}", 1, '
            'NULL, 0, NULL, 0, NULL, 0, NULL, 0, '
            f"GV_RAW_{i}, {raw_len}, "
            f'"{v["expected_status"]}" ' + "},"
        )
lines.append("};")
lines.append("")
lines.append(f"#define AX25_GOLDEN_VECTOR_COUNT {len(vectors)}")
lines.append("")
lines.append("#endif /* AX25_GOLDEN_VECTORS_INC */")

inc_path = REPO / "tests" / "golden" / "ax25_vectors.inc"
inc_path.write_text("\n".join(lines) + "\n")

print(f"Wrote {len(vectors)} vectors:")
print(f"  {json_path.relative_to(REPO)}")
print(f"  {inc_path.relative_to(REPO)}")
