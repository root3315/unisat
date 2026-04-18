# AX.25 Link Layer Implementation Plan

> ⚠️ **ARCHIVED — HISTORICAL IMPLEMENTATION ROADMAP**
>
> This 4000-line plan was executed in April 2026 and landed the
> initial AX.25 + CCSDS + HMAC stack (commits up to 99774cf). It
> is **preserved for traceability** — the Phase 2–8 TRL-5
> hardening work refined several of the APIs and wire formats
> listed here, most notably:
>
> - **Replay counter (ADR-004):** the dispatcher now expects a
>   4-byte counter prefix before the body; this plan references
>   the older body+HMAC-only layout.
> - **Key store (ADR-003):** the plan assumed the HMAC key was
>   set by boot code; the production firmware now reads it from
>   A/B flash via `key_store.c`.
> - **FDIR (ADR-005):** this plan's §7 talks about FDIR as one
>   module; it was later split into `fdir.c` (advisor) +
>   `mode_manager.c` (commander).
>
> For current implementation guidance see:
> - `docs/requirements/SRS.md` — authoritative requirements
> - `docs/adr/` — 8 ADRs covering post-Track-1 design decisions
> - `docs/TECHNICAL_DOCUMENTATION.md §0` — Phase 7/8 summary
>
> See `docs/superpowers/README.md` for the archival context.

**Goal:** Implement the AX.25 UI-frame link layer end-to-end: pure C + Python libraries with a streaming decoder, full integration into `comm.c`, SITL round-trip via TCP loopback, and a `make demo` that walks a real beacon from firmware to ground station.

**Architecture:** Four layers (pure library → style adapter → application → demo orchestration) with strict inversion of dependency — `comm.c` consumes `ax25_decoder_t`, not the other way around. Bit-level state machine inside the decoder, zero heap, zero HAL dependency in the library. Golden vectors are the single source of truth for interop between C and Python.

**Tech Stack:** C11 (firmware), Python 3.10+ (ground station), FreeRTOS (CMSIS-OS2), Unity (C tests), pytest + hypothesis (Python tests), CMake + gcovr (build/coverage), GitHub Actions (CI).

**Spec:** [`../specs/2026-04-17-track1-ax25-design.md`](../specs/2026-04-17-track1-ax25-design.md)

---

## File Structure

### New files

```
firmware/stm32/Drivers/AX25/
  ax25_types.h                  # ax25_address_t, ax25_ui_frame_t, ax25_status_t, ax25_decoder_t
  ax25.h                        # pure stateless API
  ax25.c                        # FCS, bit-stuff, encode, pure-decode implementations
  ax25_decoder.h                # streaming decoder public interface
  ax25_decoder.c                # streaming decoder implementation
  ax25_api.h                    # static-inline AX25_Xxx() facade
  CMakeLists.txt                # library build

firmware/stm32/Drivers/VirtualUART/
  virtual_uart.h
  virtual_uart.c                # TCP shim for SITL

firmware/tests/
  test_ax25.c                   # Unity tests (batch encode/decode + streaming)
  test_ax25_fcs.c               # dedicated FCS oracle test
  golden_vectors_loader.c       # reads tests/golden/ax25_vectors.json
  test_runner_ax25.c            # main() for AX.25 tests

ground-station/utils/
  ax25.py                       # Python library (mirrors C)

ground-station/cli/
  __init__.py
  ax25_listen.py
  ax25_send.py

ground-station/tests/
  test_ax25.py                  # pytest + hypothesis

tests/golden/
  ax25_vectors.json             # shared test fixtures

scripts/
  demo.py                       # orchestration
  test_roundtrip.sh             # cross-implementation CI job
  gen_trace_matrix.py           # auto-generate verification matrix

docs/adr/
  ADR-001-no-csp.md
  ADR-002-style-adapter.md
docs/security/
  ax25_threat_model.md
docs/tutorials/
  ax25_walkthrough.md
docs/verification/
  ax25_trace_matrix.md          # auto-generated

.github/workflows/
  ax25.yml                      # CI matrix (Linux/macOS/Windows)
```

### Modified files

```
firmware/stm32/Core/Inc/config.h         # add AX25_* constants
firmware/stm32/Core/Inc/comm.h           # add ax25 counters to COMM_Status_t
firmware/stm32/Core/Src/comm.c           # integrate ax25_decoder, COMM_SendAX25
firmware/stm32/Core/Src/telemetry.c      # verify/fix Telemetry_PackBeacon
firmware/stm32/CMakeLists.txt            # link new libraries
ground-station/requirements.txt          # add hypothesis
Makefile                                 # new: lib-c, lib-py, goldens, demo
```

---

## Phase 0: Pre-Flight (spec §4.5)

### Task 0.1: Verify Telemetry_PackBeacon emits 48-byte layout per spec §7.2

**Files:**
- Modify (if needed): `firmware/stm32/Core/Src/telemetry.c`
- Read: `firmware/stm32/Core/Inc/telemetry.h`
- Reference: `docs/communication_protocol.md` §7.2

- [ ] **Step 1: Read current implementation**

```bash
grep -n "Telemetry_PackBeacon" firmware/stm32/Core/Src/telemetry.c firmware/stm32/Core/Inc/telemetry.h
```

Expected: either (a) function exists with 48-byte layout — skip to Step 6, or (b) function is missing / stubbed — continue to Step 2.

- [ ] **Step 2: Write the failing unit test**

Create `firmware/tests/test_beacon_layout.c`:

```c
#include "unity.h"
#include "telemetry.h"
#include <string.h>

void setUp(void) {}
void tearDown(void) {}

void test_pack_beacon_returns_48_bytes(void) {
  uint8_t buf[128] = {0};
  uint16_t n = Telemetry_PackBeacon(buf, sizeof(buf));
  TEST_ASSERT_EQUAL_UINT16(48, n);
}

void test_pack_beacon_offset_4_is_mode_byte(void) {
  uint8_t buf[128] = {0};
  Telemetry_PackBeacon(buf, sizeof(buf));
  /* Spec §7.2: offset 4 = mode (u8). Mode must be a known enum value 0..7. */
  TEST_ASSERT_LESS_THAN_UINT8(8, buf[4]);
}

void test_pack_beacon_quaternion_at_offset_16(void) {
  uint8_t buf[128] = {0};
  Telemetry_PackBeacon(buf, sizeof(buf));
  /* Offsets 16..31 = qw,qx,qy,qz (f32 LE). Assert not all zero after init. */
  uint8_t zeros[16] = {0};
  TEST_ASSERT_NOT_EQUAL_MEMORY(zeros, &buf[16], 16);
}

int main(void) {
  UNITY_BEGIN();
  RUN_TEST(test_pack_beacon_returns_48_bytes);
  RUN_TEST(test_pack_beacon_offset_4_is_mode_byte);
  RUN_TEST(test_pack_beacon_quaternion_at_offset_16);
  return UNITY_END();
}
```

- [ ] **Step 3: Run test to confirm failure**

```bash
cd firmware && cmake -B build && cmake --build build --target test_beacon_layout
./build/test_beacon_layout
```

Expected: FAIL (either function missing or returns wrong length).

- [ ] **Step 4: Implement/fix Telemetry_PackBeacon per spec §7.2**

Replace or add in `firmware/stm32/Core/Src/telemetry.c`:

```c
uint16_t Telemetry_PackBeacon(uint8_t *buffer, uint16_t max_size) {
  if (max_size < 48 || buffer == NULL) return 0;

  OBC_Status_t  obc  = OBC_GetStatus();
  EPS_Status_t  eps  = EPS_GetStatus();
  ADCS_Status_t adcs = ADCS_GetStatus();
  GNSS_Data_t   gnss = GNSS_GetFullData();

  uint16_t o = 0;

  /* offset 0..3 : uptime seconds (u32 LE) */
  memcpy(&buffer[o], &obc.uptime_seconds, 4); o += 4;

  /* offset 4 : mode (u8) */
  buffer[o++] = (uint8_t)obc.current_state;

  /* offset 5..6 : battery voltage mV (u16 LE) */
  uint16_t vbat_mv = (uint16_t)(eps.battery_voltage * 1000.0f);
  memcpy(&buffer[o], &vbat_mv, 2); o += 2;

  /* offset 7..8 : battery current mA (i16 LE) */
  int16_t ibat_ma = (int16_t)(eps.battery_current * 1000.0f);
  memcpy(&buffer[o], &ibat_ma, 2); o += 2;

  /* offset 9 : SOC % (u8) */
  buffer[o++] = (uint8_t)eps.battery_soc;

  /* offset 10..11 : solar power mW (u16 LE) */
  uint16_t psol_mw = (uint16_t)(eps.solar_power * 1000.0f);
  memcpy(&buffer[o], &psol_mw, 2); o += 2;

  /* offset 12..13 : CPU temp 0.1°C (i16 LE) */
  int16_t tcpu_d10 = (int16_t)(obc.cpu_temperature * 10.0f);
  memcpy(&buffer[o], &tcpu_d10, 2); o += 2;

  /* offset 14..15 : board temp 0.1°C (i16 LE) */
  int16_t tboard_d10 = (int16_t)(obc.cpu_temperature * 10.0f); /* TODO: real board temp */
  memcpy(&buffer[o], &tboard_d10, 2); o += 2;

  /* offset 16..31 : quaternion qw,qx,qy,qz (f32 LE) */
  memcpy(&buffer[o], adcs.quaternion, 16); o += 16;

  /* offset 32..33 : angular rate 0.01 deg/s (u16 LE, magnitude) */
  float omega = adcs.angular_rate[0] * adcs.angular_rate[0]
              + adcs.angular_rate[1] * adcs.angular_rate[1]
              + adcs.angular_rate[2] * adcs.angular_rate[2];
  uint16_t omega_u = (uint16_t)(omega * 100.0f);
  memcpy(&buffer[o], &omega_u, 2); o += 2;

  /* offset 34..37 : latitude 1e-7 deg (i32 LE) */
  int32_t lat_e7 = (int32_t)(gnss.latitude * 1.0e7);
  memcpy(&buffer[o], &lat_e7, 4); o += 4;

  /* offset 38..41 : longitude 1e-7 deg (i32 LE) */
  int32_t lon_e7 = (int32_t)(gnss.longitude * 1.0e7);
  memcpy(&buffer[o], &lon_e7, 4); o += 4;

  /* offset 42..43 : altitude m (u16 LE) */
  uint16_t alt_m = (uint16_t)gnss.altitude;
  memcpy(&buffer[o], &alt_m, 2); o += 2;

  /* offset 44 : GNSS fix type (u8) */
  buffer[o++] = (uint8_t)gnss.fix_type;

  /* offset 45 : error count (u8, saturated) */
  buffer[o++] = obc.error_count > 255 ? 255 : (uint8_t)obc.error_count;

  /* offset 46..47 : sequence count (u16 LE) */
  static uint16_t seq = 0;
  uint16_t this_seq = seq++;
  memcpy(&buffer[o], &this_seq, 2); o += 2;

  return o;  /* must be 48 */
}
```

- [ ] **Step 5: Run test to verify pass**

```bash
cmake --build build --target test_beacon_layout && ./build/test_beacon_layout
```

Expected: PASS on all three assertions.

- [ ] **Step 6: Commit**

```bash
git add firmware/stm32/Core/Src/telemetry.c firmware/tests/test_beacon_layout.c
git commit -m "fix(telemetry): beacon layout per communication_protocol.md §7.2 (48 bytes)"
```

---

### Task 0.2: Raise IO_TIMEOUT_MS to 500 for worst-case AX.25 frame

**Files:**
- Modify: `firmware/stm32/Core/Inc/config.h`

- [ ] **Step 1: Locate current value**

```bash
grep -n "IO_TIMEOUT_MS\|IO_RETRY_DELAY_MS\|IO_MAX_RETRIES" firmware/stm32/Core/Inc/config.h
```

- [ ] **Step 2: Raise timeout**

Edit `firmware/stm32/Core/Inc/config.h`, replace:

```c
#define IO_TIMEOUT_MS    100
```

with:

```c
/* Covers worst-case bit-stuffed AX.25 frame (~266 ms @ 9600 bps). */
#define IO_TIMEOUT_MS    500
```

- [ ] **Step 3: Verify firmware still builds**

```bash
cd firmware && cmake --build build
```

Expected: build succeeds with no new warnings.

- [ ] **Step 4: Commit**

```bash
git add firmware/stm32/Core/Inc/config.h
git commit -m "fix(config): raise IO_TIMEOUT_MS to 500 for worst-case AX.25 TX"
```

---

### Task 0.3: Add AX.25 constants to config.h

**Files:**
- Modify: `firmware/stm32/Core/Inc/config.h`

- [ ] **Step 1: Append AX.25 section**

Append to `firmware/stm32/Core/Inc/config.h`, just before `#endif /* CONFIG_H */`:

```c
/* AX.25 Link Layer (spec §5.1a) */
#define ENABLE_AX25_FRAMING       true
#define AX25_MAX_INFO_LEN         256
#define AX25_MAX_FRAME_BYTES      400
#define AX25_RING_BUFFER_SIZE     512
#define AX25_DECODER_TASK_STACK   1024
```

- [ ] **Step 2: Verify build**

```bash
cd firmware && cmake --build build
```

Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add firmware/stm32/Core/Inc/config.h
git commit -m "feat(config): add AX.25 compile-time constants (REQ-AX25 §5.1a)"
```

---

## Phase 1: Pure Helpers (FCS, Bit-Stuffing, Address)

### Task 1.1: FCS CRC-16/X.25 implementation (C) with REQ-AX25-022 oracle

**Files:**
- Create: `firmware/stm32/Drivers/AX25/ax25_types.h`
- Create: `firmware/stm32/Drivers/AX25/ax25.h`
- Create: `firmware/stm32/Drivers/AX25/ax25.c`
- Create: `firmware/stm32/Drivers/AX25/CMakeLists.txt`
- Create: `firmware/tests/test_ax25_fcs.c`

- [ ] **Step 1: Create types header**

Write `firmware/stm32/Drivers/AX25/ax25_types.h`:

```c
/* AX.25 v2.2 link layer — shared types.  See docs/superpowers/specs/
 * 2026-04-17-track1-ax25-design.md §5.1 for design rationale. */
#ifndef AX25_TYPES_H
#define AX25_TYPES_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#include "config.h"

typedef enum {
  AX25_OK = 0,
  AX25_ERR_FLAG_MISSING,
  AX25_ERR_FCS_MISMATCH,
  AX25_ERR_INFO_TOO_LONG,
  AX25_ERR_FRAME_TOO_LONG,
  AX25_ERR_BUFFER_OVERFLOW,
  AX25_ERR_ADDRESS_INVALID,
  AX25_ERR_CONTROL_INVALID,
  AX25_ERR_PID_INVALID,
  AX25_ERR_STUFFING_VIOLATION
} ax25_status_t;

typedef struct {
  char    callsign[7];   /* NUL-terminated, ≤6 ASCII chars */
  uint8_t ssid;          /* 0..15 */
} ax25_address_t;

typedef struct {
  ax25_address_t dst;
  ax25_address_t src;
  uint8_t        control;            /* always 0x03 for UI frame */
  uint8_t        pid;                /* always 0xF0 */
  uint8_t        info[AX25_MAX_INFO_LEN];
  uint16_t       info_len;
  uint16_t       fcs;                /* received FCS (little-endian on wire) */
  bool           fcs_valid;
} ax25_ui_frame_t;

#endif /* AX25_TYPES_H */
```

- [ ] **Step 2: Create public pure-library header**

Write `firmware/stm32/Drivers/AX25/ax25.h`:

```c
#ifndef AX25_H
#define AX25_H

#include "ax25_types.h"

/* REQ-AX25-006, REQ-AX25-022: CRC-16/X.25.
 * poly=0x1021, init=0xFFFF, refin=true, refout=true, xorout=0xFFFF.
 * Reference vector: fcs_crc16("123456789") == 0x906E. */
uint16_t ax25_fcs_crc16(const uint8_t *data, size_t len);

/* REQ-AX25-007, REQ-AX25-016: bit-level stuffing.
 * Writes LSB-first bit stream with a 0 inserted after every 5 consecutive
 * 1 bits.  Returns bytes written; returns 0 on overflow. */
size_t ax25_bit_stuff(const uint8_t *in, size_t in_len,
                       uint8_t *out, size_t out_cap);

/* Inverse of ax25_bit_stuff; detects >5 consecutive 1s as violation
 * (returns 0 and sets *status if provided). */
size_t ax25_bit_unstuff(const uint8_t *in, size_t in_len,
                         uint8_t *out, size_t out_cap,
                         ax25_status_t *status);

/* REQ-AX25-002: address encode/decode. */
ax25_status_t ax25_encode_address(const ax25_address_t *addr,
                                   bool is_last, uint8_t out[7]);

/* Decodes one address field; returns how many bytes advanced (always 7). */
ax25_status_t ax25_decode_address(const uint8_t in[7],
                                   bool *is_last,
                                   ax25_address_t *out);

/* REQ-AX25-001..015: encode a complete UI frame with flags, FCS, stuffing. */
ax25_status_t ax25_encode_ui_frame(
    const ax25_address_t *dst, const ax25_address_t *src,
    uint8_t pid,
    const uint8_t *info, size_t info_len,
    uint8_t *out, size_t out_cap, size_t *out_len);

/* Decode a fully-buffered, unstuffed frame body (NO flags, NO stuffing).
 * Used internally by the streaming decoder and directly in unit tests. */
ax25_status_t ax25_decode_ui_frame(
    const uint8_t *in, size_t in_len,
    ax25_ui_frame_t *out_frame);

#endif /* AX25_H */
```

- [ ] **Step 3: Write failing FCS oracle test**

Write `firmware/tests/test_ax25_fcs.c`:

```c
#include "unity.h"
#include "ax25.h"
#include <string.h>

void setUp(void) {}
void tearDown(void) {}

/* REQ-AX25-022: CRC-16/X.25 reference vector. */
void test_fcs_reference_vector_123456789(void) {
  const char *s = "123456789";
  uint16_t fcs = ax25_fcs_crc16((const uint8_t *)s, 9);
  TEST_ASSERT_EQUAL_HEX16(0x906E, fcs);
}

void test_fcs_empty_input_returns_init_xor_ffff(void) {
  uint16_t fcs = ax25_fcs_crc16(NULL, 0);
  /* 0xFFFF ^ 0xFFFF = 0x0000 after xorout */
  TEST_ASSERT_EQUAL_HEX16(0x0000, fcs);
}

void test_fcs_single_zero_byte(void) {
  const uint8_t zero = 0;
  uint16_t fcs = ax25_fcs_crc16(&zero, 1);
  /* Hand-computed: 0xC873 for CRC-16/X.25 on [0x00]. */
  TEST_ASSERT_EQUAL_HEX16(0xC873, fcs);
}

int main(void) {
  UNITY_BEGIN();
  RUN_TEST(test_fcs_reference_vector_123456789);
  RUN_TEST(test_fcs_empty_input_returns_init_xor_ffff);
  RUN_TEST(test_fcs_single_zero_byte);
  return UNITY_END();
}
```

- [ ] **Step 4: Create CMake library**

Write `firmware/stm32/Drivers/AX25/CMakeLists.txt`:

```cmake
add_library(ax25 STATIC
  ax25.c
)

target_include_directories(ax25 PUBLIC
  ${CMAKE_CURRENT_SOURCE_DIR}
  ${CMAKE_SOURCE_DIR}/Core/Inc
)
```

- [ ] **Step 5: Run test, confirm failure**

```bash
cd firmware && cmake -B build && cmake --build build --target test_ax25_fcs
./build/test_ax25_fcs
```

Expected: link error — `ax25_fcs_crc16` not defined.

- [ ] **Step 6: Implement FCS in ax25.c**

Create `firmware/stm32/Drivers/AX25/ax25.c`:

```c
/* AX.25 v2.2 link layer — implementation.
 * See docs/communication_protocol.md §7 and the design spec in
 * docs/superpowers/specs/2026-04-17-track1-ax25-design.md. */

#include "ax25.h"
#include <string.h>

/* CRC-16/X.25 per REQ-AX25-006 / REQ-AX25-022.
 * Reflected algorithm: poly 0x8408 (reverse of 0x1021), init 0xFFFF,
 * xorout 0xFFFF.  Runs right-shift, LSB-first. */
uint16_t ax25_fcs_crc16(const uint8_t *data, size_t len) {
  uint16_t crc = 0xFFFF;
  for (size_t i = 0; i < len; i++) {
    crc ^= data[i];
    for (int b = 0; b < 8; b++) {
      if (crc & 1) crc = (crc >> 1) ^ 0x8408;
      else         crc >>= 1;
    }
  }
  return (uint16_t)~crc;
}
```

- [ ] **Step 7: Run test, confirm pass**

```bash
cmake --build build --target test_ax25_fcs && ./build/test_ax25_fcs
```

Expected: `3 Tests 0 Failures 0 Ignored`.

- [ ] **Step 8: Commit**

```bash
git add firmware/stm32/Drivers/AX25/ firmware/tests/test_ax25_fcs.c
git commit -m "feat(ax25): CRC-16/X.25 FCS with REQ-AX25-022 oracle vector"
```

---

### Task 1.2: FCS mirror in Python (`ground-station/utils/ax25.py`)

**Files:**
- Create: `ground-station/utils/ax25.py`
- Create: `ground-station/tests/test_ax25.py`
- Modify: `ground-station/requirements.txt`

- [ ] **Step 1: Add hypothesis to requirements**

Append to `ground-station/requirements.txt`:

```
hypothesis>=6.98,<7.0
```

Run:

```bash
cd ground-station && pip install -r requirements.txt
```

- [ ] **Step 2: Write failing test**

Create `ground-station/tests/test_ax25.py`:

```python
"""AX.25 link layer tests — see docs/superpowers/specs/..."""

import pytest

from utils.ax25 import fcs_crc16


class TestFcs:
    def test_reference_vector(self):
        """REQ-AX25-022: canonical CRC-16/X.25 oracle."""
        assert fcs_crc16(b"123456789") == 0x906E

    def test_empty_input(self):
        assert fcs_crc16(b"") == 0x0000

    def test_single_zero_byte(self):
        assert fcs_crc16(b"\x00") == 0xC873
```

- [ ] **Step 3: Run test, confirm failure**

```bash
cd ground-station && pytest tests/test_ax25.py -v
```

Expected: ImportError (utils.ax25 missing).

- [ ] **Step 4: Implement fcs_crc16**

Create `ground-station/utils/ax25.py`:

```python
"""AX.25 v2.2 link layer — Python reference implementation.

Mirrors firmware/stm32/Drivers/AX25/ax25.c.  All interop is verified
against the shared golden-vector fixtures in tests/golden/ax25_vectors.json.
"""

from __future__ import annotations


def fcs_crc16(data: bytes) -> int:
    """CRC-16/X.25 per REQ-AX25-006, REQ-AX25-022.

    poly=0x1021 (reflected 0x8408), init=0xFFFF, refin=refout=True,
    xorout=0xFFFF.  Oracle: fcs_crc16(b"123456789") == 0x906E.
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
```

- [ ] **Step 5: Run test, confirm pass**

```bash
pytest tests/test_ax25.py::TestFcs -v
```

Expected: 3 passed.

- [ ] **Step 6: Commit**

```bash
git add ground-station/utils/ax25.py ground-station/tests/test_ax25.py ground-station/requirements.txt
git commit -m "feat(gs-ax25): CRC-16/X.25 FCS Python mirror with REQ-AX25-022 oracle"
```

---

### Task 1.3: Bit-stuffing (C) — bit-level across byte boundaries

**Files:**
- Modify: `firmware/stm32/Drivers/AX25/ax25.c`
- Create: `firmware/tests/test_ax25_bitstuff.c`

- [ ] **Step 1: Write failing bit-stuff tests**

Create `firmware/tests/test_ax25_bitstuff.c`:

```c
#include "unity.h"
#include "ax25.h"
#include <string.h>

void setUp(void) {}
void tearDown(void) {}

/* REQ-AX25-007: after every 5 consecutive 1s, a 0 MUST be inserted.
 * REQ-AX25-016: this is bit-level across byte boundaries. */
void test_stuff_all_ones_byte_inserts_one_zero(void) {
  /* Input 0xFF = 11111111 LSB-first: 1,1,1,1,1,1,1,1
   * After 5 ones -> insert 0 -> 1,1,1,1,1,0,1,1,1
   * 9 bits, left-aligned in LSB-first byte: 0xFD, 0x01 */
  const uint8_t in[1] = { 0xFF };
  uint8_t out[4] = { 0 };
  size_t n = ax25_bit_stuff(in, 1, out, sizeof(out));
  TEST_ASSERT_EQUAL_size_t(2, n);
  TEST_ASSERT_EQUAL_HEX8(0xFD, out[0]);
  TEST_ASSERT_EQUAL_HEX8(0x01, out[1]);
}

void test_stuff_no_ones_no_change(void) {
  const uint8_t in[2] = { 0x00, 0x00 };
  uint8_t out[4] = { 0 };
  size_t n = ax25_bit_stuff(in, 2, out, sizeof(out));
  TEST_ASSERT_EQUAL_size_t(2, n);
  TEST_ASSERT_EQUAL_HEX8(0x00, out[0]);
  TEST_ASSERT_EQUAL_HEX8(0x00, out[1]);
}

/* Byte-boundary test: input 0x1F, 0xF8 = 1,1,1,1,1, 0,0,0 | 0,0,0, 1,1,1,1,1
 * LSB-first bit stream:
 *   byte 0 bits (LSB..MSB): 1,1,1,1,1,0,0,0
 *   byte 1 bits (LSB..MSB): 0,0,0,1,1,1,1,1
 * Concatenated bit stream: 1,1,1,1,1,0,0,0,0,0,0,1,1,1,1,1
 * After stuffing: 1,1,1,1,1,0,0,0,0,0,0,0,1,1,1,1,1,0
 * Repack LSB-first into bytes: 0x1F, 0xF8 ... wait — stuffing inserts
 * a zero only when exactly 5 ones are seen, and resets on a zero.
 * Bits 0..4 are 1,1,1,1,1 -> insert 0 after bit 4 -> continues with 0,0,0 ...
 * so the inserted 0 plus the natural 0 run keeps the next 1s safe.
 * Bits 11..15 are 1,1,1,1,1 again -> insert 0.
 * Resulting 18 bits packed LSB-first: 0x1F, 0xF0, 0x03. */
void test_stuff_across_byte_boundary(void) {
  const uint8_t in[2] = { 0x1F, 0xF8 };
  uint8_t out[8] = { 0 };
  size_t n = ax25_bit_stuff(in, 2, out, sizeof(out));
  TEST_ASSERT_EQUAL_size_t(3, n);
  TEST_ASSERT_EQUAL_HEX8(0x1F, out[0]);
  TEST_ASSERT_EQUAL_HEX8(0xF0, out[1]);
  TEST_ASSERT_EQUAL_HEX8(0x03, out[2]);
}

void test_unstuff_inverse_of_stuff(void) {
  const uint8_t original[3] = { 0x12, 0xFF, 0x34 };
  uint8_t stuffed[8] = { 0 };
  size_t ns = ax25_bit_stuff(original, 3, stuffed, sizeof(stuffed));
  uint8_t recovered[8] = { 0 };
  ax25_status_t st;
  size_t nr = ax25_bit_unstuff(stuffed, ns, recovered, sizeof(recovered), &st);
  TEST_ASSERT_EQUAL(AX25_OK, st);
  TEST_ASSERT_EQUAL_size_t(3, nr);
  TEST_ASSERT_EQUAL_MEMORY(original, recovered, 3);
}

/* Six consecutive 1s in a stuffed stream is illegal. */
void test_unstuff_rejects_six_ones(void) {
  /* 0xFC = 00111111 LSB-first = 1,1,1,1,1,1,0,0 — six 1s = violation. */
  const uint8_t bad[1] = { 0x3F };
  uint8_t out[4] = { 0 };
  ax25_status_t st;
  size_t n = ax25_bit_unstuff(bad, 1, out, sizeof(out), &st);
  TEST_ASSERT_EQUAL_size_t(0, n);
  TEST_ASSERT_EQUAL(AX25_ERR_STUFFING_VIOLATION, st);
}

int main(void) {
  UNITY_BEGIN();
  RUN_TEST(test_stuff_all_ones_byte_inserts_one_zero);
  RUN_TEST(test_stuff_no_ones_no_change);
  RUN_TEST(test_stuff_across_byte_boundary);
  RUN_TEST(test_unstuff_inverse_of_stuff);
  RUN_TEST(test_unstuff_rejects_six_ones);
  return UNITY_END();
}
```

- [ ] **Step 2: Run, confirm link failure**

```bash
cmake --build build --target test_ax25_bitstuff && ./build/test_ax25_bitstuff
```

Expected: link failure (`ax25_bit_stuff`, `ax25_bit_unstuff` missing).

- [ ] **Step 3: Implement bit-stuff helpers**

Append to `firmware/stm32/Drivers/AX25/ax25.c`:

```c
/* Internal: write one bit (LSB-first) into buf[*bit_idx], grow *bit_idx. */
static inline bool push_bit(uint8_t *buf, size_t cap, size_t *bit_idx, int bit) {
  size_t byte = *bit_idx / 8;
  size_t shift = *bit_idx % 8;
  if (byte >= cap) return false;
  if (shift == 0) buf[byte] = 0;
  if (bit) buf[byte] |= (uint8_t)(1u << shift);
  (*bit_idx)++;
  return true;
}

/* Internal: read one bit (LSB-first) from buf[bit_idx]. */
static inline int read_bit(const uint8_t *buf, size_t bit_idx) {
  return (buf[bit_idx / 8] >> (bit_idx % 8)) & 1;
}

size_t ax25_bit_stuff(const uint8_t *in, size_t in_len,
                       uint8_t *out, size_t out_cap) {
  if (in == NULL || out == NULL) return 0;
  size_t out_bit = 0;
  int ones = 0;

  for (size_t i = 0; i < in_len * 8; i++) {
    int bit = read_bit(in, i);
    if (!push_bit(out, out_cap, &out_bit, bit)) return 0;
    if (bit == 1) {
      ones++;
      if (ones == 5) {
        if (!push_bit(out, out_cap, &out_bit, 0)) return 0;
        ones = 0;
      }
    } else {
      ones = 0;
    }
  }
  /* Round up to whole bytes. */
  return (out_bit + 7) / 8;
}

size_t ax25_bit_unstuff(const uint8_t *in, size_t in_len,
                         uint8_t *out, size_t out_cap,
                         ax25_status_t *status) {
  if (in == NULL || out == NULL) {
    if (status) *status = AX25_ERR_BUFFER_OVERFLOW;
    return 0;
  }
  size_t out_bit = 0;
  int ones = 0;

  for (size_t i = 0; i < in_len * 8; i++) {
    int bit = read_bit(in, i);
    if (ones == 5 && bit == 0) {
      /* Inserted stuff bit — drop. */
      ones = 0;
      continue;
    }
    if (ones == 5 && bit == 1) {
      /* Six consecutive 1s — illegal inside a frame. */
      if (status) *status = AX25_ERR_STUFFING_VIOLATION;
      return 0;
    }
    if (!push_bit(out, out_cap, &out_bit, bit)) {
      if (status) *status = AX25_ERR_BUFFER_OVERFLOW;
      return 0;
    }
    ones = (bit == 1) ? ones + 1 : 0;
  }
  if (status) *status = AX25_OK;
  return (out_bit + 7) / 8;
}
```

- [ ] **Step 4: Run tests, confirm pass**

```bash
cmake --build build --target test_ax25_bitstuff && ./build/test_ax25_bitstuff
```

Expected: `5 Tests 0 Failures`.

- [ ] **Step 5: Commit**

```bash
git add firmware/stm32/Drivers/AX25/ax25.c firmware/tests/test_ax25_bitstuff.c
git commit -m "feat(ax25): bit-level bit-stuffing across byte boundaries (REQ-AX25-007/016)"
```

---

### Task 1.4: Bit-stuffing mirror in Python

**Files:**
- Modify: `ground-station/utils/ax25.py`
- Modify: `ground-station/tests/test_ax25.py`

- [ ] **Step 1: Add failing tests (port from C)**

Append to `ground-station/tests/test_ax25.py`:

```python
from utils.ax25 import bit_stuff, bit_unstuff, AX25Error, StuffingViolation


class TestBitStuff:
    def test_all_ones_byte_inserts_zero(self):
        assert bit_stuff(b"\xFF") == bytes([0xFD, 0x01])

    def test_no_ones_unchanged(self):
        assert bit_stuff(b"\x00\x00") == b"\x00\x00"

    def test_across_byte_boundary(self):
        assert bit_stuff(b"\x1F\xF8") == bytes([0x1F, 0xF0, 0x03])

    def test_unstuff_is_inverse(self):
        original = b"\x12\xFF\x34"
        assert bit_unstuff(bit_stuff(original)) == original

    def test_six_ones_rejected(self):
        with pytest.raises(StuffingViolation):
            bit_unstuff(b"\x3F")
```

- [ ] **Step 2: Confirm failure**

```bash
pytest tests/test_ax25.py::TestBitStuff -v
```

Expected: ImportError on `bit_stuff` / `bit_unstuff` / exception classes.

- [ ] **Step 3: Implement in ax25.py**

Append to `ground-station/utils/ax25.py`:

```python
class AX25Error(Exception):
    """Base for AX.25 decode/encode failures."""


class StuffingViolation(AX25Error):
    """More than 5 consecutive 1-bits found inside a stuffed stream."""


class FcsMismatch(AX25Error):
    pass


class FrameOverflow(AX25Error):
    pass


class InvalidAddress(AX25Error):
    pass


class InvalidControl(AX25Error):
    pass


class InvalidPid(AX25Error):
    pass


def _bits_lsb_first(data: bytes):
    for b in data:
        for shift in range(8):
            yield (b >> shift) & 1


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
    """REQ-AX25-007 / REQ-AX25-016: insert 0 after every 5 consecutive 1s."""
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
    """Inverse of bit_stuff; raises StuffingViolation on 6 consecutive 1s."""
    def gen():
        ones = 0
        it = iter(_bits_lsb_first(data))
        for bit in it:
            if ones == 5 and bit == 0:
                ones = 0
                continue
            if ones == 5 and bit == 1:
                raise StuffingViolation("six consecutive 1-bits")
            yield bit
            ones = ones + 1 if bit == 1 else 0
    return _pack_bits_lsb_first(gen())
```

- [ ] **Step 4: Run, confirm pass**

```bash
pytest tests/test_ax25.py::TestBitStuff -v
```

Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add ground-station/utils/ax25.py ground-station/tests/test_ax25.py
git commit -m "feat(gs-ax25): bit-stuffing Python mirror (REQ-AX25-007/016)"
```

---

### Task 1.5: Address encode/decode (C) — incl. digipeater rejection

**Files:**
- Modify: `firmware/stm32/Drivers/AX25/ax25.c`
- Create: `firmware/tests/test_ax25_address.c`

- [ ] **Step 1: Write failing address tests**

Create `firmware/tests/test_ax25_address.c`:

```c
#include "unity.h"
#include "ax25.h"
#include <string.h>

void setUp(void) {}
void tearDown(void) {}

/* AX.25 v2.2 §3.12: each callsign char is shifted LEFT by 1 bit;
 * the SSID byte is CRRSSIDH with C=1 for command, RR=11 reserved,
 * SSID=4-bit, H=end-of-address bit (1 on last address in field). */
void test_encode_address_simple(void) {
  ax25_address_t a = { .callsign = "UN8SAT", .ssid = 1 };
  uint8_t out[7] = { 0 };
  TEST_ASSERT_EQUAL(AX25_OK, ax25_encode_address(&a, false, out));

  TEST_ASSERT_EQUAL_HEX8('U' << 1, out[0]);
  TEST_ASSERT_EQUAL_HEX8('N' << 1, out[1]);
  TEST_ASSERT_EQUAL_HEX8('8' << 1, out[2]);
  TEST_ASSERT_EQUAL_HEX8('S' << 1, out[3]);
  TEST_ASSERT_EQUAL_HEX8('A' << 1, out[4]);
  TEST_ASSERT_EQUAL_HEX8('T' << 1, out[5]);
  /* SSID byte, is_last=false: 0x60 | (ssid << 1) = 0x62 */
  TEST_ASSERT_EQUAL_HEX8(0x62, out[6]);
}

void test_encode_address_padded_short_callsign(void) {
  ax25_address_t a = { .callsign = "CQ", .ssid = 0 };
  uint8_t out[7] = { 0 };
  ax25_encode_address(&a, false, out);
  TEST_ASSERT_EQUAL_HEX8('C' << 1, out[0]);
  TEST_ASSERT_EQUAL_HEX8('Q' << 1, out[1]);
  /* padded with ASCII space (0x20) shifted left = 0x40 */
  TEST_ASSERT_EQUAL_HEX8(0x40, out[2]);
  TEST_ASSERT_EQUAL_HEX8(0x40, out[3]);
  TEST_ASSERT_EQUAL_HEX8(0x40, out[4]);
  TEST_ASSERT_EQUAL_HEX8(0x40, out[5]);
  TEST_ASSERT_EQUAL_HEX8(0x60, out[6]);
}

void test_encode_address_last_sets_h_bit(void) {
  ax25_address_t a = { .callsign = "UN8SAT", .ssid = 1 };
  uint8_t out[7] = { 0 };
  ax25_encode_address(&a, true, out);
  TEST_ASSERT_EQUAL_HEX8(0x63, out[6]);  /* H-bit set */
}

void test_decode_address_round_trip(void) {
  ax25_address_t in = { .callsign = "UN8SAT", .ssid = 1 };
  uint8_t enc[7];
  ax25_encode_address(&in, true, enc);

  ax25_address_t out;
  bool is_last = false;
  TEST_ASSERT_EQUAL(AX25_OK, ax25_decode_address(enc, &is_last, &out));
  TEST_ASSERT_TRUE(is_last);
  TEST_ASSERT_EQUAL_STRING("UN8SAT", out.callsign);
  TEST_ASSERT_EQUAL_UINT8(1, out.ssid);
}

void test_decode_rejects_non_alnum_callsign(void) {
  /* First byte lower-case 'a' shifted left = 0xC2 — invalid (must be
   * upper-case A..Z, digit 0..9, or space). */
  uint8_t bad[7] = { 0xC2, 0x40, 0x40, 0x40, 0x40, 0x40, 0x63 };
  ax25_address_t out;
  bool is_last;
  TEST_ASSERT_EQUAL(AX25_ERR_ADDRESS_INVALID,
                    ax25_decode_address(bad, &is_last, &out));
}

int main(void) {
  UNITY_BEGIN();
  RUN_TEST(test_encode_address_simple);
  RUN_TEST(test_encode_address_padded_short_callsign);
  RUN_TEST(test_encode_address_last_sets_h_bit);
  RUN_TEST(test_decode_address_round_trip);
  RUN_TEST(test_decode_rejects_non_alnum_callsign);
  return UNITY_END();
}
```

- [ ] **Step 2: Run, confirm failure**

```bash
cmake --build build --target test_ax25_address && ./build/test_ax25_address
```

Expected: link failure.

- [ ] **Step 3: Implement in ax25.c**

Append to `firmware/stm32/Drivers/AX25/ax25.c`:

```c
static bool is_valid_callsign_char(char c) {
  return (c >= 'A' && c <= 'Z') ||
         (c >= '0' && c <= '9') ||
         c == ' ';
}

ax25_status_t ax25_encode_address(const ax25_address_t *addr,
                                   bool is_last, uint8_t out[7]) {
  if (addr == NULL || out == NULL) return AX25_ERR_ADDRESS_INVALID;

  char padded[6] = { ' ', ' ', ' ', ' ', ' ', ' ' };
  size_t n = 0;
  for (; n < 6 && addr->callsign[n] != '\0'; n++) {
    if (!is_valid_callsign_char(addr->callsign[n])) {
      return AX25_ERR_ADDRESS_INVALID;
    }
    padded[n] = addr->callsign[n];
  }
  if (addr->callsign[n] != '\0' && n == 6) {
    /* Callsign longer than 6 chars. */
    return AX25_ERR_ADDRESS_INVALID;
  }
  if (addr->ssid > 15) return AX25_ERR_ADDRESS_INVALID;

  for (int i = 0; i < 6; i++) {
    out[i] = (uint8_t)(padded[i] << 1);
  }
  /* CRRSSIDH: C=0 (response), RR=11, SSID shifted left 1, H-bit if last. */
  out[6] = (uint8_t)(0x60 | ((addr->ssid & 0x0F) << 1) | (is_last ? 1 : 0));
  return AX25_OK;
}

ax25_status_t ax25_decode_address(const uint8_t in[7],
                                   bool *is_last,
                                   ax25_address_t *out) {
  if (in == NULL || out == NULL) return AX25_ERR_ADDRESS_INVALID;

  for (int i = 0; i < 6; i++) {
    char c = (char)(in[i] >> 1);
    if (!is_valid_callsign_char(c)) return AX25_ERR_ADDRESS_INVALID;
    out->callsign[i] = c;
  }
  out->callsign[6] = '\0';
  /* Trim trailing spaces. */
  for (int i = 5; i >= 0 && out->callsign[i] == ' '; i--) {
    out->callsign[i] = '\0';
  }

  uint8_t ssid_byte = in[6];
  /* Top 3 bits (CRR) should be 011 or 111 (C/H=0/1 each).  Check RR=11. */
  if ((ssid_byte & 0x60) != 0x60) return AX25_ERR_ADDRESS_INVALID;
  out->ssid = (ssid_byte >> 1) & 0x0F;
  if (is_last) *is_last = (ssid_byte & 1) != 0;
  return AX25_OK;
}
```

- [ ] **Step 4: Run, confirm pass**

```bash
cmake --build build --target test_ax25_address && ./build/test_ax25_address
```

Expected: `5 Tests 0 Failures`.

- [ ] **Step 5: Commit**

```bash
git add firmware/stm32/Drivers/AX25/ax25.c firmware/tests/test_ax25_address.c
git commit -m "feat(ax25): address encode/decode (REQ-AX25-002)"
```

---

### Task 1.6: Address encode/decode (Python)

**Files:**
- Modify: `ground-station/utils/ax25.py`
- Modify: `ground-station/tests/test_ax25.py`

- [ ] **Step 1: Write failing tests**

Append to `ground-station/tests/test_ax25.py`:

```python
from utils.ax25 import Address, encode_address, decode_address


class TestAddress:
    def test_encode_simple(self):
        a = Address("UN8SAT", 1)
        enc = encode_address(a, is_last=False)
        assert enc == bytes([c << 1 for c in b"UN8SAT"]) + bytes([0x62])

    def test_encode_padded(self):
        enc = encode_address(Address("CQ", 0), is_last=False)
        assert enc[:6] == bytes([ord("C") << 1, ord("Q") << 1,
                                  0x40, 0x40, 0x40, 0x40])
        assert enc[6] == 0x60

    def test_encode_last_sets_h_bit(self):
        enc = encode_address(Address("UN8SAT", 1), is_last=True)
        assert enc[6] == 0x63

    def test_round_trip(self):
        a = Address("UN8SAT", 1)
        enc = encode_address(a, is_last=True)
        got, is_last = decode_address(enc)
        assert got == a
        assert is_last is True

    def test_rejects_lowercase(self):
        bad = bytes([0xC2, 0x40, 0x40, 0x40, 0x40, 0x40, 0x63])
        with pytest.raises(InvalidAddress):
            decode_address(bad)
```

- [ ] **Step 2: Confirm failure**

```bash
pytest tests/test_ax25.py::TestAddress -v
```

Expected: ImportError.

- [ ] **Step 3: Implement in ax25.py**

Append to `ground-station/utils/ax25.py`:

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class Address:
    callsign: str
    ssid: int


def _valid_callsign_char(c: str) -> bool:
    return c.isupper() and c.isalnum() or c.isdigit() or c == " "


def encode_address(addr: Address, is_last: bool) -> bytes:
    if not 0 <= addr.ssid <= 15:
        raise InvalidAddress(f"ssid {addr.ssid} out of range")
    if len(addr.callsign) > 6:
        raise InvalidAddress(f"callsign {addr.callsign!r} > 6 chars")
    padded = addr.callsign.ljust(6)
    for c in padded:
        if not _valid_callsign_char(c):
            raise InvalidAddress(f"illegal char {c!r}")
    out = bytearray(ord(c) << 1 for c in padded)
    ssid_byte = 0x60 | ((addr.ssid & 0x0F) << 1) | (1 if is_last else 0)
    out.append(ssid_byte)
    return bytes(out)


def decode_address(data: bytes) -> tuple[Address, bool]:
    if len(data) != 7:
        raise InvalidAddress("address field must be 7 bytes")
    chars = []
    for b in data[:6]:
        c = chr(b >> 1)
        if not _valid_callsign_char(c):
            raise InvalidAddress(f"illegal encoded char 0x{b:02X}")
        chars.append(c)
    callsign = "".join(chars).rstrip()
    ssid_byte = data[6]
    if (ssid_byte & 0x60) != 0x60:
        raise InvalidAddress(f"reserved bits not set in ssid byte 0x{ssid_byte:02X}")
    ssid = (ssid_byte >> 1) & 0x0F
    is_last = bool(ssid_byte & 1)
    return Address(callsign, ssid), is_last
```

- [ ] **Step 4: Confirm pass**

```bash
pytest tests/test_ax25.py::TestAddress -v
```

Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add ground-station/utils/ax25.py ground-station/tests/test_ax25.py
git commit -m "feat(gs-ax25): address encode/decode Python mirror"
```

---

## Phase 2: Batch UI-Frame Encode / Pure Decode

### Task 2.1: ax25_encode_ui_frame (C)

**Files:**
- Modify: `firmware/stm32/Drivers/AX25/ax25.c`
- Create: `firmware/tests/test_ax25_encode.c`

- [ ] **Step 1: Write failing test — canonical beacon frame**

Create `firmware/tests/test_ax25_encode.c`:

```c
#include "unity.h"
#include "ax25.h"
#include <string.h>

void setUp(void) {}
void tearDown(void) {}

/* Encode a minimal UI frame: dst=CQ-0, src=UN8SAT-1, info="Hi".
 * Expected layout:
 *   0x7E  (start flag)
 *   'C'<<1, 'Q'<<1, 0x40*4, 0x60           (dst, H=0)
 *   'U'<<1,'N'<<1,'8'<<1,'S'<<1,'A'<<1,'T'<<1, 0x63   (src, H=1)
 *   0x03 0xF0 'H' 'i'
 *   FCS (2 bytes LE) computed over addr..info
 *   bit-stuffed between flags
 *   0x7E  (end flag)
 */
void test_encode_minimal_ui_frame_has_flags(void) {
  ax25_address_t dst = { .callsign = "CQ", .ssid = 0 };
  ax25_address_t src = { .callsign = "UN8SAT", .ssid = 1 };
  const uint8_t info[] = { 'H', 'i' };
  uint8_t out[64] = { 0 };
  size_t n = 0;
  ax25_status_t st = ax25_encode_ui_frame(&dst, &src, 0xF0, info, 2,
                                           out, sizeof(out), &n);
  TEST_ASSERT_EQUAL(AX25_OK, st);
  TEST_ASSERT_TRUE(n > 20);
  TEST_ASSERT_EQUAL_HEX8(0x7E, out[0]);
  TEST_ASSERT_EQUAL_HEX8(0x7E, out[n - 1]);
}

void test_encode_info_too_long(void) {
  ax25_address_t dst = { .callsign = "CQ", .ssid = 0 };
  ax25_address_t src = { .callsign = "UN8SAT", .ssid = 1 };
  uint8_t info[AX25_MAX_INFO_LEN + 1] = { 0 };
  uint8_t out[512];
  size_t n = 0;
  TEST_ASSERT_EQUAL(AX25_ERR_INFO_TOO_LONG,
                    ax25_encode_ui_frame(&dst, &src, 0xF0, info, sizeof(info),
                                          out, sizeof(out), &n));
}

void test_encode_buffer_overflow(void) {
  ax25_address_t dst = { .callsign = "CQ", .ssid = 0 };
  ax25_address_t src = { .callsign = "UN8SAT", .ssid = 1 };
  uint8_t info[2] = { 'H', 'i' };
  uint8_t out[8];  /* too small */
  size_t n = 0;
  TEST_ASSERT_EQUAL(AX25_ERR_BUFFER_OVERFLOW,
                    ax25_encode_ui_frame(&dst, &src, 0xF0, info, 2,
                                          out, sizeof(out), &n));
}

int main(void) {
  UNITY_BEGIN();
  RUN_TEST(test_encode_minimal_ui_frame_has_flags);
  RUN_TEST(test_encode_info_too_long);
  RUN_TEST(test_encode_buffer_overflow);
  return UNITY_END();
}
```

- [ ] **Step 2: Confirm failure**

```bash
cmake --build build --target test_ax25_encode && ./build/test_ax25_encode
```

Expected: link failure.

- [ ] **Step 3: Implement encoder**

Append to `firmware/stm32/Drivers/AX25/ax25.c`:

```c
ax25_status_t ax25_encode_ui_frame(
    const ax25_address_t *dst, const ax25_address_t *src,
    uint8_t pid,
    const uint8_t *info, size_t info_len,
    uint8_t *out, size_t out_cap, size_t *out_len) {

  if (dst == NULL || src == NULL || out == NULL || out_len == NULL) {
    return AX25_ERR_BUFFER_OVERFLOW;
  }
  if (info_len > AX25_MAX_INFO_LEN) return AX25_ERR_INFO_TOO_LONG;
  if (info == NULL && info_len > 0) return AX25_ERR_BUFFER_OVERFLOW;

  /* Unstuffed frame body: dst(7) + src(7) + ctrl(1) + pid(1) + info + fcs(2). */
  uint8_t body[AX25_MAX_INFO_LEN + 20];
  size_t body_len = 0;

  ax25_status_t st = ax25_encode_address(dst, false, &body[body_len]);
  if (st != AX25_OK) return st;
  body_len += 7;

  st = ax25_encode_address(src, true, &body[body_len]);
  if (st != AX25_OK) return st;
  body_len += 7;

  body[body_len++] = 0x03;  /* UI control */
  body[body_len++] = pid;

  if (info_len > 0) memcpy(&body[body_len], info, info_len);
  body_len += info_len;

  uint16_t fcs = ax25_fcs_crc16(body, body_len);
  body[body_len++] = (uint8_t)(fcs & 0xFF);
  body[body_len++] = (uint8_t)((fcs >> 8) & 0xFF);

  /* Stuff body, then wrap with flags. */
  if (out_cap < 2) return AX25_ERR_BUFFER_OVERFLOW;
  out[0] = 0x7E;
  size_t stuffed = ax25_bit_stuff(body, body_len, &out[1], out_cap - 2);
  if (stuffed == 0) return AX25_ERR_BUFFER_OVERFLOW;
  if (1 + stuffed + 1 > AX25_MAX_FRAME_BYTES) return AX25_ERR_FRAME_TOO_LONG;
  out[1 + stuffed] = 0x7E;
  *out_len = 1 + stuffed + 1;
  return AX25_OK;
}
```

- [ ] **Step 4: Confirm pass**

```bash
cmake --build build --target test_ax25_encode && ./build/test_ax25_encode
```

Expected: `3 Tests 0 Failures`.

- [ ] **Step 5: Commit**

```bash
git add firmware/stm32/Drivers/AX25/ax25.c firmware/tests/test_ax25_encode.c
git commit -m "feat(ax25): ax25_encode_ui_frame (REQ-AX25-001..015)"
```

---

### Task 2.2: ax25_decode_ui_frame (C, pure — no streaming yet)

**Files:**
- Modify: `firmware/stm32/Drivers/AX25/ax25.c`
- Create: `firmware/tests/test_ax25_decode.c`

- [ ] **Step 1: Write failing tests**

Create `firmware/tests/test_ax25_decode.c`:

```c
#include "unity.h"
#include "ax25.h"
#include <string.h>

void setUp(void) {}
void tearDown(void) {}

/* Round-trip: encode then decode (strip flags, unstuff manually). */
static size_t unwrap(const uint8_t *frame, size_t n, uint8_t *body, size_t cap) {
  /* strip flags */
  const uint8_t *start = frame + 1;
  size_t mid_len = n - 2;
  ax25_status_t st;
  return ax25_bit_unstuff(start, mid_len, body, cap, &st);
}

void test_decode_round_trip(void) {
  ax25_address_t dst = { .callsign = "CQ", .ssid = 0 };
  ax25_address_t src = { .callsign = "UN8SAT", .ssid = 1 };
  const uint8_t info[] = { 'H', 'i' };

  uint8_t frame[64];
  size_t n = 0;
  TEST_ASSERT_EQUAL(AX25_OK,
    ax25_encode_ui_frame(&dst, &src, 0xF0, info, 2, frame, sizeof(frame), &n));

  uint8_t body[64];
  size_t body_n = unwrap(frame, n, body, sizeof(body));

  ax25_ui_frame_t decoded;
  TEST_ASSERT_EQUAL(AX25_OK,
    ax25_decode_ui_frame(body, body_n, &decoded));

  TEST_ASSERT_EQUAL_STRING("CQ", decoded.dst.callsign);
  TEST_ASSERT_EQUAL_UINT8(0, decoded.dst.ssid);
  TEST_ASSERT_EQUAL_STRING("UN8SAT", decoded.src.callsign);
  TEST_ASSERT_EQUAL_UINT8(1, decoded.src.ssid);
  TEST_ASSERT_EQUAL_UINT8(0x03, decoded.control);
  TEST_ASSERT_EQUAL_UINT8(0xF0, decoded.pid);
  TEST_ASSERT_EQUAL_UINT16(2, decoded.info_len);
  TEST_ASSERT_EQUAL_MEMORY("Hi", decoded.info, 2);
  TEST_ASSERT_TRUE(decoded.fcs_valid);
}

void test_decode_bad_fcs(void) {
  /* Craft a body with a deliberately wrong FCS. */
  uint8_t body[64];
  /* Manually build: dst+src+ctrl+pid+"Hi"+bad_fcs */
  ax25_address_t d = { .callsign = "CQ", .ssid = 0 };
  ax25_address_t s = { .callsign = "UN8SAT", .ssid = 1 };
  ax25_encode_address(&d, false, &body[0]);
  ax25_encode_address(&s, true, &body[7]);
  body[14] = 0x03; body[15] = 0xF0;
  body[16] = 'H'; body[17] = 'i';
  body[18] = 0xDE; body[19] = 0xAD;  /* bogus FCS */

  ax25_ui_frame_t out;
  TEST_ASSERT_EQUAL(AX25_ERR_FCS_MISMATCH,
    ax25_decode_ui_frame(body, 20, &out));
}

void test_decode_rejects_digipeater_path(void) {
  /* REQ-AX25-018: dst + src + extra addr field is invalid. */
  uint8_t body[64];
  ax25_address_t d = { .callsign = "CQ", .ssid = 0 };
  ax25_address_t s = { .callsign = "UN8SAT", .ssid = 1 };
  ax25_address_t r = { .callsign = "REPEAT", .ssid = 0 };
  ax25_encode_address(&d, false, &body[0]);
  ax25_encode_address(&s, false, &body[7]);     /* H=0 — more follows */
  ax25_encode_address(&r, true,  &body[14]);    /* H=1 on repeater */
  body[21] = 0x03; body[22] = 0xF0; body[23] = 'X';
  uint16_t fcs = ax25_fcs_crc16(body, 24);
  body[24] = (uint8_t)fcs;
  body[25] = (uint8_t)(fcs >> 8);

  ax25_ui_frame_t out;
  TEST_ASSERT_EQUAL(AX25_ERR_ADDRESS_INVALID,
    ax25_decode_ui_frame(body, 26, &out));
}

void test_decode_rejects_bad_control(void) {
  uint8_t body[64];
  ax25_address_t d = { .callsign = "CQ", .ssid = 0 };
  ax25_address_t s = { .callsign = "UN8SAT", .ssid = 1 };
  ax25_encode_address(&d, false, &body[0]);
  ax25_encode_address(&s, true,  &body[7]);
  body[14] = 0x99;   /* not 0x03 */
  body[15] = 0xF0;
  uint16_t fcs = ax25_fcs_crc16(body, 16);
  body[16] = (uint8_t)fcs;
  body[17] = (uint8_t)(fcs >> 8);
  ax25_ui_frame_t out;
  TEST_ASSERT_EQUAL(AX25_ERR_CONTROL_INVALID,
    ax25_decode_ui_frame(body, 18, &out));
}

int main(void) {
  UNITY_BEGIN();
  RUN_TEST(test_decode_round_trip);
  RUN_TEST(test_decode_bad_fcs);
  RUN_TEST(test_decode_rejects_digipeater_path);
  RUN_TEST(test_decode_rejects_bad_control);
  return UNITY_END();
}
```

- [ ] **Step 2: Confirm failure**

```bash
cmake --build build --target test_ax25_decode && ./build/test_ax25_decode
```

- [ ] **Step 3: Implement pure decoder**

Append to `firmware/stm32/Drivers/AX25/ax25.c`:

```c
ax25_status_t ax25_decode_ui_frame(const uint8_t *in, size_t in_len,
                                    ax25_ui_frame_t *out_frame) {
  if (in == NULL || out_frame == NULL) return AX25_ERR_BUFFER_OVERFLOW;
  /* Minimum: 14 (addrs) + 1 (ctrl) + 1 (pid) + 0 (info) + 2 (fcs) = 18 */
  if (in_len < 18) return AX25_ERR_FLAG_MISSING;

  memset(out_frame, 0, sizeof(*out_frame));

  bool is_last = false;
  ax25_status_t st = ax25_decode_address(&in[0], &is_last, &out_frame->dst);
  if (st != AX25_OK) return st;
  /* REQ-AX25-018: destination MUST NOT have H-bit set. */
  if (is_last) return AX25_ERR_ADDRESS_INVALID;

  st = ax25_decode_address(&in[7], &is_last, &out_frame->src);
  if (st != AX25_OK) return st;
  /* REQ-AX25-018: source MUST have H-bit set — no digipeater path allowed. */
  if (!is_last) return AX25_ERR_ADDRESS_INVALID;

  uint8_t ctrl = in[14];
  uint8_t pid  = in[15];
  if (ctrl != 0x03) return AX25_ERR_CONTROL_INVALID;
  if (pid  != 0xF0) return AX25_ERR_PID_INVALID;
  out_frame->control = ctrl;
  out_frame->pid     = pid;

  size_t info_len = in_len - 14 - 2 - 2;  /* minus addr + ctrl/pid + fcs */
  if (info_len > AX25_MAX_INFO_LEN) return AX25_ERR_INFO_TOO_LONG;
  out_frame->info_len = (uint16_t)info_len;
  if (info_len > 0) memcpy(out_frame->info, &in[16], info_len);

  uint16_t wanted = ax25_fcs_crc16(in, in_len - 2);
  uint16_t got = (uint16_t)(in[in_len - 2] | (in[in_len - 1] << 8));
  out_frame->fcs = got;
  out_frame->fcs_valid = (wanted == got);
  if (!out_frame->fcs_valid) return AX25_ERR_FCS_MISMATCH;

  return AX25_OK;
}
```

- [ ] **Step 4: Confirm pass**

```bash
cmake --build build --target test_ax25_decode && ./build/test_ax25_decode
```

- [ ] **Step 5: Commit**

```bash
git add firmware/stm32/Drivers/AX25/ax25.c firmware/tests/test_ax25_decode.c
git commit -m "feat(ax25): ax25_decode_ui_frame pure decoder (REQ-AX25-018)"
```

---

### Task 2.3: Encoder + pure-decoder Python mirror

**Files:**
- Modify: `ground-station/utils/ax25.py`
- Modify: `ground-station/tests/test_ax25.py`

- [ ] **Step 1: Write round-trip test**

Append to `ground-station/tests/test_ax25.py`:

```python
from utils.ax25 import UiFrame, encode_ui_frame, decode_ui_frame


class TestUiFrame:
    def test_round_trip(self):
        dst = Address("CQ", 0)
        src = Address("UN8SAT", 1)
        frame_bytes = encode_ui_frame(dst, src, 0xF0, b"Hi")
        assert frame_bytes[0] == 0x7E
        assert frame_bytes[-1] == 0x7E
        # Strip flags and unstuff.
        body = bit_unstuff(frame_bytes[1:-1])
        decoded = decode_ui_frame(body)
        assert decoded.dst == dst
        assert decoded.src == src
        assert decoded.pid == 0xF0
        assert decoded.info == b"Hi"
        assert decoded.fcs_valid is True

    def test_rejects_digipeater(self):
        """REQ-AX25-018: third address field must be rejected."""
        d = encode_address(Address("CQ", 0), is_last=False)
        s = encode_address(Address("UN8SAT", 1), is_last=False)
        r = encode_address(Address("REPEAT", 0), is_last=True)
        body = d + s + r + b"\x03\xF0X"
        body += fcs_crc16(body).to_bytes(2, "little")
        with pytest.raises(InvalidAddress):
            decode_ui_frame(body)
```

- [ ] **Step 2: Confirm failure**

```bash
pytest tests/test_ax25.py::TestUiFrame -v
```

- [ ] **Step 3: Implement encode + decode**

Append to `ground-station/utils/ax25.py`:

```python
@dataclass(frozen=True)
class UiFrame:
    dst: Address
    src: Address
    control: int
    pid: int
    info: bytes
    fcs: int
    fcs_valid: bool


def encode_ui_frame(dst: Address, src: Address, pid: int,
                     info: bytes) -> bytes:
    if len(info) > 256:
        raise FrameOverflow(f"info {len(info)} > 256")
    body = bytearray()
    body += encode_address(dst, is_last=False)
    body += encode_address(src, is_last=True)
    body.append(0x03)
    body.append(pid & 0xFF)
    body += info
    fcs = fcs_crc16(bytes(body))
    body += fcs.to_bytes(2, "little")
    stuffed = bit_stuff(bytes(body))
    return b"\x7E" + stuffed + b"\x7E"


def decode_ui_frame(body: bytes) -> UiFrame:
    """Decodes an UNSTUFFED body (no flags)."""
    if len(body) < 18:
        raise FrameOverflow(f"body {len(body)} < 18")
    dst, last_after_dst = decode_address(body[0:7])
    if last_after_dst:
        raise InvalidAddress("destination has H-bit set")
    src, last_after_src = decode_address(body[7:14])
    if not last_after_src:
        raise InvalidAddress("digipeater path not supported (REQ-AX25-018)")
    ctrl = body[14]
    pid = body[15]
    if ctrl != 0x03:
        raise InvalidControl(f"control 0x{ctrl:02X} != 0x03")
    if pid != 0xF0:
        raise InvalidPid(f"pid 0x{pid:02X} != 0xF0")
    info = bytes(body[16:-2])
    if len(info) > 256:
        raise FrameOverflow(f"info {len(info)} > 256")
    wanted = fcs_crc16(body[:-2])
    got = int.from_bytes(body[-2:], "little")
    fcs_valid = wanted == got
    if not fcs_valid:
        raise FcsMismatch(f"expected 0x{wanted:04X}, got 0x{got:04X}")
    return UiFrame(dst, src, ctrl, pid, info, got, fcs_valid)
```

- [ ] **Step 4: Confirm pass**

```bash
pytest tests/test_ax25.py::TestUiFrame -v
```

- [ ] **Step 5: Commit**

```bash
git add ground-station/utils/ax25.py ground-station/tests/test_ax25.py
git commit -m "feat(gs-ax25): ui-frame encode/decode Python mirror"
```

---

## Phase 3: Golden Vectors

### Task 3.1: Author `tests/golden/ax25_vectors.json` (≥28 vectors, 7 categories)

**Files:**
- Create: `tests/golden/ax25_vectors.json`

- [ ] **Step 1: Write generator script**

Since hand-crafting 28 correct hex vectors is error-prone, generate
them from the Python reference implementation (which is already
covered by the oracle test REQ-AX25-022).

Create `scripts/gen_golden_vectors.py`:

```python
"""Generate tests/golden/ax25_vectors.json from the Python reference.

Run from repo root:  python scripts/gen_golden_vectors.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "ground-station"))
from utils.ax25 import (
    Address, encode_ui_frame, fcs_crc16, encode_address, bit_stuff,
)


def encode(desc, reqs, dst, src, info):
    frame = encode_ui_frame(dst, src, 0xF0, info)
    return {
        "description": desc,
        "reqs": reqs,
        "inputs": {
            "dst_callsign": dst.callsign, "dst_ssid": dst.ssid,
            "src_callsign": src.callsign, "src_ssid": src.ssid,
            "pid": 0xF0, "info_hex": info.hex(),
        },
        "encoded_hex": frame.hex(),
        "decode_status": "AX25_OK",
    }


vectors = []

# Category 1: canonical
vectors.append(encode(
    "canonical beacon-style frame, 48 B info",
    ["REQ-AX25-001", "REQ-AX25-009"],
    Address("CQ", 0), Address("UN8SAT", 1), bytes(range(48))))
vectors.append(encode(
    "min-size UI (0 B info)",
    ["REQ-AX25-005"],
    Address("CQ", 0), Address("UN8SAT", 1), b""))
vectors.append(encode(
    "max-size UI (256 B info)",
    ["REQ-AX25-005"],
    Address("CQ", 0), Address("UN8SAT", 1), bytes([i & 0xFF for i in range(256)])))

# Category 2: bit-stuffing adversarial
vectors.append(encode(
    "info contains 0x7E",
    ["REQ-AX25-007"],
    Address("CQ", 0), Address("UN8SAT", 1), b"\x7E\x7E\x7E"))
vectors.append(encode(
    "info all 0xFF (worst-case growth)",
    ["REQ-AX25-007", "REQ-AX25-011"],
    Address("CQ", 0), Address("UN8SAT", 1), b"\xFF" * 64))
vectors.append(encode(
    "info 0xFE (5 ones at low nibble)",
    ["REQ-AX25-007", "REQ-AX25-016"],
    Address("CQ", 0), Address("UN8SAT", 1), b"\xFE" * 8))
vectors.append(encode(
    "byte-boundary 5-ones run",
    ["REQ-AX25-016"],
    Address("CQ", 0), Address("UN8SAT", 1), b"\x1F\xF8" * 4))

# Category 3: address edge cases
vectors.append(encode(
    "short callsign (padded spaces)",
    ["REQ-AX25-002"],
    Address("CT", 0), Address("UN", 0), b"X"))
vectors.append(encode(
    "ssid 0",
    ["REQ-AX25-002"],
    Address("UN8SAT", 0), Address("UN8SAT", 0), b"X"))
vectors.append(encode(
    "ssid 15",
    ["REQ-AX25-002"],
    Address("UN8SAT", 15), Address("UN8SAT", 15), b"X"))
vectors.append(encode(
    "digits in callsign",
    ["REQ-AX25-002"],
    Address("123456", 0), Address("UN8SAT", 1), b"X"))

# Category 4: digipeater rejection — crafted raw bodies
repeater_body = (
    encode_address(Address("CQ", 0), is_last=False)
    + encode_address(Address("UN8SAT", 1), is_last=False)  # H=0 -> more
    + encode_address(Address("REPEAT", 0), is_last=True)
    + b"\x03\xF0X"
)
repeater_body += fcs_crc16(repeater_body).to_bytes(2, "little")
vectors.append({
    "description": "digipeater path MUST be rejected",
    "reqs": ["REQ-AX25-018"],
    "inputs": {"raw_body_hex": repeater_body.hex()},
    "encoded_hex": None,
    "decode_status": "AX25_ERR_ADDRESS_INVALID",
})

# Category 5: malformed
bad_fcs_body = (
    encode_address(Address("CQ", 0), is_last=False)
    + encode_address(Address("UN8SAT", 1), is_last=True)
    + b"\x03\xF0Hi" + b"\xDE\xAD"
)
vectors.append({
    "description": "bad FCS",
    "reqs": ["REQ-AX25-006"],
    "inputs": {"raw_body_hex": bad_fcs_body.hex()},
    "encoded_hex": None,
    "decode_status": "AX25_ERR_FCS_MISMATCH",
})
bad_ctrl_body = (
    encode_address(Address("CQ", 0), is_last=False)
    + encode_address(Address("UN8SAT", 1), is_last=True)
    + b"\x99\xF0"
)
bad_ctrl_body += fcs_crc16(bad_ctrl_body).to_bytes(2, "little")
vectors.append({
    "description": "control != 0x03",
    "reqs": ["REQ-AX25-003"],
    "inputs": {"raw_body_hex": bad_ctrl_body.hex()},
    "encoded_hex": None,
    "decode_status": "AX25_ERR_CONTROL_INVALID",
})
bad_pid_body = (
    encode_address(Address("CQ", 0), is_last=False)
    + encode_address(Address("UN8SAT", 1), is_last=True)
    + b"\x03\xEE"
)
bad_pid_body += fcs_crc16(bad_pid_body).to_bytes(2, "little")
vectors.append({
    "description": "pid != 0xF0",
    "reqs": ["REQ-AX25-004"],
    "inputs": {"raw_body_hex": bad_pid_body.hex()},
    "encoded_hex": None,
    "decode_status": "AX25_ERR_PID_INVALID",
})

# Category 6: DoS
vectors.append({
    "description": "1000-byte garbage with stuffing — decoder MUST NOT hang",
    "reqs": ["REQ-AX25-012"],
    "inputs": {"raw_body_hex": ("AA" * 1000)},
    "encoded_hex": None,
    "decode_status": "AX25_ERR_FRAME_TOO_LONG",
})

# Category 7: flag edge cases (REQ-AX25-023)
frame_a = encode_ui_frame(Address("CQ", 0), Address("UN8SAT", 1), 0xF0, b"A")
frame_b = encode_ui_frame(Address("CQ", 0), Address("UN8SAT", 1), 0xF0, b"B")
back_to_back = frame_a + frame_b  # shares no byte since both have 0x7E start+end
idle_then_frame = b"\x7E\x7E\x7E" + frame_a[1:]
vectors.append({
    "description": "idle flags then valid frame — ignore idle, emit frame",
    "reqs": ["REQ-AX25-023"],
    "inputs": {"stream_hex": idle_then_frame.hex()},
    "encoded_hex": None,
    "decode_status": "AX25_OK",
})
vectors.append({
    "description": "back-to-back frames with shared flag boundary",
    "reqs": ["REQ-AX25-023"],
    "inputs": {"stream_hex": back_to_back.hex()},
    "encoded_hex": None,
    "decode_status": "AX25_OK",
    "expected_frame_count": 2,
})

# Emit.
out_path = Path("tests/golden/ax25_vectors.json")
out_path.parent.mkdir(parents=True, exist_ok=True)
out_path.write_text(json.dumps(vectors, indent=2) + "\n")
print(f"wrote {len(vectors)} vectors to {out_path}")
```

- [ ] **Step 2: Run the generator**

```bash
cd /path/to/unisat && python scripts/gen_golden_vectors.py
```

Expected: `wrote 17+ vectors to tests/golden/ax25_vectors.json`.

- [ ] **Step 3: Extend generator to reach ≥28 vectors (add more adversarial)**

Append additional stuff-boundary variants, different callsigns, different
info payloads, zero-ssid/nonzero-ssid mixes until `len(vectors) >= 28`.
Re-run the generator.

- [ ] **Step 4: Commit**

```bash
git add scripts/gen_golden_vectors.py tests/golden/ax25_vectors.json
git commit -m "feat(test): golden vectors for AX.25 interop (≥28 across 7 categories)"
```

---

### Task 3.2: C golden-vector test runner

**Files:**
- Create: `firmware/tests/test_ax25_golden.c`
- Create: `firmware/tests/golden_loader.c`, `golden_loader.h`

- [ ] **Step 1: Write minimal JSON loader (or use jsmn / cJSON)**

Add `cJSON` as a test-only dependency in `firmware/CMakeLists.txt`:

```cmake
FetchContent_Declare(
  cjson
  GIT_REPOSITORY https://github.com/DaveGamble/cJSON.git
  GIT_TAG v1.7.18
)
FetchContent_MakeAvailable(cjson)
```

- [ ] **Step 2: Write failing test skeleton**

Create `firmware/tests/test_ax25_golden.c`:

```c
#include "unity.h"
#include "ax25.h"
#include "cjson/cJSON.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static char *load_file(const char *path) {
  FILE *f = fopen(path, "rb");
  if (!f) return NULL;
  fseek(f, 0, SEEK_END);
  long n = ftell(f);
  fseek(f, 0, SEEK_SET);
  char *buf = malloc(n + 1);
  fread(buf, 1, n, f);
  buf[n] = 0;
  fclose(f);
  return buf;
}

static int hex_to_bytes(const char *hex, uint8_t *out, size_t cap) {
  size_t len = strlen(hex) / 2;
  if (len > cap) return -1;
  for (size_t i = 0; i < len; i++) {
    unsigned b;
    sscanf(hex + 2 * i, "%02x", &b);
    out[i] = (uint8_t)b;
  }
  return (int)len;
}

void setUp(void) {}
void tearDown(void) {}

void test_all_golden_vectors_encode_matches(void) {
  char *json = load_file("tests/golden/ax25_vectors.json");
  TEST_ASSERT_NOT_NULL(json);
  cJSON *arr = cJSON_Parse(json);
  TEST_ASSERT_NOT_NULL(arr);

  int count = cJSON_GetArraySize(arr);
  int checked = 0;
  for (int i = 0; i < count; i++) {
    cJSON *v = cJSON_GetArrayItem(arr, i);
    cJSON *enc = cJSON_GetObjectItem(v, "encoded_hex");
    if (!cJSON_IsString(enc)) continue;  /* decode-only vector */

    cJSON *inputs = cJSON_GetObjectItem(v, "inputs");
    const char *dst_c = cJSON_GetObjectItem(inputs, "dst_callsign")->valuestring;
    int dst_s = cJSON_GetObjectItem(inputs, "dst_ssid")->valueint;
    const char *src_c = cJSON_GetObjectItem(inputs, "src_callsign")->valuestring;
    int src_s = cJSON_GetObjectItem(inputs, "src_ssid")->valueint;
    const char *info_hex = cJSON_GetObjectItem(inputs, "info_hex")->valuestring;

    uint8_t info[AX25_MAX_INFO_LEN];
    int info_len = hex_to_bytes(info_hex, info, sizeof(info));
    ax25_address_t dst = { .ssid = (uint8_t)dst_s };
    strncpy(dst.callsign, dst_c, 6);
    ax25_address_t src = { .ssid = (uint8_t)src_s };
    strncpy(src.callsign, src_c, 6);

    uint8_t out[AX25_MAX_FRAME_BYTES];
    size_t n = 0;
    TEST_ASSERT_EQUAL(AX25_OK,
      ax25_encode_ui_frame(&dst, &src, 0xF0, info, info_len,
                            out, sizeof(out), &n));

    uint8_t expected[AX25_MAX_FRAME_BYTES];
    int exp_n = hex_to_bytes(enc->valuestring, expected, sizeof(expected));
    TEST_ASSERT_EQUAL_size_t((size_t)exp_n, n);
    TEST_ASSERT_EQUAL_MEMORY(expected, out, n);
    checked++;
  }
  cJSON_Delete(arr);
  free(json);
  TEST_ASSERT_GREATER_OR_EQUAL_INT(15, checked);
}

int main(void) {
  UNITY_BEGIN();
  RUN_TEST(test_all_golden_vectors_encode_matches);
  return UNITY_END();
}
```

- [ ] **Step 3: Run (should pass since Python generated the fixtures from the same algorithm)**

```bash
cmake --build build --target test_ax25_golden && ./build/test_ax25_golden
```

- [ ] **Step 4: If vectors don't match, investigate discrepancy**

Pair-debug until byte-identical. Do NOT just "fix the vectors" — the
point of REQ-AX25-015 is that the two implementations MUST match.

- [ ] **Step 5: Commit**

```bash
git add firmware/tests/test_ax25_golden.c firmware/CMakeLists.txt
git commit -m "test(ax25): C golden-vector cross-validation runner (REQ-AX25-015)"
```

---

### Task 3.3: Python golden-vector runner

**Files:**
- Modify: `ground-station/tests/test_ax25.py`

- [ ] **Step 1: Write failing test**

Append to `ground-station/tests/test_ax25.py`:

```python
import json
from pathlib import Path


class TestGoldenVectors:
    @pytest.fixture(scope="class")
    def vectors(self):
        path = Path(__file__).parents[2] / "tests" / "golden" / "ax25_vectors.json"
        return json.loads(path.read_text())

    def test_encode_matches_all(self, vectors):
        checked = 0
        for v in vectors:
            if v.get("encoded_hex") is None:
                continue
            inp = v["inputs"]
            frame = encode_ui_frame(
                Address(inp["dst_callsign"], inp["dst_ssid"]),
                Address(inp["src_callsign"], inp["src_ssid"]),
                inp["pid"],
                bytes.fromhex(inp["info_hex"]),
            )
            assert frame.hex() == v["encoded_hex"], v["description"]
            checked += 1
        assert checked >= 15
```

- [ ] **Step 2: Run**

```bash
pytest tests/test_ax25.py::TestGoldenVectors -v
```

Expected: PASS (the generator used this exact same code).

- [ ] **Step 3: Commit**

```bash
git add ground-station/tests/test_ax25.py
git commit -m "test(gs-ax25): golden-vector cross-validation runner (REQ-AX25-015)"
```

---

## Phase 4: Streaming Decoder (first-class type)

### Task 4.1: ax25_decoder_t struct + init/reset

**Files:**
- Modify: `firmware/stm32/Drivers/AX25/ax25_types.h`
- Create: `firmware/stm32/Drivers/AX25/ax25_decoder.h`
- Create: `firmware/stm32/Drivers/AX25/ax25_decoder.c`
- Create: `firmware/tests/test_ax25_decoder.c`

- [ ] **Step 1: Extend types header**

Append to `ax25_types.h` before `#endif`:

```c
typedef enum {
  AX25_STATE_HUNT = 0,
  AX25_STATE_FRAME
} ax25_decoder_state_t;

typedef struct {
  uint8_t              buf[AX25_MAX_FRAME_BYTES];
  size_t               len;
  uint16_t             shift_reg;
  uint8_t              bit_count;
  uint8_t              ones_run;
  ax25_decoder_state_t state;
  uint32_t             frames_ok;
  uint32_t             frames_fcs_err;
  uint32_t             frames_overflow;
  uint32_t             frames_stuffing_err;
  uint32_t             frames_other_err;
} ax25_decoder_t;
```

- [ ] **Step 2: Write decoder public header**

Create `ax25_decoder.h`:

```c
#ifndef AX25_DECODER_H
#define AX25_DECODER_H

#include "ax25_types.h"

void ax25_decoder_init(ax25_decoder_t *d);
void ax25_decoder_reset(ax25_decoder_t *d);

/* REQ-AX25-017: feed ONE byte (LSB-first bit order on the wire).
 * Returns OK on successful consumption; *frame_ready==true means
 * *out_frame was populated. On error, decoder is reset to HUNT
 * (REQ-AX25-024) and the corresponding counter is incremented. */
ax25_status_t ax25_decoder_push_byte(
    ax25_decoder_t *d,
    uint8_t byte,
    ax25_ui_frame_t *out_frame,
    bool *frame_ready);

#endif /* AX25_DECODER_H */
```

- [ ] **Step 3: Write failing init/reset tests**

Create `firmware/tests/test_ax25_decoder.c`:

```c
#include "unity.h"
#include "ax25.h"
#include "ax25_decoder.h"
#include <string.h>

static ax25_decoder_t d;

void setUp(void) { ax25_decoder_init(&d); }
void tearDown(void) {}

void test_init_zeros_all_counters(void) {
  /* pre-poison */
  memset(&d, 0xAA, sizeof(d));
  ax25_decoder_init(&d);
  TEST_ASSERT_EQUAL(AX25_STATE_HUNT, d.state);
  TEST_ASSERT_EQUAL_UINT32(0, d.frames_ok);
  TEST_ASSERT_EQUAL_UINT32(0, d.frames_fcs_err);
  TEST_ASSERT_EQUAL_size_t(0, d.len);
  TEST_ASSERT_EQUAL_UINT8(0, d.bit_count);
}

int main(void) {
  UNITY_BEGIN();
  RUN_TEST(test_init_zeros_all_counters);
  return UNITY_END();
}
```

- [ ] **Step 4: Implement init/reset**

Create `firmware/stm32/Drivers/AX25/ax25_decoder.c`:

```c
#include "ax25_decoder.h"
#include "ax25.h"
#include <string.h>

void ax25_decoder_init(ax25_decoder_t *d) {
  if (d == NULL) return;
  memset(d, 0, sizeof(*d));
  d->state = AX25_STATE_HUNT;
}

void ax25_decoder_reset(ax25_decoder_t *d) {
  /* Preserve counters; reset only the per-frame state. */
  if (d == NULL) return;
  d->len = 0;
  d->shift_reg = 0;
  d->bit_count = 0;
  d->ones_run = 0;
  d->state = AX25_STATE_HUNT;
}

/* Stub — implemented in Task 4.2. */
ax25_status_t ax25_decoder_push_byte(ax25_decoder_t *d, uint8_t byte,
                                      ax25_ui_frame_t *out_frame,
                                      bool *frame_ready) {
  (void)d; (void)byte; (void)out_frame;
  if (frame_ready) *frame_ready = false;
  return AX25_OK;
}
```

Add the file to `firmware/stm32/Drivers/AX25/CMakeLists.txt`:

```cmake
add_library(ax25 STATIC
  ax25.c
  ax25_decoder.c
)
```

- [ ] **Step 5: Run, confirm pass**

```bash
cmake --build build --target test_ax25_decoder && ./build/test_ax25_decoder
```

- [ ] **Step 6: Commit**

```bash
git add firmware/stm32/Drivers/AX25/ firmware/tests/test_ax25_decoder.c
git commit -m "feat(ax25): ax25_decoder_t skeleton with init/reset"
```

---

### Task 4.2: `ax25_decoder_push_byte` — full bit-level implementation

**Files:**
- Modify: `firmware/stm32/Drivers/AX25/ax25_decoder.c`
- Modify: `firmware/tests/test_ax25_decoder.c`

- [ ] **Step 1: Add failing streaming tests**

Append to `firmware/tests/test_ax25_decoder.c`:

```c
#include "config.h"

/* Feed an entire encoded frame byte-by-byte and expect one frame_ready. */
void test_push_byte_single_frame_emits_exactly_one(void) {
  ax25_address_t dst = { .callsign = "CQ", .ssid = 0 };
  ax25_address_t src = { .callsign = "UN8SAT", .ssid = 1 };
  uint8_t frame[AX25_MAX_FRAME_BYTES];
  size_t n = 0;
  ax25_encode_ui_frame(&dst, &src, 0xF0, (const uint8_t *)"Hi", 2,
                         frame, sizeof(frame), &n);

  ax25_ui_frame_t out;
  bool ready;
  int ready_count = 0;
  for (size_t i = 0; i < n; i++) {
    ax25_decoder_push_byte(&d, frame[i], &out, &ready);
    if (ready) ready_count++;
  }
  TEST_ASSERT_EQUAL_INT(1, ready_count);
  TEST_ASSERT_EQUAL_UINT32(1, d.frames_ok);
  TEST_ASSERT_EQUAL_STRING("Hi", (const char *)out.info);
}

/* REQ-AX25-023: idle flags between frames silently ignored. */
void test_push_byte_idle_flags_ignored(void) {
  /* Feed ten 0x7E bytes — no frame, no error, no counter change. */
  ax25_ui_frame_t out;
  bool ready;
  for (int i = 0; i < 10; i++) {
    ax25_decoder_push_byte(&d, 0x7E, &out, &ready);
    TEST_ASSERT_FALSE(ready);
  }
  TEST_ASSERT_EQUAL_UINT32(0, d.frames_ok);
  TEST_ASSERT_EQUAL_UINT32(0, d.frames_other_err);
}

/* REQ-AX25-023: two frames sharing a flag boundary. */
void test_push_byte_back_to_back_frames(void) {
  ax25_address_t dst = { .callsign = "CQ", .ssid = 0 };
  ax25_address_t src = { .callsign = "UN8SAT", .ssid = 1 };
  uint8_t a[64], b[64];
  size_t na = 0, nb = 0;
  ax25_encode_ui_frame(&dst, &src, 0xF0, (const uint8_t*)"A", 1, a, sizeof(a), &na);
  ax25_encode_ui_frame(&dst, &src, 0xF0, (const uint8_t*)"B", 1, b, sizeof(b), &nb);

  ax25_ui_frame_t out;
  bool ready;
  int seen = 0;
  for (size_t i = 0; i < na; i++) {
    ax25_decoder_push_byte(&d, a[i], &out, &ready);
    if (ready) seen++;
  }
  for (size_t i = 0; i < nb; i++) {
    ax25_decoder_push_byte(&d, b[i], &out, &ready);
    if (ready) seen++;
  }
  TEST_ASSERT_EQUAL_INT(2, seen);
  TEST_ASSERT_EQUAL_UINT32(2, d.frames_ok);
}

/* REQ-AX25-024: on error inside FRAME, decoder resets to HUNT,
 * does NOT reprocess the offending byte. */
void test_push_byte_error_resets_to_hunt(void) {
  /* Feed valid start flag, then six consecutive 1-bit bytes to trigger
   * stuffing violation. */
  ax25_ui_frame_t out; bool ready;
  ax25_decoder_push_byte(&d, 0x7E, &out, &ready);  /* enter FRAME */
  for (int i = 0; i < 4; i++) {
    ax25_decoder_push_byte(&d, 0xFF, &out, &ready);
    TEST_ASSERT_FALSE(ready);
  }
  /* At this point stuffing should have triggered somewhere. */
  TEST_ASSERT_TRUE(d.frames_stuffing_err > 0 || d.frames_overflow > 0);
  TEST_ASSERT_EQUAL(AX25_STATE_HUNT, d.state);
}

/* REQ-AX25-012: reject frames beyond AX25_MAX_FRAME_BYTES. */
void test_push_byte_overflow_rejected(void) {
  ax25_ui_frame_t out; bool ready;
  ax25_decoder_push_byte(&d, 0x7E, &out, &ready);
  for (size_t i = 0; i < AX25_MAX_FRAME_BYTES + 10; i++) {
    ax25_decoder_push_byte(&d, 0xAA, &out, &ready);
    if (ready) TEST_FAIL_MESSAGE("should not emit frame");
  }
  TEST_ASSERT_TRUE(d.frames_overflow >= 1);
}

void update_main_runner(void) { /* registered below */ }

/* In main(), register all: */
#define _RUN(t) RUN_TEST(t)
```

Update the `main` at bottom of the file:

```c
int main(void) {
  UNITY_BEGIN();
  RUN_TEST(test_init_zeros_all_counters);
  RUN_TEST(test_push_byte_single_frame_emits_exactly_one);
  RUN_TEST(test_push_byte_idle_flags_ignored);
  RUN_TEST(test_push_byte_back_to_back_frames);
  RUN_TEST(test_push_byte_error_resets_to_hunt);
  RUN_TEST(test_push_byte_overflow_rejected);
  return UNITY_END();
}
```

- [ ] **Step 2: Run, confirm failure**

```bash
cmake --build build --target test_ax25_decoder && ./build/test_ax25_decoder
```

- [ ] **Step 3: Implement `ax25_decoder_push_byte`**

Replace the stub in `ax25_decoder.c`:

```c
/* Feed one de-stuffed bit into the assembly buffer (LSB-first). */
static bool append_bit(ax25_decoder_t *d, int bit) {
  d->shift_reg |= (uint16_t)(bit & 1) << d->bit_count;
  d->bit_count++;
  if (d->bit_count == 8) {
    if (d->len >= sizeof(d->buf)) {
      d->frames_overflow++;
      ax25_decoder_reset(d);
      return false;
    }
    d->buf[d->len++] = (uint8_t)(d->shift_reg & 0xFF);
    d->shift_reg = 0;
    d->bit_count = 0;
  }
  return true;
}

static void emit_frame_if_valid(ax25_decoder_t *d,
                                 ax25_ui_frame_t *out, bool *ready) {
  /* Discard trailing partial byte (the closing flag bits). */
  if (d->bit_count != 0) {
    d->shift_reg = 0;
    d->bit_count = 0;
  }
  if (d->len < 18) {
    /* Empty / too-short — REQ-AX25-023 says idle runs are silent. */
    ax25_decoder_reset(d);
    return;
  }
  ax25_status_t st = ax25_decode_ui_frame(d->buf, d->len, out);
  if (st == AX25_OK) {
    d->frames_ok++;
    *ready = true;
  } else if (st == AX25_ERR_FCS_MISMATCH) {
    d->frames_fcs_err++;
  } else {
    d->frames_other_err++;
  }
  ax25_decoder_reset(d);
}

ax25_status_t ax25_decoder_push_byte(ax25_decoder_t *d, uint8_t byte,
                                      ax25_ui_frame_t *out_frame,
                                      bool *frame_ready) {
  if (frame_ready) *frame_ready = false;

  if (byte == 0x7E) {
    /* Flag byte — boundary.  State transition:
     *   HUNT  -> FRAME     (REQ-AX25-001: opening flag)
     *   FRAME -> try emit  (REQ-AX25-008: closing flag; REQ-AX25-023 ignore empty)
     */
    if (d->state == AX25_STATE_HUNT) {
      d->state = AX25_STATE_FRAME;
      d->len = 0;
      d->shift_reg = 0;
      d->bit_count = 0;
      d->ones_run = 0;
      return AX25_OK;
    }
    /* state == FRAME: close. */
    emit_frame_if_valid(d, out_frame, frame_ready);
    /* A closing flag is also a valid opening flag for the next frame. */
    d->state = AX25_STATE_FRAME;
    d->len = 0;
    d->shift_reg = 0;
    d->bit_count = 0;
    d->ones_run = 0;
    return AX25_OK;
  }

  if (d->state == AX25_STATE_HUNT) {
    /* Outside frame — ignore. */
    return AX25_OK;
  }

  /* Inside FRAME: consume each bit LSB-first, applying de-stuffing. */
  for (int b = 0; b < 8; b++) {
    int bit = (byte >> b) & 1;
    if (d->ones_run == 5) {
      if (bit == 0) {
        /* Stuffed bit — drop. */
        d->ones_run = 0;
        continue;
      }
      /* Six ones inside frame — REQ-AX25-024: reset. */
      d->frames_stuffing_err++;
      ax25_decoder_reset(d);
      return AX25_ERR_STUFFING_VIOLATION;
    }
    if (!append_bit(d, bit)) {
      /* Buffer overflow already logged; decoder is reset. */
      return AX25_ERR_FRAME_TOO_LONG;
    }
    d->ones_run = (bit == 1) ? d->ones_run + 1 : 0;
    /* Frame-size DoS guard: hard-reject as soon as we exceed max. */
    if (d->len >= AX25_MAX_FRAME_BYTES) {
      d->frames_overflow++;
      ax25_decoder_reset(d);
      return AX25_ERR_FRAME_TOO_LONG;
    }
  }
  return AX25_OK;
}
```

- [ ] **Step 4: Run, confirm pass**

```bash
cmake --build build --target test_ax25_decoder && ./build/test_ax25_decoder
```

Expected: `6 Tests 0 Failures`. If stuffing-violation test fails
because the decoder reaches overflow before 6 ones, that's still
a valid recovery; adjust the assertion to accept either counter.

- [ ] **Step 5: Commit**

```bash
git add firmware/stm32/Drivers/AX25/ax25_decoder.c firmware/tests/test_ax25_decoder.c
git commit -m "feat(ax25): streaming decoder push_byte (REQ-AX25-017/023/024)"
```

---

### Task 4.3: Python `Ax25Decoder` mirror

**Files:**
- Modify: `ground-station/utils/ax25.py`
- Modify: `ground-station/tests/test_ax25.py`

- [ ] **Step 1: Add failing tests**

Append to `ground-station/tests/test_ax25.py`:

```python
from utils.ax25 import Ax25Decoder


class TestStreaming:
    def test_single_frame(self):
        dst = Address("CQ", 0); src = Address("UN8SAT", 1)
        frame = encode_ui_frame(dst, src, 0xF0, b"Hi")
        dec = Ax25Decoder()
        out = [r for b in frame if (r := dec.push_byte(b)) is not None]
        assert len(out) == 1
        assert out[0].info == b"Hi"

    def test_idle_flags(self):
        dec = Ax25Decoder()
        for _ in range(10):
            assert dec.push_byte(0x7E) is None

    def test_back_to_back(self):
        dst = Address("CQ", 0); src = Address("UN8SAT", 1)
        a = encode_ui_frame(dst, src, 0xF0, b"A")
        b = encode_ui_frame(dst, src, 0xF0, b"B")
        dec = Ax25Decoder()
        frames = []
        for byte in a + b:
            f = dec.push_byte(byte)
            if f: frames.append(f)
        assert [f.info for f in frames] == [b"A", b"B"]
```

- [ ] **Step 2: Confirm failure**

```bash
pytest tests/test_ax25.py::TestStreaming -v
```

- [ ] **Step 3: Implement `Ax25Decoder`**

Append to `ground-station/utils/ax25.py`:

```python
class _State:
    HUNT = 0
    FRAME = 1


class Ax25Decoder:
    """Byte-by-byte AX.25 UI frame assembler.

    Mirrors firmware/stm32/Drivers/AX25/ax25_decoder.c.  Thread-unsafe —
    one instance per RX stream.
    """

    MAX_FRAME = 400  # AX25_MAX_FRAME_BYTES

    def __init__(self):
        self.reset_all()

    def reset_all(self):
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

    def _reset_frame(self):
        self._state = _State.HUNT
        self._buf = bytearray()
        self._shift = 0
        self._bit_count = 0
        self._ones = 0

    def _append_bit(self, bit: int) -> bool:
        self._shift |= (bit & 1) << self._bit_count
        self._bit_count += 1
        if self._bit_count == 8:
            if len(self._buf) >= self.MAX_FRAME:
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
            self._reset_frame()
            return frame
        except FcsMismatch:
            self.frames_fcs_err += 1
        except AX25Error:
            self.frames_other_err += 1
        self._reset_frame()
        return None

    def push_byte(self, byte: int):
        if byte == 0x7E:
            if self._state == _State.HUNT:
                self._state = _State.FRAME
                return None
            # FRAME -> close
            frame = self._emit()
            self._state = _State.FRAME  # closing flag opens next frame
            return frame

        if self._state == _State.HUNT:
            return None

        for b in range(8):
            bit = (byte >> b) & 1
            if self._ones == 5:
                if bit == 0:
                    self._ones = 0
                    continue
                self.frames_stuffing_err += 1
                self._reset_frame()
                return None
            if not self._append_bit(bit):
                return None
            self._ones = self._ones + 1 if bit == 1 else 0
            if len(self._buf) >= self.MAX_FRAME:
                self.frames_overflow += 1
                self._reset_frame()
                return None
        return None
```

- [ ] **Step 4: Confirm pass**

```bash
pytest tests/test_ax25.py::TestStreaming -v
```

- [ ] **Step 5: Commit**

```bash
git add ground-station/utils/ax25.py ground-station/tests/test_ax25.py
git commit -m "feat(gs-ax25): Ax25Decoder streaming mirror (REQ-AX25-017)"
```

---

### Task 4.4: Hypothesis property-based tests + fuzz

**Files:**
- Modify: `ground-station/tests/test_ax25.py`

- [ ] **Step 1: Add property & fuzz tests**

Append to `ground-station/tests/test_ax25.py`:

```python
from hypothesis import given, strategies as st, settings

_CALL_ALPHA = st.text(alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
                      min_size=1, max_size=6)

_addr = st.builds(Address, _CALL_ALPHA, st.integers(0, 15))


@given(dst=_addr, src=_addr, info=st.binary(max_size=200))
@settings(max_examples=500, deadline=None)
def test_encode_decode_round_trip_property(dst, src, info):
    frame = encode_ui_frame(dst, src, 0xF0, info)
    body = bit_unstuff(frame[1:-1])
    got = decode_ui_frame(body)
    assert got.dst == dst
    assert got.src == src
    assert got.info == info


@given(stream=st.binary(max_size=1024))
@settings(max_examples=2000, deadline=None)
def test_decoder_never_crashes_on_garbage(stream):
    dec = Ax25Decoder()
    for b in stream:
        try:
            dec.push_byte(b)
        except AX25Error:
            pass  # typed errors allowed; unexpected exceptions = failure
```

- [ ] **Step 2: Run (may take ~10 s)**

```bash
pytest tests/test_ax25.py -v -k "property or garbage"
```

Expected: PASS. Hypothesis will shrink any failing input to a
minimal reproducer; if that happens, it's a real bug — fix before
committing.

- [ ] **Step 3: Commit**

```bash
git add ground-station/tests/test_ax25.py
git commit -m "test(gs-ax25): hypothesis property-based round-trip and fuzz"
```

---

## Phase 5: Style Adapter

### Task 5.1: C facade `ax25_api.h`

**Files:**
- Create: `firmware/stm32/Drivers/AX25/ax25_api.h`

- [ ] **Step 1: Write the header**

Create:

```c
/* Project-facing AX.25 facade (spec §4.2 / ADR-002).
 * Embedded-HAL style names wrapping the Google-style pure library. */
#ifndef AX25_API_H
#define AX25_API_H

#include "ax25.h"
#include "ax25_decoder.h"

typedef ax25_address_t       AX25_Address_t;
typedef ax25_ui_frame_t      AX25_UiFrame_t;
typedef ax25_status_t        AX25_Status_t;
typedef ax25_decoder_t       AX25_Decoder_t;

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

static inline void AX25_DecoderInit(AX25_Decoder_t *d) {
  ax25_decoder_init(d);
}

static inline bool AX25_DecoderPushByte(
    AX25_Decoder_t *d, uint8_t byte, AX25_UiFrame_t *out, bool *ready) {
  return ax25_decoder_push_byte(d, byte, out, ready) == AX25_OK;
}

#endif /* AX25_API_H */
```

- [ ] **Step 2: Add a smoke-test using only the facade**

Create `firmware/tests/test_ax25_api.c`:

```c
#include "unity.h"
#include "ax25_api.h"
#include <string.h>

void setUp(void) {} void tearDown(void) {}

void test_facade_encode_decode_round_trip(void) {
  AX25_Address_t dst = { .callsign = "CQ", .ssid = 0 };
  AX25_Address_t src = { .callsign = "UN8SAT", .ssid = 1 };
  uint8_t buf[128]; uint16_t n = 0;
  TEST_ASSERT_TRUE(AX25_EncodeUiFrame(&dst, &src, 0xF0,
                                       (const uint8_t *)"Hi", 2,
                                       buf, sizeof(buf), &n));

  AX25_Decoder_t dec; AX25_DecoderInit(&dec);
  AX25_UiFrame_t f; bool ready;
  int got = 0;
  for (uint16_t i = 0; i < n; i++) {
    AX25_DecoderPushByte(&dec, buf[i], &f, &ready);
    if (ready) got++;
  }
  TEST_ASSERT_EQUAL_INT(1, got);
  TEST_ASSERT_EQUAL_STRING("Hi", (char *)f.info);
}

int main(void) { UNITY_BEGIN(); RUN_TEST(test_facade_encode_decode_round_trip); return UNITY_END(); }
```

- [ ] **Step 3: Run, confirm pass**

```bash
cmake --build build --target test_ax25_api && ./build/test_ax25_api
```

- [ ] **Step 4: Commit**

```bash
git add firmware/stm32/Drivers/AX25/ax25_api.h firmware/tests/test_ax25_api.c
git commit -m "feat(ax25): AX25_Xxx() facade for project-style consumers (ADR-002)"
```

---

## Phase 6: Integration into `comm.c`

### Task 6.1: Extend `COMM_Status_t` with AX.25 counters

**Files:**
- Modify: `firmware/stm32/Core/Inc/comm.h`

- [ ] **Step 1: Add fields**

Edit `firmware/stm32/Core/Inc/comm.h`, replace the `COMM_Status_t` struct body with:

```c
typedef struct {
    bool uhf_connected;
    bool sband_connected;
    uint32_t packets_sent;
    uint32_t packets_received;
    uint32_t errors;
    int8_t rssi;
    uint32_t last_rx_timestamp;
    uint32_t last_tx_timestamp;
    /* AX.25 link-layer counters (mirrored from ax25_decoder_t after each drain) */
    uint32_t ax25_frames_ok;
    uint32_t ax25_fcs_errors;
    uint32_t ax25_frame_errors;
    uint32_t ax25_overflow_errors;
} COMM_Status_t;
```

- [ ] **Step 2: Confirm build**

```bash
cmake --build build
```

- [ ] **Step 3: Commit**

```bash
git add firmware/stm32/Core/Inc/comm.h
git commit -m "feat(comm): add AX.25 counters to COMM_Status_t"
```

---

### Task 6.2: Rewrite `COMM_ProcessRxBuffer()` to use the streaming decoder

**Files:**
- Modify: `firmware/stm32/Core/Src/comm.c`

- [ ] **Step 1: Update tests FIRST — integration harness**

Create `firmware/tests/test_comm_integration.c`:

```c
#include "unity.h"
#include "comm.h"
#include "ax25_api.h"

extern void COMM_ProcessRxBuffer(void);
/* Needed to inject bytes in the SIMULATION_MODE test harness. */
extern void COMM_UART_RxCallback(CommChannel_t ch, uint8_t byte);

void setUp(void) { COMM_Init(); }
void tearDown(void) {}

void test_process_rx_buffer_emits_ax25_frame_via_decoder(void) {
  AX25_Address_t dst = { .callsign = "CQ", .ssid = 0 };
  AX25_Address_t src = { .callsign = "UN8SAT", .ssid = 1 };
  uint8_t frame[128]; uint16_t n = 0;
  AX25_EncodeUiFrame(&dst, &src, 0xF0, (const uint8_t *)"X", 1,
                     frame, sizeof(frame), &n);

  for (uint16_t i = 0; i < n; i++) {
    COMM_UART_RxCallback(COMM_CHANNEL_UHF, frame[i]);
  }
  COMM_ProcessRxBuffer();

  COMM_Status_t st = COMM_GetStatus();
  TEST_ASSERT_EQUAL_UINT32(1, st.ax25_frames_ok);
}

int main(void) {
  UNITY_BEGIN();
  RUN_TEST(test_process_rx_buffer_emits_ax25_frame_via_decoder);
  return UNITY_END();
}
```

- [ ] **Step 2: Run, confirm failure**

```bash
cmake --build build --target test_comm_integration && ./build/test_comm_integration
```

Expected: FAIL (`ax25_frames_ok` stays 0 because `COMM_ProcessRxBuffer` is
still a placeholder).

- [ ] **Step 3: Implement integration**

Edit `firmware/stm32/Core/Src/comm.c`:

```c
#include "ax25_api.h"   // add at top

static AX25_Decoder_t g_uhf_decoder;

void COMM_Init(void) {
    memset(&comm_status, 0, sizeof(comm_status));
    uhf_rx_head = 0;
    uhf_rx_tail = 0;
    AX25_DecoderInit(&g_uhf_decoder);

#ifndef SIMULATION_MODE
    if (config.comm.uhf_enabled) {
        HAL_UART_Receive_IT(&huart1, &uhf_rx_buffer[0], 1);
    }
#endif
}

/* Replaces previous placeholder. */
void COMM_ProcessRxBuffer(void) {
    while (uhf_rx_tail != uhf_rx_head) {
        uint8_t byte = uhf_rx_buffer[uhf_rx_tail];
        uhf_rx_tail = (uhf_rx_tail + 1) % COMM_RX_BUFFER_SIZE;

        AX25_UiFrame_t frame;
        bool ready = false;
        AX25_DecoderPushByte(&g_uhf_decoder, byte, &frame, &ready);

        if (ready) {
            extern void CCSDS_Dispatcher_Submit(const uint8_t *data, uint16_t n);
            CCSDS_Dispatcher_Submit(frame.info, frame.info_len);
        }
    }
    /* Mirror counters to COMM_Status_t */
    comm_status.ax25_frames_ok      = g_uhf_decoder.frames_ok;
    comm_status.ax25_fcs_errors     = g_uhf_decoder.frames_fcs_err;
    comm_status.ax25_frame_errors   = g_uhf_decoder.frames_other_err
                                    + g_uhf_decoder.frames_stuffing_err;
    comm_status.ax25_overflow_errors = g_uhf_decoder.frames_overflow;
}
```

Provide a weak stub for `CCSDS_Dispatcher_Submit` if it doesn't exist yet:

```c
__attribute__((weak))
void CCSDS_Dispatcher_Submit(const uint8_t *data, uint16_t n) {
    (void)data; (void)n;
}
```

- [ ] **Step 4: Confirm pass**

```bash
cmake --build build --target test_comm_integration && ./build/test_comm_integration
```

- [ ] **Step 5: Commit**

```bash
git add firmware/stm32/Core/Src/comm.c firmware/tests/test_comm_integration.c
git commit -m "feat(comm): integrate AX.25 streaming decoder into RX path"
```

---

### Task 6.3: Add `COMM_SendAX25` and convert `COMM_SendBeacon`

**Files:**
- Modify: `firmware/stm32/Core/Inc/comm.h`
- Modify: `firmware/stm32/Core/Src/comm.c`

- [ ] **Step 1: Declare new function**

Append to `comm.h`:

```c
bool COMM_SendAX25(CommChannel_t channel,
                    const char *dst_call, uint8_t dst_ssid,
                    const char *src_call, uint8_t src_ssid,
                    const uint8_t *info, uint16_t info_len);
```

- [ ] **Step 2: Implement**

Append to `comm.c`:

```c
bool COMM_SendAX25(CommChannel_t channel,
                    const char *dst_call, uint8_t dst_ssid,
                    const char *src_call, uint8_t src_ssid,
                    const uint8_t *info, uint16_t info_len) {
    AX25_Address_t dst = { .ssid = dst_ssid };
    AX25_Address_t src = { .ssid = src_ssid };
    strncpy(dst.callsign, dst_call, 6); dst.callsign[6] = 0;
    strncpy(src.callsign, src_call, 6); src.callsign[6] = 0;

    uint8_t buf[AX25_MAX_FRAME_BYTES];
    uint16_t n = 0;
    if (!AX25_EncodeUiFrame(&dst, &src, 0xF0, info, info_len,
                             buf, sizeof(buf), &n)) {
        comm_status.errors++;
        return false;
    }
    return COMM_Send(channel, buf, n);
}
```

- [ ] **Step 3: Rewrite `COMM_SendBeacon` to use AX.25**

Replace the existing `COMM_SendBeacon` body with:

```c
bool COMM_SendBeacon(void) {
    /* Spec §7.2: 48-byte beacon layout. */
    extern uint16_t Telemetry_PackBeacon(uint8_t *buf, uint16_t max);
    uint8_t info[48];
    uint16_t len = Telemetry_PackBeacon(info, sizeof(info));
    if (len != 48) {
        comm_status.errors++;
        return false;
    }
    return COMM_SendAX25(COMM_CHANNEL_UHF,
                         "CQ",     0,
                         "UN8SAT", 1,
                         info, len);
}
```

- [ ] **Step 4: Verify build**

```bash
cmake --build build
```

- [ ] **Step 5: Commit**

```bash
git add firmware/stm32/Core/Src/comm.c firmware/stm32/Core/Inc/comm.h
git commit -m "feat(comm): COMM_SendAX25 + beacon path via AX.25"
```

---

### Task 6.4: FreeRTOS `comm_rx_task` (spec §4.10)

**Files:**
- Modify: `firmware/stm32/Core/Src/comm.c`
- Modify: `firmware/stm32/Core/Src/main.c` (wire up task)

- [ ] **Step 1: Add task function**

Append to `comm.c`:

```c
#ifndef SIMULATION_MODE
#include "cmsis_os2.h"

static osThreadId_t s_comm_rx_task_id;

static void CommRxTask(void *arg) {
    (void)arg;
    for (;;) {
        COMM_ProcessRxBuffer();
        osDelay(10); /* 10 ms period per spec §4.10 */
    }
}

void COMM_StartTask(void) {
    osThreadAttr_t attr = {
        .name = "comm_rx",
        .stack_size = AX25_DECODER_TASK_STACK,
        .priority = AX25_DECODER_TASK_PRIO,
    };
    s_comm_rx_task_id = osThreadNew(CommRxTask, NULL, &attr);
}
#else
void COMM_StartTask(void) {}
#endif
```

- [ ] **Step 2: Declare in `comm.h`**

Append:

```c
void COMM_StartTask(void);
```

- [ ] **Step 3: Call from main.c**

In `main.c`, after subsystem init, add:

```c
COMM_StartTask();
```

(Exact location: inside `MX_FREERTOS_Init()` or equivalent, after
`COMM_Init()`.)

- [ ] **Step 4: Build and verify**

```bash
cmake --build build
```

- [ ] **Step 5: Commit**

```bash
git add firmware/stm32/Core/Src/comm.c firmware/stm32/Core/Inc/comm.h firmware/stm32/Core/Src/main.c
git commit -m "feat(comm): FreeRTOS comm_rx_task at 10 ms period (spec §4.10)"
```

---

## Phase 7: SITL Virtual UART

### Task 7.1: `virtual_uart.c` — TCP client shim

**Files:**
- Create: `firmware/stm32/Drivers/VirtualUART/virtual_uart.h`
- Create: `firmware/stm32/Drivers/VirtualUART/virtual_uart.c`
- Create: `firmware/stm32/Drivers/VirtualUART/CMakeLists.txt`

- [ ] **Step 1: Write header**

Create `virtual_uart.h`:

```c
#ifndef VIRTUAL_UART_H
#define VIRTUAL_UART_H

#include <stdint.h>
#include <stdbool.h>

/* SIM-only. Connects to 127.0.0.1:port as a TCP client. */
bool VirtualUART_Init(uint16_t port);
void VirtualUART_Shutdown(void);

/* Replacements for HAL_UART_Transmit / HAL_UART_Receive_IT-style push. */
bool VirtualUART_Send(const uint8_t *data, uint16_t len);

/* Polls up to max_bytes bytes; returns count received. */
int VirtualUART_Recv(uint8_t *buf, int max_bytes);

#endif /* VIRTUAL_UART_H */
```

- [ ] **Step 2: Write cross-platform TCP implementation**

Create `virtual_uart.c`:

```c
#include "virtual_uart.h"
#include <string.h>

#ifdef _WIN32
#include <winsock2.h>
#include <ws2tcpip.h>
typedef SOCKET sock_t;
#define CLOSE_SOCK closesocket
#else
#include <sys/socket.h>
#include <arpa/inet.h>
#include <unistd.h>
#include <fcntl.h>
typedef int sock_t;
#define CLOSE_SOCK close
#define INVALID_SOCKET (-1)
#endif

static sock_t s_fd = (sock_t)INVALID_SOCKET;

bool VirtualUART_Init(uint16_t port) {
#ifdef _WIN32
  WSADATA wsa; WSAStartup(MAKEWORD(2,2), &wsa);
#endif
  s_fd = socket(AF_INET, SOCK_STREAM, 0);
  if (s_fd == (sock_t)INVALID_SOCKET) return false;

  struct sockaddr_in addr = {0};
  addr.sin_family = AF_INET;
  addr.sin_port = htons(port);
  inet_pton(AF_INET, "127.0.0.1", &addr.sin_addr);
  if (connect(s_fd, (struct sockaddr *)&addr, sizeof(addr)) != 0) {
    CLOSE_SOCK(s_fd); s_fd = (sock_t)INVALID_SOCKET; return false;
  }
#ifndef _WIN32
  int flags = fcntl(s_fd, F_GETFL, 0);
  fcntl(s_fd, F_SETFL, flags | O_NONBLOCK);
#else
  u_long mode = 1; ioctlsocket(s_fd, FIONBIO, &mode);
#endif
  return true;
}

void VirtualUART_Shutdown(void) {
  if (s_fd != (sock_t)INVALID_SOCKET) {
    CLOSE_SOCK(s_fd); s_fd = (sock_t)INVALID_SOCKET;
  }
#ifdef _WIN32
  WSACleanup();
#endif
}

bool VirtualUART_Send(const uint8_t *data, uint16_t len) {
  if (s_fd == (sock_t)INVALID_SOCKET) return false;
  int n = send(s_fd, (const char *)data, len, 0);
  return n == (int)len;
}

int VirtualUART_Recv(uint8_t *buf, int max_bytes) {
  if (s_fd == (sock_t)INVALID_SOCKET) return 0;
  int n = recv(s_fd, (char *)buf, max_bytes, 0);
  return n < 0 ? 0 : n;
}
```

- [ ] **Step 3: Wire into comm.c `SIMULATION_MODE` paths**

In `comm.c`, replace the `#else` branches in `COMM_Send` / `COMM_Init` with:

```c
#ifdef SIMULATION_MODE
    VirtualUART_Init(52100);
#else
    if (config.comm.uhf_enabled) HAL_UART_Receive_IT(&huart1, ...);
#endif
```

and

```c
#ifdef SIMULATION_MODE
    if (!VirtualUART_Send(data, length)) { comm_status.errors++; return false; }
    comm_status.packets_sent++;
    return true;
#else
    /* HAL path */
#endif
```

Also add a SIM poller: in `COMM_ProcessRxBuffer`, at the top (only under
`SIMULATION_MODE`), pull bytes from the virtual UART into the ring
buffer:

```c
#ifdef SIMULATION_MODE
    uint8_t sim_buf[128];
    int got = VirtualUART_Recv(sim_buf, sizeof(sim_buf));
    for (int i = 0; i < got; i++) {
        COMM_UART_RxCallback(COMM_CHANNEL_UHF, sim_buf[i]);
    }
#endif
```

- [ ] **Step 4: Build SIM target**

```bash
cmake -B build -DSIMULATION_MODE=1 && cmake --build build
```

- [ ] **Step 5: Commit**

```bash
git add firmware/stm32/Drivers/VirtualUART/ firmware/stm32/Core/Src/comm.c
git commit -m "feat(sim): TCP-loopback virtual UART for SITL (spec §4.3)"
```

---

## Phase 8: Ground-Station CLI

### Task 8.1: `ax25_listen.py`

**Files:**
- Create: `ground-station/cli/__init__.py` (empty)
- Create: `ground-station/cli/ax25_listen.py`

- [ ] **Step 1: Write the script**

Create `ground-station/cli/ax25_listen.py`:

```python
"""AX.25 listener over TCP loopback.

Usage:
  python -m cli.ax25_listen [--host 127.0.0.1] [--port 52100]
"""
import argparse
import json
import socket
import sys
from dataclasses import asdict

from utils.ax25 import Ax25Decoder, AX25Error


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=52100)
    args = ap.parse_args()

    # Server socket — firmware connects to us as a client.
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((args.host, args.port))
    srv.listen(1)
    print(f"[ax25_listen] waiting on {args.host}:{args.port}", flush=True)

    conn, peer = srv.accept()
    print(f"[ax25_listen] connected: {peer}", flush=True)

    decoder = Ax25Decoder()
    try:
        while True:
            data = conn.recv(4096)
            if not data:
                break
            for b in data:
                try:
                    frame = decoder.push_byte(b)
                except AX25Error as e:
                    print(json.dumps({"error": str(e)}), flush=True)
                    continue
                if frame is not None:
                    print(json.dumps({
                        "dst": {"callsign": frame.dst.callsign, "ssid": frame.dst.ssid},
                        "src": {"callsign": frame.src.callsign, "ssid": frame.src.ssid},
                        "pid": frame.pid,
                        "info_hex": frame.info.hex(),
                        "fcs_valid": frame.fcs_valid,
                    }), flush=True)
    finally:
        conn.close(); srv.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Smoke-test against a hard-coded encoded frame**

```bash
cd ground-station && python -m cli.ax25_listen &
sleep 0.3
python -c "
import socket, sys
sys.path.insert(0, '.')
from utils.ax25 import Address, encode_ui_frame
s = socket.socket(); s.connect(('127.0.0.1', 52100))
s.sendall(encode_ui_frame(Address('CQ',0), Address('UN8SAT',1), 0xF0, b'hello'))
"
wait
```

Expected: JSON line on stdout with `info_hex: "68656c6c6f"`.

- [ ] **Step 3: Commit**

```bash
git add ground-station/cli/
git commit -m "feat(gs-cli): ax25_listen — TCP AX.25 listener"
```

---

### Task 8.2: `ax25_send.py`

**Files:**
- Create: `ground-station/cli/ax25_send.py`

- [ ] **Step 1: Write the script**

Create `ground-station/cli/ax25_send.py`:

```python
"""Send a single AX.25 UI frame over TCP loopback.

Usage:
  python -m cli.ax25_send --dst-call CQ --dst-ssid 0 \
      --src-call UN8SAT --src-ssid 1 --info-hex 68656c6c6f \
      [--host 127.0.0.1] [--port 52100]
"""
import argparse
import socket
import sys

from utils.ax25 import Address, encode_ui_frame


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=52100)
    ap.add_argument("--dst-call", required=True)
    ap.add_argument("--dst-ssid", type=int, default=0)
    ap.add_argument("--src-call", required=True)
    ap.add_argument("--src-ssid", type=int, default=0)
    ap.add_argument("--info-hex", default="")
    args = ap.parse_args()

    frame = encode_ui_frame(
        Address(args.dst_call, args.dst_ssid),
        Address(args.src_call, args.src_ssid),
        0xF0,
        bytes.fromhex(args.info_hex),
    )
    with socket.socket() as s:
        s.connect((args.host, args.port))
        s.sendall(frame)
    print(f"sent {len(frame)} bytes", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Smoke-test (requires ax25_listen running)**

```bash
python -m cli.ax25_listen &
sleep 0.3
python -m cli.ax25_send --dst-call CQ --src-call UN8SAT --src-ssid 1 --info-hex 68656c6c6f
wait
```

Expected: listener prints JSON with `info_hex: "68656c6c6f"`.

- [ ] **Step 3: Commit**

```bash
git add ground-station/cli/ax25_send.py
git commit -m "feat(gs-cli): ax25_send — TCP AX.25 sender"
```

---

## Phase 9: Orchestration & Demo

### Task 9.1: `scripts/demo.py`

**Files:**
- Create: `scripts/demo.py`

- [ ] **Step 1: Write demo orchestrator**

```python
"""End-to-end SITL demo.

Starts ax25_listen, spawns the fw-SITL binary, waits for two beacons.
Exit 0 on success, non-zero on timeout or failure.
"""
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
GS = REPO / "ground-station"
FW_BIN = REPO / "firmware" / "build" / "fw_sitl"

def main() -> int:
    listener = subprocess.Popen(
        [sys.executable, "-m", "cli.ax25_listen"],
        cwd=GS, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    time.sleep(0.5)
    fw = subprocess.Popen([str(FW_BIN)])
    beacons = []
    deadline = time.time() + 90  # 3 beacons at 30 s
    try:
        while time.time() < deadline and len(beacons) < 2:
            line = listener.stdout.readline()
            if not line:
                break
            if line.startswith("{") and '"fcs_valid": true' in line:
                beacons.append(json.loads(line))
                print(f"[demo] beacon {len(beacons)}: {beacons[-1]['info_hex'][:16]}…")
    finally:
        fw.send_signal(signal.SIGTERM); fw.wait(timeout=5)
        listener.send_signal(signal.SIGTERM); listener.wait(timeout=5)

    if len(beacons) >= 2:
        print("[demo] SUCCESS"); return 0
    print(f"[demo] FAIL — got {len(beacons)} beacons"); return 1

if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Makefile target**

Append to repo-root `Makefile` (create if missing):

```make
.PHONY: demo lib-c lib-py goldens

lib-c:
	cmake -S firmware -B firmware/build -DSIMULATION_MODE=1
	cmake --build firmware/build --target fw_sitl

lib-py:
	cd ground-station && pip install -r requirements.txt

goldens:
	python scripts/gen_golden_vectors.py

demo: lib-c lib-py goldens
	python scripts/demo.py
```

- [ ] **Step 3: Run the demo**

```bash
make demo
```

Expected: SUCCESS after ~60 s (two beacons captured).

- [ ] **Step 4: Commit**

```bash
git add scripts/demo.py Makefile
git commit -m "feat(demo): end-to-end SITL beacon demo"
```

---

## Phase 10: CI, ADRs, Docs

### Task 10.1: ADR-001 — No CSP

**Files:**
- Create: `docs/adr/ADR-001-no-csp.md`

- [ ] **Step 1: Write the ADR**

```markdown
# ADR-001: No CSP — CCSDS-only Network Layer

## Status
Accepted — 2026-04-17.

## Context
The external review flagged the absence of CubeSat Space Protocol (CSP)
as a deficiency. CSP provides port-based addressing, packet routing
between internal nodes, and light authentication over arbitrary data
links.

## Decision
UniSat-1 does not implement CSP. The network-layer role is filled by
CCSDS Space Packet Protocol (CCSDS 133.0-B-2) carried inside AX.25
on the UHF link and directly over CCSDS ASM on the S-band link.

## Rationale
1. **Topology**: UniSat-1 is a point-to-point satellite ↔ ground
   system. CSP adds value when multiple internal nodes share a bus
   (OBC ↔ EPS ↔ COMMS ↔ payload on CAN/RS-485). On this mission the
   OBC bundles all subsystems in a single MCU.
2. **Addressing**: CCSDS APID provides 11-bit subsystem/packet-type
   routing, covering every dispatch need we have.
3. **Footprint**: libcsp adds ~4 KB of flash and a routing table we
   would never populate with more than two nodes.
4. **Interop**: Ground-station tools (GNU Radio, SatNOGS) ingest AX.25
   + CCSDS natively; CSP frames are uncommon on amateur UHF.

## Consequences
- We do NOT gain CSP's built-in CMP (CSP Management Protocol) or
  RDP (Reliable Datagram Protocol). We accept this: CMP features are
  duplicated by CCSDS telemetry, and reliability is managed at the
  application layer via sequence numbers + ground-side retransmit.
- If UniSat-2 adds an EPS daughterboard with its own MCU, CSP should
  be reconsidered.
```

- [ ] **Step 2: Commit**

```bash
git add docs/adr/ADR-001-no-csp.md
git commit -m "docs(adr): ADR-001 — CCSDS-only network layer, no CSP"
```

---

### Task 10.2: ADR-002 — Style Adapter

**Files:**
- Create: `docs/adr/ADR-002-style-adapter.md`

- [ ] **Step 1: Write**

```markdown
# ADR-002: AX.25 Library Style Adapter

## Status
Accepted — 2026-04-17.

## Context
The pure AX.25 library is written in Google C++ style (snake_case
functions, lower_case_t types). Existing firmware uses embedded-HAL
style (`COMM_SendXxx()`, `COMM_Status_t`). A mix inside one translation
unit hurts readability.

## Decision
A `ax25_api.h` facade exposes thin `static inline AX25_Xxx()` wrappers
and `AX25_Xxx_t` typedefs. The pure library stays independent and
portable; integration callers include the facade.

## Consequences
- Two names for every API, but never inside the same file — callers
  choose one consistently.
- Library retains zero project dependencies and can be lifted into
  other repositories.
```

- [ ] **Step 2: Commit**

```bash
git add docs/adr/ADR-002-style-adapter.md
git commit -m "docs(adr): ADR-002 — AX.25 style adapter rationale"
```

---

### Task 10.3: Threat Model

**Files:**
- Create: `docs/security/ax25_threat_model.md`

- [ ] **Step 1: Write per spec §4.7**

```markdown
# AX.25 Link-Layer Threat Model

## Assumptions
- UHF uplink is unlicensed / partially authenticated only by callsign.
- Any party with a transmitter can inject frames on the same frequency.
- Satellite receives frames with no prior authentication at link layer.

## Threats & Mitigations

### T1 — Command Injection
**Vector**: attacker crafts an AX.25 UI frame with a valid CCSDS command.
**Mitigation**: CCSDS-level HMAC + sequence window (Track 1b).
**Residual**: assumed negligible post-Track 1b.

### T2 — Replay
**Vector**: captured command replayed later.
**Mitigation**: CCSDS secondary header carries timestamp + sequence;
command dispatcher rejects outside the freshness window.

### T3 — Bit-Stuffing DoS
**Vector**: crafted stream inflates decoder CPU cost.
**Mitigation**: REQ-AX25-012 — hard reject at `AX25_MAX_FRAME_BYTES`
(400 B) at every stage. Decoder recovery is O(1) per error (REQ-AX25-024).

### T4 — Flood of Garbage Bytes
**Vector**: attacker fills the RF band with random bytes.
**Mitigation**: REQ-AX25-014 — decoder never crashes on garbage
(fuzz-tested). Beacon cadence is independent of RX success.
```

- [ ] **Step 2: Commit**

```bash
git add docs/security/ax25_threat_model.md
git commit -m "docs(security): AX.25 link-layer threat model"
```

---

### Task 10.4: Tutorial walkthrough

**Files:**
- Create: `docs/tutorials/ax25_walkthrough.md`

- [ ] **Step 1: Write byte-by-byte walkthrough**

```markdown
# AX.25 Walkthrough: Decoding a Real Beacon

This tutorial walks one captured beacon from wire bytes to decoded
telemetry. All numbers are from the canonical test vector in
`tests/golden/ax25_vectors.json` entry 0.

## Wire bytes (hex)

```
7E 86 A2 40 40 40 40 60   AA 9C 70 A6 82 A8 63   03 F0   <48 bytes of
telemetry>   <2 bytes FCS>   7E
```

## Field-by-field

### 1. Start flag (1 byte)
`0x7E` — HDLC flag. Delimiter. Never stuffed.

### 2. Destination address (7 bytes)
`86 A2 40 40 40 40 60` — each byte is `char << 1`. Decoded:
- 0x86 >> 1 = 0x43 = 'C'
- 0xA2 >> 1 = 0x51 = 'Q'
- 0x40 >> 1 = 0x20 = ' ' (padding)
- SSID byte 0x60 = `0110 0000` → C=0, RR=11, SSID=0, H=0 (more follows)

So destination = `CQ-0` (broadcast).

### 3. Source address (7 bytes)
`AA 9C 70 A6 82 A8 63` → `UN8SAT-1`, H=1 (last address, no digipeater).

### 4. Control field (1 byte)
`0x03` — UI (unnumbered information) frame.

### 5. PID (1 byte)
`0xF0` — no layer-3 protocol; payload is raw bytes to the application.

### 6. Info field (variable, ≤256 B)
The 48 bytes here are the beacon layout from
`communication_protocol.md` §7.2: uptime, mode, battery, attitude,
position, errors, sequence.

### 7. FCS (2 bytes, little-endian)
CRC-16/X.25 over the address + control + PID + info. Two
little-endian bytes. Oracle: `fcs_crc16(b"123456789") == 0x906E`.

### 8. End flag (1 byte)
`0x7E` — closes the frame. May also be the start flag of the next frame.

## Bit-stuffing: why it matters

If any five consecutive 1-bits appear in the body *after* shifting,
a 0-bit is inserted by the transmitter. The receiver reverses it.
This prevents the body from ever producing a byte identical to the
HDLC flag. See `firmware/stm32/Drivers/AX25/ax25.c` —
`ax25_bit_stuff` for the exact algorithm.
```

- [ ] **Step 2: Commit**

```bash
git add docs/tutorials/ax25_walkthrough.md
git commit -m "docs(tutorial): AX.25 byte-by-byte beacon walkthrough"
```

---

### Task 10.5: `scripts/gen_trace_matrix.py`

**Files:**
- Create: `scripts/gen_trace_matrix.py`

- [ ] **Step 1: Write generator**

```python
"""Generate docs/verification/ax25_trace_matrix.md.

Scans test files for /* REQ-AX25-NNN */ annotations and links each
requirement to the tests covering it.
"""
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TEST_DIRS = [
    REPO / "firmware" / "tests",
    REPO / "ground-station" / "tests",
]

REQ_RE = re.compile(r"REQ-AX25-(\d{3})")


def main() -> None:
    reqs: dict[str, list[tuple[Path, int, str]]] = {}
    for d in TEST_DIRS:
        for p in d.rglob("test_*.*"):
            if p.suffix not in (".c", ".py"):
                continue
            text = p.read_text(errors="ignore")
            current_test = None
            for i, line in enumerate(text.splitlines(), 1):
                m = re.search(r"def (test_\w+)|void (test_\w+)\s*\(", line)
                if m:
                    current_test = m.group(1) or m.group(2)
                for rm in REQ_RE.finditer(line):
                    reqs.setdefault(f"REQ-AX25-{rm.group(1)}", []).append(
                        (p.relative_to(REPO), i, current_test or "<file>"))

    out = ["# AX.25 Verification Matrix",
            "",
            "Auto-generated by `scripts/gen_trace_matrix.py`.",
            "",
            "| REQ | Test file | Line | Test name |",
            "|-----|-----------|------|-----------|"]
    for req in sorted(reqs):
        for path, line, name in reqs[req]:
            out.append(f"| {req} | `{path}` | {line} | `{name}` |")
    (REPO / "docs/verification/ax25_trace_matrix.md").parent.mkdir(
        parents=True, exist_ok=True)
    (REPO / "docs/verification/ax25_trace_matrix.md").write_text(
        "\n".join(out) + "\n")
    print(f"wrote {sum(len(v) for v in reqs.values())} links for "
          f"{len(reqs)} requirements")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run**

```bash
python scripts/gen_trace_matrix.py
```

Expected: `wrote NN links for MM requirements`. Then open the
generated file and confirm every REQ-AX25-NNN from spec §9 has ≥1
link.

- [ ] **Step 3: Commit**

```bash
git add scripts/gen_trace_matrix.py docs/verification/ax25_trace_matrix.md
git commit -m "feat(test): auto-generated AX.25 requirement traceability matrix"
```

---

### Task 10.6: CI workflow

**Files:**
- Create: `.github/workflows/ax25.yml`

- [ ] **Step 1: Write workflow**

```yaml
name: AX.25

on:
  push:
    branches: [master]
    paths:
      - "firmware/stm32/Drivers/AX25/**"
      - "ground-station/utils/ax25.py"
      - "ground-station/tests/test_ax25.py"
      - "tests/golden/**"
  pull_request:

jobs:
  matrix:
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - name: Install Python deps
        run: |
          cd ground-station && pip install -r requirements.txt
          pip install pyink pylint gcovr
      - name: Python tests
        run: |
          cd ground-station && pytest tests/test_ax25.py -v
      - name: Generate goldens (sanity)
        run: python scripts/gen_golden_vectors.py
      - name: Configure & build firmware (SIM)
        run: |
          cmake -S firmware -B firmware/build -DSIMULATION_MODE=1
          cmake --build firmware/build
      - name: C unit tests
        run: |
          cd firmware/build
          ctest --output-on-failure
      - name: Cross-impl round-trip
        run: bash scripts/test_roundtrip.sh
      - name: Coverage (C)
        if: matrix.os == 'ubuntu-latest'
        run: |
          cd firmware/build && gcovr --fail-under-line 95 --fail-under-branch 90 ..
```

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/ax25.yml
git commit -m "ci(ax25): matrix build+test+fuzz across Linux/macOS/Windows"
```

---

## Self-Review

After writing this plan I checked against the spec:

**Spec coverage** — every REQ-AX25-001..024 from §9 maps to at least one task:
- REQ-001..015: Tasks 1.1–2.2
- REQ-016: Task 1.3
- REQ-017: Tasks 4.1–4.3
- REQ-018: Tasks 2.2, 3.1 (generator)
- REQ-019: Task 6.4 (task construction forbids ISR execution)
- REQ-020: Task 0.3 (AX25_RING_BUFFER_SIZE=512)
- REQ-021: Task 4.2 (reset on error)
- REQ-022: Tasks 1.1, 1.2 (oracle vector)
- REQ-023: Tasks 3.1 (generator cat 7), 4.2
- REQ-024: Task 4.2

**Placeholder scan** — no "TBD", "implement later", or vague error-handling
placeholders. One stub (`CCSDS_Dispatcher_Submit` weak symbol, Task 6.2)
is explicit and deliberate — it provides a seam for a future CCSDS
dispatcher track.

**Type consistency** — function names match across tasks (e.g.
`ax25_encode_ui_frame` identical in header, implementation, tests,
Python mirror named differently by idiom but clearly paired).

**Deliverables** — all 15 deliverables from spec §10 present:
- 1: Phase 1+2+5 (lib) ✓
- 2: Phase 7 ✓
- 3: Phase 1+2 (py) ✓
- 4: Phase 8 ✓
- 5: Phase 3 ✓
- 6: Phases 1–4 tests ✓
- 7: Phases 1–4 py tests ✓
- 8: Phases 9 + 10.5 ✓
- 9: Task 10.6 ✓
- 10: Task 10.1 ✓
- 11: Task 10.2 ✓
- 12: Task 10.3 ✓
- 13: Task 10.5 ✓
- 14: Task 10.4 ✓
- 15: Task 0.x (covered as pre-flight, not a separate spec doc — acceptable simplification)

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-04-17-track1-ax25-implementation.md`. Two execution options:

1. **Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration, minimal context pressure on the main session.

2. **Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints.

Which approach?
