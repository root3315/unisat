# AX.25 Link-Layer Threat Model

**Track:** 1 (AX.25 Link Layer)
**Updated:** 2026-04-17 — T2 replay protection closed (Phase 2).

## Assumptions

- The UHF uplink is a shared amateur-radio band. Anyone with a
  transmitter on 437 MHz can send bytes the satellite will receive.
- The satellite has no physical-layer authentication — AX.25 callsigns
  are clear-text.
- The decoder runs in a dedicated FreeRTOS task, not in interrupt
  context (spec §4.10, REQ-AX25-019).

## Threats & Mitigations

### T1 — Command Injection

**Vector:** an attacker transmits a crafted AX.25 UI frame carrying a
syntactically valid CCSDS command packet.

**Mitigation — primitives available (Track 1b partial):**

- HMAC-SHA256 library at `firmware/stm32/Drivers/Crypto/hmac_sha256.c`
  (+ Python mirror at `ground-station/utils/hmac_auth.py`). RFC 4231
  test vectors asserted on both sides so a ground-computed tag equals
  the satellite-computed tag bit-for-bit.
- Constant-time verification (`hmac_sha256_verify`) to defeat
  timing side-channels.

**Mitigation — wired (Track 1b complete + Phase 2 replay):**

`firmware/stm32/Core/Src/command_dispatcher.c` provides the strong
`CCSDS_Dispatcher_Submit` symbol that overrides the weak no-op in
`comm.c`. Every frame emitted by the AX.25 streaming decoder is now:

1. Length check (≥ 4 counter + 1 body + 32 HMAC = 37 B).
2. HMAC-SHA256 recomputed over `counter || body` with the pre-shared key.
3. Constant-time compared (`hmac_sha256_verify`).
4. Counter fed through the sliding-window replay filter (see T2).
5. On all-pass → body forwarded to the registered command handler;
   on any reject → dropped silently, the corresponding reject counter
   bumped for downlink telemetry.

Unit tests (`firmware/tests/test_command_dispatcher.c`, 11/11 green):

- Valid counter + tag → handler fired, `accepted` +1.
- Tampered tag → handler NOT fired, `rejected_bad_tag` +1.
- Frame < 37 B → `rejected_too_short` +1.
- Key not installed → every frame rejected (fail-closed).
- Full T2 coverage — see §T2 below.

**Residual risk:** the pre-shared key is currently held in `g_key[]`
RAM installed at boot. Persistent key storage in a dedicated flash
sector with CRC-protected rotation is the remaining Phase 2 item
(tracked in `docs/project/GAPS_AND_ROADMAP.md` as S-SEC-KEYSTORE).

### T2 — Replay

**Vector:** capture a legitimate command off-air and retransmit it later.

**Mitigation (wired, Phase 2):** every authenticated frame carries a
32-bit monotonic counter (big-endian, prepended to the authenticated
span so HMAC covers `counter || body`). The dispatcher maintains:

- `g_high_counter`   — highest counter ever accepted (init 0).
- `g_window`         — 64-bit bitmap; bit *i* = "counter
                        `g_high_counter − i` already accepted".
- `g_window_valid`   — cleared on every rekey or explicit reset.

Acceptance rules (see `replay_window_check_and_update`):

| Condition                                     | Result                     |
|-----------------------------------------------|----------------------------|
| `counter == 0`                                | reject (reserved sentinel) |
| First frame for this key epoch                | accept, init window        |
| `counter > g_high_counter`                    | accept, shift window up    |
| `counter <= g_high_counter − 64`              | reject (outside window)    |
| `counter` already has its bit set in window   | reject (duplicate)         |
| `counter` inside window, bit unset            | accept, set its bit        |

Rekeying (`CommandDispatcher_SetKey`) and `ResetReplayWindow()` both
clear the window so a ground-operator key rotation implicitly starts
a fresh counter epoch. `CommandDispatcher_GetStats()` exports
`rejected_replay` and `highest_counter` for downlink monitoring.

Unit-test coverage (`firmware/tests/test_command_dispatcher.c`):

- Duplicate counter → replay rejected.
- Monotonic 1..100 → 100 accepted, 0 replays.
- Out-of-order inside window → accepted once, duplicate rejected.
- Counter older than window (100 vs highest=200) → rejected.
- Boundary: counter=137 (diff 63) accepted, counter=136 (diff 64) rejected.
- Counter = 0 → rejected.
- Rekey → 50 accepted, rekey, 50 accepted again (fresh epoch).
- `ResetReplayWindow()` → same semantics as rekey for counter state.

**Residual risk:** an attacker who replays a frame *within the same
key epoch* and *before the legitimate operator transmits it once*
still gets one acceptance. This is inherent to any freshness scheme
that relies on counters rather than synchronised clocks. Mitigated at
the operational level by ground-side counter tracking (every ground
TX increments a local counter and records the last-acked value; a
gap triggers an anomaly alert). A true clock-based freshness gate
requires a reliable RTC — open for Phase 3 FDIR work.

### T3 — Bit-Stuffing DoS

**Vector:** transmit bytes crafted to cause worst-case stuffing expansion,
inflating decoder CPU cost per byte received.

**Mitigation:** REQ-AX25-012 — the decoder hard-rejects frames > 400 B
(`AX25_MAX_FRAME_BYTES`) at every stage (flag scanner, unstuffer,
parser). Recovery is O(1) per error (REQ-AX25-024: reset to HUNT,
offending byte not reprocessed).

The per-byte decode cost is bounded by constant work (shift-register
update + 5-ones check). Throughput budget (§4.11) shows 0.6 % CPU at
9600 bps even at maximum frame rate.

### T4 — Flood of Garbage Bytes

**Vector:** jam the RF band with random bytes to exhaust the decoder.

**Mitigation:** REQ-AX25-014 — the decoder never crashes or leaks state
on arbitrary garbage. This is fuzz-tested with 10 000 random iterations
(C, deterministic LCG) + 500 hypothesis cases (Python). Beacon TX runs
on its own cadence independent of RX activity.

### T5 — Protocol Confusion / Spec Drift

**Vector:** a subtle mismatch between the C and Python implementations
allows an attacker to craft a frame accepted by one but rejected by the
other, bypassing ground-side validation.

**Mitigation:** 28 shared golden vectors (REQ-AX25-015); both
implementations assert bit-identical output against the same fixtures.
CI runs the check on every commit touching the library.

## Out of scope

- Physical-layer spoofing (jamming, replay attacks on the radio PHY) —
  handled by frequency agility (future) or mission-level fallback
  (manual OBC recovery command sequence).
- Side-channel attacks on the flight MCU — no sensitive key material in
  flash until Track 1b.
- Supply-chain attacks on the build pipeline — mitigated by pinning CI
  image digests (Track 4 scope).
