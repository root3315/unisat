# Track 1 — AX.25 Link Layer: Design Spec

**Status**: Approved
**Date**: 2026-04-17
**Author**: UniSat engineering
**Track**: 1 of 4 (Protocol Completion)

---

## 1. Goals

1. Implement the AX.25 UI-frame link layer fully specified in
   `docs/communication_protocol.md` §7 — both on the satellite (STM32 firmware)
   and on the ground station (Python).
2. Provide a reproducible end-to-end demonstration:
   `make demo` sends a beacon from the firmware (in SITL), and the ground
   station decodes and displays it.
3. Close the two audit findings that formally remain:
   - `comm.c:139` is a `Placeholder for AX.25 frame parsing`.
   - CSP (CubeSat Space Protocol) is not implemented. This is resolved by a
     written architectural decision record (ADR-001), not by adding CSP code.
4. Reach a level of documentation, traceability, and testing that a third-party
   reviewer (jury member or student) can walk the code and reproduce every
   claim without running a physical board.

## 2. Non-Goals

- HMAC / replay protection (CCSDS-level; separate track).
- Full `libcsp` port (see ADR-001).
- Driver audit / other audit findings (Tracks 2-4).
- Changes to the Streamlit UI of the ground station.
- Radio modem hardware abstraction (CC1125 driver is out of scope; we
  interface with the existing UART abstraction).

## 3. Reference Documents

- `docs/communication_protocol.md` §7 — AX.25 UI Frame Format.
- AX.25 Link Access Protocol for Amateur Packet Radio, v2.2, 1998.
- Google C++ Style Guide (applied to pure library C11 code).
- Google Python Style Guide (applied to `utils/ax25.py` and CLI).
- CCSDS 133.0-B-2 — Space Packet Protocol (carried inside AX.25 info field).

## 4. Architecture

### 4.1 Layered Model

```
L4  DEMO ORCHESTRATION
      scripts/demo.py — spawns fw-SITL, GS listener, TCP bridge
L3  APPLICATION (existing, minimal touch)
      comm.c, telemetry.c        Streamlit UI, CLI tools
L2  STYLE ADAPTER (new, thin)
      ax25_api.h → AX25_Xxx()    ax25_client.py (Pythonic)
L1  PURE AX.25 LIBRARY (new, core)
      Drivers/AX25/ax25.c/.h     utils/ax25.py
      ───── shared source of truth: tests/golden/ax25_vectors.json ─────
```

Each layer depends only on the one below; no sibling dependencies.

### 4.2 Style Adapter — Conflict Resolution

Existing firmware uses `PascalCase_Xxx()` + `xxx_t` types (embedded-HAL
convention). The pure library uses Google C++ snake_case. To avoid a
half-and-half mix inside a single translation unit, a static-inline facade
exposes project-style names:

```c
/* Public project-facing API in ax25_api.h */
static inline bool AX25_EncodeUiFrame(
    const AX25_Address_t *dst, const AX25_Address_t *src,
    uint8_t pid, const uint8_t *info, uint16_t info_len,
    uint8_t *out_buf, uint16_t out_cap, uint16_t *out_len) {
  size_t len_tmp = 0;
  ax25_status_t s = ax25_encode_ui_frame(dst, src, pid, info, info_len,
                                         out_buf, out_cap, &len_tmp);
  *out_len = (uint16_t)len_tmp;
  return s == AX25_OK;
}
```

Documented in ADR-002.

### 4.3 Cross-Platform Virtual Radio (SITL)

TCP loopback `127.0.0.1:52100` replaces a potential Unix socket (which is
not portable to pre-Win10 hosts and behaves differently under CI).

In `SIMULATION_MODE`, a shim (`Drivers/VirtualUART/virtual_uart.c`) replaces
`HAL_UART_Transmit` and `HAL_UART_Receive_IT` with TCP-backed equivalents.
Firmware application code is unchanged.

**SITL Limitations (explicit)**

SITL provides functional correctness validation only. It does NOT reproduce:

- Inter-byte timing jitter from a real UART clock.
- Burst / noise patterns of an RF link.
- ISR pressure from asynchronous byte arrival.

SITL SHALL NOT be used for timing validation. Timing validation is deferred
to Track 3 (Renode / QEMU / HIL with a real CC1125 transceiver).

### 4.4 Requirement Traceability

Every bullet in `docs/communication_protocol.md` §7 receives an ID of the form
`REQ-AX25-NNN`. A matrix in `docs/verification/ax25_trace_matrix.md` maps:

```
REQ-AX25-NNN → test file : test name → golden vector(s) → status
```

The matrix is auto-generated from test docstrings by
`scripts/gen_trace_matrix.py`.

### 4.5 Pre-Flight Prerequisites

The following upstream issues MUST be verified, and fixed if broken, before
the main AX.25 implementation begins. They are tracked in a separate
artifact: `docs/superpowers/specs/2026-04-17-track1-preflight.md`.

1. `Telemetry_PackBeacon()` emits exactly the 48-byte layout from
   `communication_protocol.md` §7.2.
2. `ccsds.c` builds a valid CCSDS Space Packet including secondary header.
3. `HAL_UART_Transmit` timeout in `config.h` is raised from 100 ms to
   500 ms — a worst-case bit-stuffed 320-byte frame at 9600 bps takes 266 ms.

### 4.6 Performance Budget

| Metric                        | Budget                     | Rationale                                   |
| ----------------------------- | -------------------------- | ------------------------------------------- |
| Encode time                   | < 5 ms @ 168 MHz           | Beacon cadence 30 s                         |
| Decode time                   | < 2 ms per frame           | Decoder runs in task (see §4.10), not ISR   |
| Flash footprint               | < 6 KB (incl. 512 B CRC)   | STM32F446 has 512 KB                        |
| Static RAM (library)          | 1 × `ax25_decoder_t` (~430 B) + encode scratch (~400 B) | STM32F446 has 128 KB |
| Worst-case stuffing growth    | +20 % of frame size        | All-0xFF info produces maximum stuffing     |
| UART TX timeout (raised)      | 500 ms                     | Covers 266 ms worst-case transmission       |

Full throughput derivation is in §4.11. Threading invariants that make
the decode budget meaningful are in §4.10.

### 4.7 Security — Threat Model

AX.25 is an unauthenticated link layer. Attacks and mitigations:

- **Injection**: any party with an RF transmitter can insert a frame.
  Mitigation: CCSDS-level HMAC authentication (Track 1b, separate track).
- **Replay**: AX.25 has no link-layer sequence numbers.
  Mitigation: CCSDS secondary header provides sequence + timestamp; command
  dispatcher rejects stale or duplicate packets (Track 1b).
- **Bit-stuffing DoS**: a crafted stream could inflate CPU cost in the
  decoder. Mitigation: the decoder hard-rejects any frame larger than
  `AX25_MAX_FRAME_BYTES` (400 B by default; see §5.1a) at every stage
  (flag scanner, unstuffer, parser).

Documented in `docs/security/ax25_threat_model.md`.

### 4.8 Blast Radius / Rollback

- `ENABLE_AX25_FRAMING` feature flag in `config.h` (default: on).
- Library is self-contained in `Drivers/AX25/` — removed by deleting the
  folder and one line in `CMakeLists.txt`.
- Streamlit UI is untouched; existing dashboards keep working.

### 4.9 Educational Layer (Explicit Override)

For goal B (educational flagship) the project default of "no comments
unless the WHY is non-obvious" is explicitly relaxed within this track:

- Block comments in `ax25.c` with inline references to AX.25 v2.2 §X.Y.
- `docs/tutorials/ax25_walkthrough.md` — byte-by-byte walkthrough of one
  real frame with diagrams.
- Optional `notebooks/ax25_interactive.ipynb` — interactive visualization
  of bit-stuffing and FCS.

### 4.10 Threading Model (FreeRTOS)

Strict separation between interrupt context and task context.

```
┌──────────────────────── UART RX interrupt ──────────────────────────┐
│ HAL_UART_RxCpltCallback                                             │
│   └─ COMM_UART_RxCallback(byte)                                     │
│        └─ ring buffer push (volatile head/tail, no locks)           │
│   [CONSTRAINT] no decode, no memcpy > 1 byte, no logging            │
└──────────────────────────────────────────────────────────────────────┘
                              │
                              ▼  (lock-free SPSC ring buffer, 512 B)
┌──────────────────────── comm_rx_task (FreeRTOS) ────────────────────┐
│ priority:     osPriorityAboveNormal (existing convention)           │
│ stack:        1024 B                                                │
│ period:       10 ms (tick notification) or signal on ring fill      │
│   loop:                                                             │
│     while (ring_not_empty):                                         │
│         byte = ring_pop()                                           │
│         status = ax25_decoder_push_byte(&dec, byte, &frame, &rdy)   │
│         if (rdy):                                                   │
│             CCSDS_Dispatcher_Submit(&frame.info[0], frame.info_len) │
└──────────────────────────────────────────────────────────────────────┘
```

**Invariants**:

- The AX.25 decoder NEVER runs in interrupt context.
- The ISR performs a single `uint8_t` push and nothing else.
- The library has ZERO dependency on FreeRTOS or HAL — those dependencies
  live entirely in `comm.c` and the task wrapper.
- One `ax25_decoder_t` instance per RX channel. Decoders are not shared
  across threads.

**Worst-case latency analysis**:

```
Ring buffer depth:       512 B
UART bit rate:           9600 bps → 1200 B/s
Full-buffer drain time:  512 / 1200 = 427 ms

Task period:             10 ms → up to 12 bytes buffered between wakeups
Backlog headroom:        512 - 12 = 500 B (40× safety factor)
```

The ring buffer can hold 427 ms of incoming UART data. The task runs
every 10 ms, so it only needs to drain ~12 bytes per wakeup. Overflow is
physically impossible under nominal conditions at 9600 bps.

### 4.11 Throughput Budget

All numbers derived for the worst-case bit-stuffed frame (+20 % growth).

```
Bit rate:                  9600 bps
Byte rate:                 1200 B/s
Max stuffed frame:         400 B (configurable, see §5.7)
Wire time per frame:       400 / 1200 = 333 ms
Max frame rate:            3.0 frames/s

Per-frame decoder cost:    < 2 ms (budget from §4.6)
CPU time/s at max load:    3.0 × 2 ms = 6 ms/s
CPU utilization:           6 ms / 1000 ms = 0.6 %

Decoder throughput ceiling: 1000 / 2 = 500 frames/s
Safety margin over radio:  500 / 3 = 166× headroom
```

**Conclusion**: The decoder cannot saturate the CPU under any physically
realizable UART load. The ring buffer provides 427 ms of absorb capacity
against scheduling jitter. No backpressure mechanism is required at the
link layer at 9600 bps. If the UART bit rate ever rises above ~480 kbps
(400× nominal), this budget must be re-derived.

---

## 5. Components

### 5.1 C Library (`firmware/stm32/Drivers/AX25/`)

- `ax25.h` — public pure-library API (snake_case).
- `ax25.c` — implementation (encode, batch-decode, FCS, bit-stuffing).
- `ax25_decoder.h` / `ax25_decoder.c` — streaming decoder (stateful).
- `ax25_api.h` — `static inline` facade (`AX25_Xxx()`).
- `ax25_types.h` — `ax25_address_t`, `ax25_ui_frame_t`, `ax25_status_t`,
  `ax25_decoder_t`.

**Pure / stateless API** (used internally by the streaming decoder, and
directly in unit tests where a complete frame is given):

```c
ax25_status_t ax25_encode_ui_frame(
    const ax25_address_t *dst, const ax25_address_t *src,
    uint8_t pid,
    const uint8_t *info, size_t info_len,
    uint8_t *out, size_t out_cap, size_t *out_len);

ax25_status_t ax25_decode_ui_frame(
    const uint8_t *in, size_t in_len,
    ax25_ui_frame_t *out_frame);

uint16_t ax25_fcs_crc16(const uint8_t *data, size_t len);

size_t ax25_bit_stuff(const uint8_t *in, size_t in_len,
                       uint8_t *out, size_t out_cap);

size_t ax25_bit_unstuff(const uint8_t *in, size_t in_len,
                         uint8_t *out, size_t out_cap);
```

**Streaming decoder** (first-class stateful type, consumed byte-by-byte
from the `comm_rx_task`):

```c
typedef enum {
  AX25_STATE_HUNT,       /* scanning for opening 0x7E flag                */
  AX25_STATE_FRAME       /* inside frame, accumulating bits into shift reg*/
} ax25_decoder_state_t;

typedef struct {
  uint8_t              buf[AX25_MAX_FRAME_BYTES];  /* assembled bytes     */
  size_t               len;                        /* bytes written so far*/
  uint16_t             shift_reg;                  /* bit-level state     */
  uint8_t              bit_count;                  /* bits in shift_reg   */
  uint8_t              ones_run;                   /* consecutive-1 counter*/
  ax25_decoder_state_t state;
  uint32_t             frames_ok;                  /* statistics          */
  uint32_t             frames_fcs_err;
  uint32_t             frames_overflow;
} ax25_decoder_t;

void ax25_decoder_init(ax25_decoder_t *d);
void ax25_decoder_reset(ax25_decoder_t *d);

/* Returns:
 *   AX25_OK              — byte consumed; *frame_ready == true means
 *                          *out_frame is populated with a valid frame.
 *   AX25_ERR_*           — byte consumed but produced a malformed frame
 *                          (counter incremented); *frame_ready == false;
 *                          decoder is back in AX25_STATE_HUNT.
 *
 * This function NEVER returns without consuming the byte. It NEVER blocks.
 * It NEVER allocates. It is safe to call at up to the CPU's clock rate,
 * but the spec guarantees correctness at ≤ 480 kbps (see §4.11).
 */
ax25_status_t ax25_decoder_push_byte(
    ax25_decoder_t *d,
    uint8_t byte,
    ax25_ui_frame_t *out_frame,
    bool *frame_ready);
```

**Key design properties**:

- **Inversion of dependency**: `comm.c` depends on `ax25_decoder_t`;
  the decoder does not depend on `comm.c`, HAL, or FreeRTOS.
- **One decoder instance per RX channel.** Not thread-safe by design —
  the decoder runs in exactly one task (`comm_rx_task`).
- **No malloc.** The 400-byte assembly buffer is embedded in the struct.
- **Bit-level state machine**. `shift_reg` + `bit_count` + `ones_run`
  track bits across byte boundaries — satisfies REQ-AX25-016.
- **Non-destructive on error.** A malformed byte returns an error status,
  increments a counter, resets the decoder to `AX25_STATE_HUNT`, but
  never corrupts or leaks state.
- **Pure decoder still exists.** `ax25_decode_ui_frame()` is used by
  the streaming decoder internally (to validate/parse a complete frame
  once the closing flag is found) and is directly callable from unit
  tests and offline tools.

### 5.1a Configurable Limits (`config.h`)

All hard limits surface as compile-time constants — no magic numbers in
library code:

```c
#define AX25_MAX_INFO_LEN        256  /* bytes; AX.25 v2.2 hard max   */
#define AX25_MAX_FRAME_BYTES     400  /* stuffed; margin above +20%    */
#define AX25_RING_BUFFER_SIZE    512  /* UART RX ring; 427 ms @ 9600  */
#define AX25_DECODER_TASK_STACK  1024 /* bytes                         */
#define AX25_DECODER_TASK_PRIO   osPriorityAboveNormal
```

Library code references these symbolically. Tests override them via
`-D` for boundary-case exercises.

### 5.2 Python Library (`ground-station/utils/ax25.py`)

Mirrors the C library one-for-one; shares golden vectors.

- `@dataclass(frozen=True)` types: `Address(callsign: str, ssid: int)`,
  `UiFrame(dst: Address, src: Address, pid: int, info: bytes, fcs: int,
  fcs_valid: bool)`.

**Pure / stateless functions**:
`encode_ui_frame`, `decode_ui_frame`, `fcs_crc16`, `bit_stuff`,
`bit_unstuff`.

**Streaming decoder** (class `Ax25Decoder`):

```python
class Ax25Decoder:
    def __init__(self) -> None: ...
    def reset(self) -> None: ...
    def push_byte(self, byte: int) -> Optional[UiFrame]:
        """Feed one byte. Returns a UiFrame when a complete valid frame
        is assembled, else None. Malformed frames raise AX25Error and
        reset the decoder to HUNT state."""
```

**Exception hierarchy**:

```
AX25Error
├── FcsMismatch
├── FrameOverflow
├── InvalidAddress
├── InvalidControl
├── InvalidPid
├── StuffingViolation
└── DigipeaterUnsupported
```

### 5.3 Virtual UART Shim (SIM-only)

`firmware/stm32/Drivers/VirtualUART/virtual_uart.{c,h}` — compiled only when
`SIMULATION_MODE=1`. Connects to `127.0.0.1:52100` as a TCP client,
replaces HAL UART functions via link-time substitution.

### 5.4 Ground-Station CLI (`ground-station/cli/`)

- `ax25_listen.py` — TCP client, decodes incoming frames, prints JSON.
- `ax25_send.py` — reads hex/JSON input, encodes, sends over TCP.

### 5.5 Integration Touchpoints in Existing Code

Integration inverts the existing dependency: the AX.25 streaming decoder
owns the link-layer state machine; `comm.c` is the consumer.

- `comm.c`:
  - Adds a file-static `ax25_decoder_t g_uhf_decoder;`
    initialised in `COMM_Init()`.
  - `COMM_UART_RxCallback()` (ISR) — unchanged; still pushes one byte
    to the ring buffer.
  - `COMM_ProcessRxBuffer()` — replaced. Now drains the ring buffer and
    calls `ax25_decoder_push_byte()` per byte. On `frame_ready`, passes
    `frame.info[]` to the CCSDS dispatcher.
  - New function `COMM_SendAX25(channel, dst, src, info, info_len)` —
    calls `ax25_encode_ui_frame()` then the existing UART transmit path.
- `comm.h` — adds `ax25_frames_ok`, `ax25_fcs_errors`, `ax25_frame_errors`,
  `ax25_overflow_errors` to `COMM_Status_t` (mirrored from decoder stats).
- `config.h` — adds `ENABLE_AX25_FRAMING` feature flag and the
  `AX25_MAX_*` / `AX25_DECODER_*` compile-time constants from §5.1a.
- FreeRTOS task `comm_rx_task` (either new or existing) polls the ring
  buffer every 10 ms per §4.10.

### 5.6 Orchestration

- `scripts/demo.py` — spawns fw-SITL and GS listener, pipes stdout.
- `Makefile` targets: `lib-c`, `lib-py`, `goldens`, `demo`, `trace-matrix`.

---

## 6. Data Flow

### 6.1 TX Path (satellite → ground, beacon)

```
Telemetry_PackBeacon(buf, 48)                   // existing
CCSDS_BuildSpacePacket(buf, 48, ccsds_out, 66)  // existing
AX25_EncodeUiFrame(dst=CQ-0, src=UN8SAT-1,
                   pid=0xF0, info=ccsds_out, 66)
  ├─ prepend flag 0x7E
  ├─ encode 14 B address field (callsign << 1, SSID byte)
  ├─ emit 0x03 (UI control), 0x0F (PID no L3)
  ├─ emit info (66 B CCSDS packet)
  ├─ compute FCS = CRC-16/AX.25 over address..info
  ├─ bit-stuff bytes between flags
  └─ append flag 0x7E
HAL_UART_Transmit(huart1, frame, n, 500 /*ms*/)
  ↓
[ SIMULATION_MODE: virtual_uart.c → TCP 127.0.0.1:52100 ]
  ↓
ax25_listen.py → decode → print JSON beacon
```

### 6.2 RX Path (ground → satellite, telecommand)

```
ax25_send.py --dst UN8SAT-1 --info <hex>
  → TCP 127.0.0.1:52100
HAL_UART_Receive_IT  (real or virtual shim)
  → COMM_UART_RxCallback(byte)                       // ISR, existing
  → ring_push(uhf_rx_buffer, byte)                   // lock-free SPSC
────────────────── task / ISR boundary ──────────────────
FreeRTOS comm_rx_task (period 10 ms, priority above-normal)
  loop:
    while ring_not_empty:
      byte = ring_pop()
      ax25_decoder_push_byte(&g_uhf_decoder, byte, &frame, &ready)
        ├─ internally: feed bit-level shift register
        ├─ on 0x7E in HUNT   → transition to FRAME
        ├─ on 0x7E in FRAME  → validate FCS, populate out_frame, ready=true
        ├─ on >5 ones run    → StuffingViolation (reset to HUNT)
        └─ on buf overflow   → FrameOverflow (reset to HUNT)
      if ready:
        CCSDS_Dispatcher_Submit(frame.info, frame.info_len)
```

The decoder owns the protocol state machine end-to-end. `comm.c` is a
pure byte pump between the ring buffer and the decoder. No flag
scanning, no bit manipulation, no CRC logic lives in `comm.c`.

### 6.3 Byte Map of an AX.25 UI Frame

```
[0x7E] [Dest 7 B] [Src 7 B] [0x03] [0xF0] [Info ≤256 B] [FCS 2 B LE] [0x7E]
   │       │         │        │       │         │            │         │
   │       │         │        │       │         │            │         end flag
   │       │         │        │       │         │            CRC-16/AX.25
   │       │         │        │       │         CCSDS Space Packet
   │       │         │        │       PID (0xF0 = no L3)
   │       │         │        UI control (0x03)
   │       │         callsign + SSID (encoded per AX.25 v2.2 §3.12)
   │       callsign + SSID (encoded per AX.25 v2.2 §3.12, H-bit last)
   HDLC flag; bit-stuffing is not applied to flags themselves
```

Exact bit-level address encoding (left-shift by 1, H-bit on last SSID
byte, C/R bits) is specified in AX.25 v2.2 §3.12 and implemented in
`ax25_encode_address()` / `ax25_decode_address()`.

---

## 7. Error Handling

### 7.1 Status Codes

```c
typedef enum {
  AX25_OK = 0,
  AX25_ERR_FLAG_MISSING,
  AX25_ERR_FCS_MISMATCH,
  AX25_ERR_INFO_TOO_LONG,        /* info > AX25_MAX_INFO_LEN          */
  AX25_ERR_FRAME_TOO_LONG,       /* stuffed frame > AX25_MAX_FRAME_BYTES
                                    (DoS guard; see §4.11)            */
  AX25_ERR_BUFFER_OVERFLOW,
  AX25_ERR_ADDRESS_INVALID,      /* non-alnum or >6-char callsign, OR
                                    >2 address fields (digipeater path,
                                    see REQ-AX25-018)                 */
  AX25_ERR_CONTROL_INVALID,      /* control != 0x03                   */
  AX25_ERR_PID_INVALID,          /* pid != 0xF0                       */
  AX25_ERR_STUFFING_VIOLATION    /* > 5 consecutive 1s in payload     */
} ax25_status_t;
```

### 7.2 Principles

- No function enters a panic path or calls a global `Error_Handler()`.
  Failures are reported via return code only.
- Zero heap allocation. Buffers are either static or caller-provided.
- Decoder hard-rejects any frame or candidate > `AX25_MAX_FRAME_BYTES`
  (400 B by default, configurable per §5.1a) at every stage.
- Malformed input never produces undefined behaviour (enforced by fuzz).
- Python raises a typed `AX25Error` subclass; `ax25_listen.py` catches,
  logs, and continues — the process never crashes.

### 7.3 Counters (in `COMM_Status_t`)

- `ax25_frames_ok`
- `ax25_fcs_errors`
- `ax25_frame_errors`
- `ax25_overflow_errors`

Exposed in telemetry housekeeping packets.

### 7.4 Recovery

- If `ax25_overflow_errors` exceeds a per-window threshold, `uhf_rx_buffer`
  is flushed and `error_handler.c` logs `ERR_COMM_RX_OVERFLOW`.
- AX.25 errors do not trigger safe mode. This is a link-layer concern, not
  a system-safety concern.

---

## 8. Testing

### 8.1 Golden Vectors (`tests/golden/ax25_vectors.json`)

≥28 vectors, 7 categories:

1. **Canonical** — spec beacon; min-size UI (0 B info); max-size UI (256 B).
2. **Bit-stuffing adversarial** — info containing `0x7E`, `0xFE`,
   five consecutive 1s across byte boundaries, all-0xFF payload.
3. **Address edge cases** — callsign shorter than 6 chars (space-padded),
   SSIDs 0 and 15, lower ASCII boundary, H-bit polarity.
4. **Digipeater rejection** — frames with 3+ address fields MUST decode to
   `AX25_ERR_ADDRESS_INVALID`.
5. **Malformed** — bad FCS, missing start flag, missing end flag,
   info > 256 B, control ≠ 0x03, PID ≠ 0xF0, stuffing violation (6 ones).
6. **DoS** — 1000-byte bit-stuffed frame (decoder rejects without hang),
   all-zero 10 KB stream (scanner does not spin).
7. **Flag-handling edge cases** (REQ-AX25-023) — idle runs of flags
   (`0x7E 0x7E 0x7E`) silently ignored; back-to-back frames sharing
   a flag (`… 0x7E 0x7E …`) yield two valid frames; trailing flag
   runs after a valid frame do not produce spurious errors.

**Dedicated FCS oracle** (REQ-AX25-022): the golden set includes a
fixed entry `{"input": "123456789", "fcs": "0x906E"}` that both C
and Python test runners assert before any other test runs.

Vector schema:

```json
{
  "description": "...",
  "reqs": ["REQ-AX25-006", "REQ-AX25-007"],
  "inputs": { ... },
  "encoded_hex": "...",
  "decode_result": { ... },
  "decode_status": "AX25_OK"
}
```

### 8.2 Unity Tests (`firmware/tests/test_ax25.c`)

- ≥50 tests; parameterised via a table of golden vectors.
- Separate unit tests for `encode`, pure `decode_ui_frame`, `fcs`,
  `bit_stuff`, address encoding, boundary cases.
- **Streaming-decoder tests** (first-class): for every encodable golden
  vector, feed bytes one at a time into a fresh `ax25_decoder_t`;
  assert that the emitted frame is byte-identical to the output of
  the pure `ax25_decode_ui_frame()` on the same input.
- **Partial-frame tests**: feed a prefix of a valid frame, assert
  `frame_ready == false` and no state corruption; then feed the
  remainder, assert success.
- **Split-stream tests**: feed two frames back-to-back, verify the
  decoder emits both correctly; feed garbage between frames, verify
  recovery.
- **Byte-boundary bit-stuffing**: dedicated tests for stuffing runs
  that cross byte boundaries (the common implementation bug — see
  REQ-AX25-016).
- Coverage gate: ≥95 % lines, ≥90 % branches (`gcovr`).

### 8.3 pytest (`ground-station/tests/test_ax25.py`)

- Golden-vector run — identical pass/fail with the C tests.
- `hypothesis` property-based: `decode(encode(x)) == x` for random valid
  frames within size bounds.
- Fuzz: 100 000 random byte sequences; the decoder must not crash, only
  return typed errors.

### 8.4 Cross-Implementation Round-Trip (`scripts/test_roundtrip.sh`)

- Compiles the C encoder as a host binary.
- Pipes its output through the Python decoder and vice versa.
- Checks each frame against the golden vector set.

### 8.5 CI (`.github/workflows/ax25.yml`)

- Matrix: Linux, macOS, Windows.
- Jobs: `lint-c` (clang-format Google), `lint-py` (pyink, pylint),
  `build`, `unit-c`, `unit-py`, `fuzz` (60-second timeout, 100 000 iters),
  `roundtrip`, `coverage` (≥95 % gate).

### 8.6 Verification Matrix

`docs/verification/ax25_trace_matrix.md` auto-generated from test
docstrings. Every `REQ-AX25-NNN` has at least one test and one golden
vector.

### 8.7 Demo Acceptance Test

`make demo` runs a 30-second scenario: firmware emits two beacons, the
ground station decodes them, prints the expected JSON. Exit code 0 = pass.

---

## 9. Requirements (derived from `communication_protocol.md` §7)

- **REQ-AX25-001** HDLC flag 0x7E delimits every frame; flags are never
  bit-stuffed.
- **REQ-AX25-002** Address field is exactly 14 bytes: 6-char callsign
  left-shifted by 1 bit + SSID byte encoded per AX.25 v2.2.
- **REQ-AX25-003** Control field is 0x03 (UI frame).
- **REQ-AX25-004** PID field is 0xF0 (no layer-3 protocol).
- **REQ-AX25-005** Info field length ≤ 256 bytes.
- **REQ-AX25-006** FCS is CRC-16/AX.25 (poly 0x1021, init 0xFFFF, output
  inverted, little-endian on the wire).
- **REQ-AX25-007** Bit-stuffing inserts a 0 bit after every 5 consecutive
  1 bits between flags.
- **REQ-AX25-008** End flag 0x7E closes every frame.
- **REQ-AX25-009** Beacon frame layout exactly matches §7.2 (48-byte info
  layout).
- **REQ-AX25-010** Receiver state machine matches §8.1.
- **REQ-AX25-011** Encoder emits frames ≤ 320 bytes after bit-stuffing.
- **REQ-AX25-012** Decoder rejects any candidate > `AX25_MAX_FRAME_BYTES`
  (default 400 bytes, configurable per §5.1a) at every
  stage.
- **REQ-AX25-013** No heap allocation in either encoder or decoder.
- **REQ-AX25-014** Decoder never produces undefined behaviour on
  arbitrary byte input.
- **REQ-AX25-015** Encoder and decoder are bit-identical across the
  C and Python implementations when run against the golden vectors.
- **REQ-AX25-016** Bit-stuffing MUST be implemented at bit level with
  continuous bit-stream state across byte boundaries. Byte-wise
  stuffing is explicitly incorrect and MUST be caught by tests.
- **REQ-AX25-017** The streaming decoder, when fed any valid encoded
  frame one byte at a time, MUST produce a `ax25_ui_frame_t` byte-
  identical to the output of `ax25_decode_ui_frame()` called on the
  same full buffer.
- **REQ-AX25-018** Frames containing more than two address fields
  (digipeater paths) MUST be rejected with
  `AX25_ERR_ADDRESS_INVALID`. Digipeater support is explicitly out
  of scope (see §11).
- **REQ-AX25-019** The AX.25 decoder MUST NOT execute in interrupt
  context. The ISR MUST perform only a single-byte ring-buffer push.
  Violation is a build-time or review-time failure, not a runtime
  check (the library has no HAL dependency by which it could enter
  an ISR).
- **REQ-AX25-020** The UART RX ring buffer MUST provide ≥ 400 ms of
  absorb capacity at the nominal link bit rate. At 9600 bps this
  requires ≥ 480 B; the chosen value is 512 B with 427 ms headroom.
- **REQ-AX25-021** The streaming decoder MUST be recoverable:
  malformed input increments a failure counter, resets the decoder
  to `AX25_STATE_HUNT`, and does not leak bytes of the malformed
  frame into subsequent frames.
- **REQ-AX25-022** The FCS implementation MUST match the canonical
  CRC-16/X-25 reference vector: `fcs_crc16("123456789") == 0x906E`.
  This exact value MUST be asserted in both the C Unity test suite
  and the Python pytest suite. It protects against the three most
  common silent bugs: bit-order reversal, missing input/output
  reflection, and `XorOut` endian confusion.
- **REQ-AX25-023** Consecutive flag bytes (`0x7E 0x7E`, and any run
  of flags) MUST be treated as frame delimiters with zero-length
  payload between them and MUST be silently ignored — no error,
  no counter increment, no frame emission. This is the standard
  AX.25 idle pattern between frames.
- **REQ-AX25-024** On any decode error encountered inside
  `AX25_STATE_FRAME`, the decoder MUST:
  1. Discard the current frame buffer and bit-level state.
  2. Treat the offending byte as already consumed.
  3. Return to `AX25_STATE_HUNT` to scan for the next opening flag.
  4. Not reprocess the offending byte.
  This prevents livelock and guarantees clean re-synchronisation
  on a noisy RF link.

---

## 10. Deliverables

1. `firmware/stm32/Drivers/AX25/` — pure C library (encode, batch decode,
   FCS, bit-stuff) + streaming decoder (`ax25_decoder.{c,h}`) + public
   `AX25_Xxx()` adapter facade.
2. `firmware/stm32/Drivers/VirtualUART/` — SIM-only TCP shim.
3. `ground-station/utils/ax25.py` — Python library.
4. `ground-station/cli/ax25_listen.py`, `ax25_send.py` — CLI tools.
5. `tests/golden/ax25_vectors.json` — shared test vectors.
6. `firmware/tests/test_ax25.c` — Unity tests.
7. `ground-station/tests/test_ax25.py` — pytest tests (+ hypothesis).
8. `scripts/test_roundtrip.sh`, `scripts/demo.py`,
   `scripts/gen_trace_matrix.py`.
9. `.github/workflows/ax25.yml` — CI pipeline.
10. `docs/adr/ADR-001-no-csp.md` — CSP architectural decision.
11. `docs/adr/ADR-002-style-adapter.md` — style-adapter rationale.
12. `docs/security/ax25_threat_model.md`.
13. `docs/verification/ax25_trace_matrix.md` (auto-generated).
14. `docs/tutorials/ax25_walkthrough.md` — educational walkthrough.
15. `docs/superpowers/specs/2026-04-17-track1-preflight.md` — upstream
    fixes to validate before coding.

---

## 11. Out-of-Scope (explicit)

- CCSDS-level HMAC — Track 1b.
- Real `libcsp` port — addressed by ADR-001, not by code.
- Driver reality audit — Track 2.
- End-to-end SITL test harness across all subsystems — Track 3.
- Developer-experience polish (`make all` across the whole repo) — Track 4.
- **Digipeater / repeater paths** — this implementation supports only
  point-to-point addressing (destination + source). Frames containing
  more than two address fields MUST be rejected with
  `AX25_ERR_ADDRESS_INVALID` (REQ-AX25-018). This is a mission
  constraint: UN8SAT-1 communicates directly with the ground station
  with no relay hops.
- **Timing-accurate simulation** — the SITL TCP shim validates
  functional correctness only; byte-interval jitter, burst patterns,
  and ISR pressure are not reproduced. Timing validation belongs to
  Track 3 (Renode / QEMU / HIL).
- **Hardware flow control (RTS/CTS)** — not used on amateur-radio
  UHF links; not implemented. Throughput budget §4.11 proves flow
  control is unnecessary at 9600 bps.

---

## 12. Open Questions

None at design time. Pre-flight spec (§4.5) may raise concrete issues to
close before the implementation plan is written.
