# AX.25 Link-Layer Threat Model

**Track:** 1 (AX.25 Link Layer)
**Updated:** 2026-04-17

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

**Mitigation:** CCSDS-level HMAC (256-bit pre-shared key) over the full
command packet plus a replay-protection sequence window. Track 1b owns
this — AX.25 alone does not defend against command injection.

**Residual risk:** until Track 1b lands, command injection is possible.
For testing we run with commands disabled; beacon TX is read-only.

### T2 — Replay

**Vector:** capture a legitimate command off-air and retransmit it later.

**Mitigation:** CCSDS secondary header carries timestamp + 14-bit sequence
number. The dispatcher (Track 1b) will reject packets outside a
configurable freshness window (±60 s per spec §6.3).

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
