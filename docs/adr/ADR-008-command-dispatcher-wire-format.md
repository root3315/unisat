# ADR-008: CCSDS-agnostic command-dispatcher wire format

**Status:** Accepted — 2026-04-17
**Phase:** 1b + 2
**Commits:** 99774cf (original) → 942abce (counter added)

## Context

The command dispatcher receives frames from the AX.25 streaming
decoder and has to decide: authentic? fresh? act on it?

Two designs competed:

1. **Consume a parsed `CCSDS_Packet_t`** — the decoder calls
   `CCSDS_Parse(bytes, len, &pkt)` first, and the dispatcher
   operates on the parsed struct (APID, secondary header
   timestamp, data[]).
2. **Consume raw bytes, treat the payload as opaque** — the
   dispatcher only knows "here are N bytes, verify + extract
   counter + forward to handler", zero CCSDS awareness.

## Decision

Option 2. Dispatcher wire format is:

    [ 4-byte counter (BE) ][ opaque body ][ 32-byte HMAC tag ]
      \_________ authenticated ________/

The dispatcher neither parses nor validates CCSDS fields. The
registered `CommandHandler_t` receives the "body" bytes and is
free to interpret them as CCSDS (or anything else) at its own
pace.

## Rationale

* **Layer separation.** The HMAC + replay filter is a
  transport-level concern; CCSDS is the application-level
  payload encoding. Mixing the two means a CCSDS schema change
  (e.g. adding a secondary-header field) ripples into the
  security-critical path.
* **Testability.** `test_command_dispatcher.c` doesn't need any
  CCSDS helper — it passes raw `[counter | body | tag]` arrays
  and asserts only what the dispatcher promises. CCSDS tests
  live separately in `test_ccsds*.c`.
* **Future proof.** A future mission that swaps CCSDS for, say,
  CSP or a mission-specific TLV encoding, reuses the dispatcher
  as-is. Only the handler changes.
* **Crypto-scope clarity.** The HMAC authenticates
  `counter || body`. Everything inside body is protected
  without the dispatcher needing to know what "inside" means.

## Consequences

Positive:
* ~80-line command_dispatcher.c, zero CCSDS dependencies
* Easy unit-testing with synthetic fixtures
* Wire format evolution is decoupled from crypto format
* Handler can be as dumb or smart as the mission wants

Negative:
* CCSDS sequence-count duplication: both CCSDS primary header
  AND the HMAC replay counter serve freshness-adjacent roles.
  Resolved by ADR-004: counter starts at 1 and is the
  authoritative anti-replay source; CCSDS sequence stays as
  the application-layer housekeeping field.
* Ground operator must maintain two counters — the CCSDS
  sequence in the packet + the dispatcher counter in the wrap.
  Documented in `ground-station/utils/hmac_auth.py:CounterSender`.

## Alternatives considered

* **Dispatcher parses CCSDS, uses secondary-header timestamp
  as freshness token** — rejected; timestamps require a real
  RTC on the flight side, which UniSat does not have as a
  hard requirement.
* **Dispatcher uses CCSDS sequence count as the replay
  counter** — rejected; CCSDS sequence is 14 bits, wraps at
  16384, can be reset by a ground-side restart, and is not
  HMAC-covered if the sender forgets to include the full
  primary header in the auth span.
* **Separate HMAC and body (split packet)** — rejected;
  increases wire overhead and complicates the streaming
  decoder.

## Implementation

```c
void CCSDS_Dispatcher_Submit(const uint8_t *data, uint16_t len) {
    /* 1. length >= 4 counter + 1 body + 32 tag = 37 */
    /* 2. recompute HMAC over data[0..len-32], compare to data[len-32..] */
    /* 3. extract counter from data[0..4] BE */
    /* 4. replay-window check */
    /* 5. forward data[4..len-32] to handler */
}
```

Source: `firmware/stm32/Core/Src/command_dispatcher.c` +
tests `firmware/tests/test_command_dispatcher.c` (11/11) +
integration `firmware/tests/test_boot_security.c` (4/4) +
Python mirror `ground-station/utils/hmac_auth.py` with
`test_hmac_auth.py` (22/22).
