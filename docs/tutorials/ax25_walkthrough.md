# AX.25 Walkthrough: Decoding a Real Beacon

This tutorial walks one captured beacon from wire bytes to decoded
telemetry. All numbers come from Python: you can reproduce every step
with the tools in `ground-station/`.

## 1. Build a canonical beacon

Use the Python library to encode a beacon with callsigns `CQ-0` (dest)
and `UN8SAT-1` (source), 48-byte info payload of `0x00..0x2F`:

```python
from utils.ax25 import Address, encode_ui_frame

frame = encode_ui_frame(
    Address("CQ", 0),
    Address("UN8SAT", 1),
    pid=0xF0,
    info=bytes(range(48)),
)
print(frame.hex())
```

The output is **exactly** what the C firmware transmits via
`AX25_EncodeUiFrame` — the cross-validation in Phase 3 proves it.

## 2. Byte map

```
7E  86 A2 40 40 40 40 60  AA 9C 70 A6 82 A8 63  03 F0   <info 48 B>  FF FF   7E
│   └─────── dst ───────┘ └──────── src ──────┘ │  │    │             │   │   │
│                                               │  │    │             │   │   end flag
│                                               │  │    │             │   FCS lo/hi (LE)
│                                               │  │    CCSDS / beacon payload
│                                               │  PID 0xF0 (no layer 3)
│                                               UI control 0x03
start flag
```

### 2.1 Start flag (1 byte)

`0x7E` — HDLC flag. Never bit-stuffed.

### 2.2 Destination address (7 bytes)

Each callsign character is **left-shifted by 1 bit**:

| Byte | Value | Decode |
|------|-------|--------|
| 0 | 0x86 | `0x86 >> 1 = 0x43 = 'C'` |
| 1 | 0xA2 | `0xA2 >> 1 = 0x51 = 'Q'` |
| 2 | 0x40 | `0x40 >> 1 = 0x20 = ' '` (space padding) |
| 3..5 | 0x40 | spaces |
| 6 | 0x60 | SSID byte |

SSID byte 0x60 = `0110 0000`:

```
bit:  7 6 5 4 3 2 1 0
       0 1 1 S S S S H
       C R R ─── ─── │
                     └─ H = 0 (another address follows)
       C = 0 (response), RR = 11 (reserved, always 1)
       SSID = 0 (callsign CQ-0)
```

### 2.3 Source address (7 bytes)

`UN8SAT-1` with H-bit set (this is the last address — REQ-AX25-018
rejects any third address field).

SSID byte for UN8SAT with `ssid=1` and `H=1`:
`0x60 | (1 << 1) | 1 = 0x63`.

### 2.4 Control + PID

`0x03` = UI frame (unnumbered information).
`0xF0` = no layer-3 protocol; the info field is raw bytes for the
application to interpret.

### 2.5 Info field (0..256 bytes)

Arbitrary payload. For a UniSat beacon, exactly 48 bytes matching the
spec §7.2 layout (uptime, mode, V/I/SOC, quaternion, lat/lon, …).

### 2.6 FCS (2 bytes, little-endian on the wire)

CRC-16/X.25 over **address + control + PID + info** (NOT including the
flags). Polynomial 0x1021 reflected (0x8408), init 0xFFFF, final XOR
0xFFFF. The canonical oracle:

```python
>>> fcs_crc16(b"123456789")
0x906E
```

### 2.7 End flag (1 byte)

`0x7E` — closes the frame. A back-to-back frame may reuse this flag as
its own start (REQ-AX25-023).

## 3. Bit-stuffing: why it matters

Between the flags, the transmitter walks the payload as an **LSB-first
bit stream** and inserts a `0` bit after every five consecutive `1`
bits. This guarantees that a byte-aligned `0x7E` can never appear
inside a frame body — flag matching stays unambiguous.

Example: input bit stream `1,1,1,1,1,0,0,0` (byte `0x1F`) gets
stuffed to `1,1,1,1,1,0,0,0,0` — the inserted `0` (same value as the
natural next bit) is dropped on the receive side.

The receiver runs the inverse: drop the bit after any five 1s; six 1s
in a row is a protocol violation and aborts the current frame
(REQ-AX25-024).

See `firmware/stm32/Drivers/AX25/ax25.c` — functions
`ax25_bit_stuff` / `ax25_bit_unstuff` — for the exact implementation,
and `ground-station/utils/ax25.py` for the Python mirror.

## 4. Try it live

```bash
# Terminal 1: listen for beacons on TCP loopback.
cd ground-station
python -m cli.ax25_listen --port 52100

# Terminal 2: run the firmware SITL demo.
cd firmware && cmake -B build -S . && cmake --build build --target sitl_fw
./build/sitl_fw 52100
```

The listener prints one JSON line per beacon. The C encoder and the
Python decoder produce byte-identical results over the real TCP path.
