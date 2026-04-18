# ADR-004: Reserve counter = 0 as uninitialised sentinel in replay window

**Status:** Accepted — 2026-04-17
**Phase:** 2 (Anti-replay)
**Commit:** 942abce

## Context

The command dispatcher gained a 32-bit monotonic counter + 64-bit
sliding-window bitmap to reject replayed uplink commands. Two
design choices around counter semantics bit us during test:

1. On cold boot, `g_high_counter` is 0 and the bitmap is empty.
   A prerecorded frame with counter = 0 would walk the "first of
   epoch" branch and be accepted — replayable indefinitely across
   reboots.
2. If 0 is a valid counter, the ground side must carefully track
   its first transmission; off-by-one here produces either a
   reject or a replay-window misalignment.

## Decision

**Counter value 0 is reserved. The firmware rejects every frame
with counter == 0 regardless of HMAC validity; the ground library
(`ground-station/utils/hmac_auth.py`) raises
`ReplayCounterError` when a caller tries to build a frame with
counter <= 0.**

Senders start at counter = 1 and increment monotonically.

## Rationale

* **Power-on replay prevention.** Immediately after a soft reset
  `g_high_counter` is 0. If 0 were a legitimate counter value,
  an attacker with a captured counter=0 frame could replay it
  and pass the "first frame of epoch" branch — indistinguishable
  from a fresh boot.
* **Simple sender contract.** "Start at 1" is an obvious rule;
  "start at 0 but make sure the firmware has seen something
  first" invites misconfiguration.
* **Room for future signal values.** Reserving 0 (and implicitly,
  values above 2^32 - 1) leaves the library room to repurpose
  those ranges later — e.g. a "force key rotation" command could
  use counter = UINT32_MAX as a distinguished marker without
  colliding with normal traffic.

## Consequences

Positive:
* Power-on replay of a captured counter=0 frame is rejected
  without any additional state
* Fail-closed by default — if sender forgets to seed the counter
  at all, the 0 default value rejects rather than "works once"
* Ground library's input validation catches the error before the
  frame ever hits the air

Negative:
* One counter value out of 2^32 is unavailable (4.2 billion
  legitimate uses remain per key epoch — not a practical limit)
* Senders must remember "start at 1, not 0"

## Implementation

Firmware (`firmware/stm32/Core/Src/command_dispatcher.c`):

```c
if (counter == 0U) {
    return false;        /* reserved sentinel */
}
```

Ground (`ground-station/utils/hmac_auth.py`):

```python
if counter <= 0 or counter > 0xFFFFFFFF:
    raise ReplayCounterError(...)
```

Both paths are exercised by dedicated tests:
* `test_command_dispatcher.c::test_counter_zero_rejected`
* `test_hmac_auth.py::test_counter_zero_or_out_of_range_rejected`
