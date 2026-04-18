# ADR-003: Dual-slot HMAC key store with CRC + monotonic generation

**Status:** Accepted — 2026-04-17
**Phase:** 2 (Replay protection + secure key store)
**Commit:** 508aba7

## Context

The command dispatcher (HMAC-authenticated uplink) at 99774cf
(Track 1b) held the pre-shared key in a RAM variable populated at
runtime. This left two unresolved questions:

1. Where does the key come from on a cold boot? If nothing
   pre-populates the variable, the satellite refuses every
   uplink — including legitimate traffic. The satellite needs a
   durable key that survives power cycles.
2. How is a key rotated in flight? If an operator detects a key
   compromise (ground station intrusion, captured HF trace), the
   recovery procedure must replace the key without physical
   access to the spacecraft.

Storing a single key in a dedicated flash sector (straight-line
design) solves (1) but not (2) safely: a power-loss during the
erase-program cycle of a rotation leaves half-erased bytes and
no usable key at the next boot — the satellite bricks itself.

## Decision

A/B dual-slot persistent store with monotonic generation counter,
CRC-protected records, and "write-to-inactive-then-switch"
rotation semantics.

```
+--------- slot A ----------+   +--------- slot B ----------+
| magic | gen | key | CRC32 |   | magic | gen | key | CRC32 |
+---------------------------+   +---------------------------+
     41 B                           41 B
```

Boot-time rule: pick the slot with the highest generation whose
magic marker and CRC both validate. Rotation rule: write new
record to the currently-INACTIVE slot, verify by read-back, then
accept. If a power-loss happens mid-erase of the inactive slot,
the active slot with the previous generation is still valid and
next boot uses it — graceful degradation.

## Rationale

* **Single-slot is unsafe.** Torn writes brick the satellite.
* **A/B scheme is industry-standard.** SPIFFS, LittleFS, ST's
  EEPROM-emulation AN3969 all use two-sector wear-and-fail-safe
  rotation.
* **CRC-32 catches half-erased sectors.** A magic word alone is
  not enough — a partial write can produce a legitimate-looking
  magic + wrong key. CRC over (magic | gen | key) is the
  minimum that detects torn writes.
* **Monotonic generation prevents downgrade replay.** Even if an
  attacker captures an old rotation command's bytes, replaying
  it against the store is rejected because new_gen <= current
  fails the monotonicity check.

## Consequences

Positive:
* Key survives power cycles without flash write every boot
* Rotation is safe against power-loss
* Downgrade attacks via replay of old rotation command
  automatically rejected
* Same CRC + magic check catches cosmic-ray bit flips in the
  record for free

Negative:
* Two flash sectors (8 KB on F446RE) reserved instead of one
* Rotation needs two separate erase-then-program operations
  (inactive slot + previous active's invalidation, though the
  library does not explicitly invalidate — the higher-gen
  record wins at boot either way)
* First-boot-ever requires a factory-programming step to
  install the initial key and generation = 1

## Alternatives considered

* **Single flash sector + RAM cache** — rejected; torn-write
  during rotation bricks the satellite.
* **Journaling log of N past keys** — over-engineered; the
  mission only needs the *current* key, not history.
* **External secure element (ATECC608)** — strong security but
  adds a BOM part, I2C routing, and trust chain. UniSat is
  student-class, not nation-state threat model.

## Implementation

See `firmware/stm32/Core/Src/key_store.c` + tests in
`firmware/tests/test_key_store.c` (10/10) +
`firmware/tests/test_boot_security.c` (4/4).

Platform hooks (`key_store_platform_{read,write,erase}`) are
weak, defaulting to in-RAM for host tests; a target build
overrides them with HAL_FLASHEx_Erase + HAL_FLASH_Program.
