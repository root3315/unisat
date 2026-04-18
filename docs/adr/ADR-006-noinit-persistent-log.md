# ADR-006: Warm-reboot-survivable fault log via `.noinit` SRAM

**Status:** Accepted — 2026-04-17
**Phase:** 7.4 (Persistent fault log)
**Commit:** 03049a1

## Context

The Phase-3 FDIR advisor counts faults in plain `.bss`, so every
warm reboot — including reboots *caused* by a fault — erases the
counter. A satellite that cycles on repeated `FAULT_STACK_OVERFLOW`
leaves no trace for post-mortem downlink; ground sees only the
current-boot state, not why the previous boot ended.

Flight-software / mission-operations wants:
* the last N fault events carried across a soft reset,
* the reboot reason (which ModeReason_t fired) also preserved,
* a reboot counter so an operator can distinguish a one-time
  glitch from a cycling fault,
* zero impact on host tests — the mechanism must remain
  deterministic when run on a PC with ordinary `.bss` semantics.

## Decision

Reserve a dedicated `.noinit` section in the STM32F446 linker
script and place the persistent ring + header there. The section
is marked `NOLOAD` so `Reset_Handler`'s BSS zero-init loop
**never touches it**; the SRAM contents survive a soft reset
(NVIC_SystemReset, WWDG/IWDG, HardFault recovery path).

Validate-on-read pattern:

```
   first 4 bytes: magic  ('F''D''I''R' LE)
   next  4 bytes: CRC32 over (header[with crc=0] | ring payload)
   next  1 byte : head
   next  1 byte : count
   next  1 byte : reboot_reason
   padding
   next  4 bytes: reboot_count
   ring[16 × 16 bytes]
```

At boot:
* magic mismatch → cold power-on (garbage SRAM) → wipe + arm
* magic OK but head/count out-of-range → torn write → wipe + arm
* magic OK + CRC mismatch → bit flip → wipe + arm
* everything valid → warm reboot; bump reboot_count, preserve ring

## Rationale

* **No flash wear.** The persistent state is SRAM that survives
  soft reset "for free" — no flash erase / program cycle per
  boot.
* **CRC catches partial writes.** A power glitch mid-rotation
  of the ring leaves a valid-looking magic with inconsistent
  head/count/ring; CRC over the whole payload catches it.
* **Magic distinguishes cold vs garbage.** A true cold boot
  leaves 0xFFs in SRAM (or zeroes — depends on the reset type);
  a specific magic marker reliably says "this store was
  written by us".
* **Linker section is universal.** Any toolchain supports
  `.noinit`; no vendor-specific backup-RAM or RTC-backed domain
  is required. STM32F446 has no separate battery-backed RAM but
  the main SRAM survives every soft reset mode.

## Consequences

Positive:
* 272 B of SRAM reserved (16 × 16 B ring + 16 B header) — 0.2%
  of total SRAM budget
* Warm-reboot → downlink carries the pre-reset fault tail
* Ground operator can correlate a reboot cycle to its
  triggering fault
* Test semantics identical on host (plain `.bss` start-of-
  process) and target (.noinit warm-reboot)

Negative:
* Not proof against full power loss (SRAM goes to noise)
* Relies on the MCU's SRAM retention across soft reset — true
  on STM32F4 family, would need re-evaluation on an MCU with
  mandatory zero-init

## Alternatives considered

* **Persist in flash.** Each reboot would write a flash sector;
  wear out in months. Also slow: ~30 ms per write, jittering
  the reset path.
* **RTC backup registers.** STM32F446 has 20 × 32-bit backup
  registers — enough for header + reboot counter but not for
  a 16-entry ring. Would require mixing two storage tiers.
* **External EEPROM.** Adds an I²C BOM part and a driver
  dependency; single-sector wear is slow enough to block a
  time-critical boot path.

## Implementation

```
  MEMORY layout:
    .text / .rodata    FLASH @ 0x08000000
    .data              RAM (loaded)    <- zero-init loop fills
    .bss               RAM             <- zero-init loop fills
    .noinit (NOLOAD)   RAM             <- linker does NOT touch
    ._user_heap_stack  RAM
```

```c
#define NOINIT_ATTR  __attribute__((section(".noinit")))

static FDIR_PersistentHeader_t g_hdr NOINIT_ATTR;
static FDIR_PersistentEntry_t  g_ring[16] NOINIT_ATTR;
```

On host (`SIMULATION_MODE`), `NOINIT_ATTR` expands to empty; the
backing array lives in `.bss` and the test harness uses
`FDIR_Persistent_Wipe()` + a pristine magic to simulate a cold
boot. Exercised by 6 / 6 tests in `test_fdir_persistent.c`.

## Follow-up bug caught during test

Initial implementation had `Wipe()` leave `magic = MAGIC` — which
made the subsequent `Init()` take the warm-reboot branch and
erroneously bump `reboot_count`. Fixed by splitting
`wipe_storage()` (zero everything including magic) and
`arm_storage()` (set magic + CRC). `Init()` on a post-wipe state
now correctly takes the cold-boot branch.
