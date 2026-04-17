# ADR-007: Weak HAL shim + optional autodetect over full HAL bundling

**Status:** Accepted — 2026-04-17
**Phase:** 1 (STM32 target build)
**Commit:** 2fb1847

## Context

`firmware/stm32/CMakeLists.txt` needs to produce a linkable ARM
`.elf` out of the box — a fresh `git clone` on a machine with
`arm-none-eabi-gcc` installed should produce an artefact without
any further setup. But every existing sensor driver
(`LIS3MDL`, `BME280`, `TMP117`, ...) calls into the STM32Cube
HAL (`HAL_I2C_Mem_Read`, `HAL_SPI_TransmitReceive`, ...) which
lives in a separate ST-hosted repository (~500 MB). Three
plausible strategies:

1. **Vendor-bundle full HAL.** Ship the whole STM32CubeF4 tree
   under `firmware/stm32/Drivers/STM32F4xx_HAL_Driver/` so it's
   in every clone.
2. **Require user to run setup_stm32_hal.sh before first build.**
   Fail early with a diagnostic if the HAL directory is missing.
3. **Weak shim + optional autodetect.** Ship our own tiny
   `hal_shim.c` with weak stubs for every `HAL_*` function the
   drivers reference; autodetect the real HAL in CMake and drop
   the shim when found.

Option 1 bloats the repo by 15 MB + ties us to ST's licence text.
Option 2 is a worse user experience — `cmake -B build && make`
should work on a fresh clone even if the answer is "boots to
infinite loop with no peripherals".

## Decision

Option 3 — weak shim + autodetect.

`firmware/stm32/Target/hal_shim.c` provides a `__attribute__((weak))`
definition for every HAL entry point the firmware drivers reference
(~30 functions across `HAL_I2C_*`, `HAL_SPI_*`, `HAL_UART_*`,
`HAL_ADC_*`, `HAL_TIM_Base_*`, `HAL_IWDG_*`, `HAL_GPIO_*`). Each
returns `HAL_ERROR` (or zero for `HAL_GetTick` fallback).

`firmware/CMakeLists.txt` probes
`firmware/stm32/Drivers/STM32F4xx_HAL_Driver/Src`:

  * **present** → link the full HAL .c files; the real strong
    symbols override every shim weak symbol at link time; real
    hardware I/O happens.
  * **absent** → link `hal_shim.c`; the firmware boots, clocks
    up, tasks start, but every bus call returns `HAL_ERROR`
    (drivers already handle this by returning a sentinel).

## Rationale

* **Fresh clone produces an artefact.** `cmake -B build-arm && make`
  gives a .elf on day zero; no setup script required.
* **Production build is unchanged.** After `setup_stm32_hal.sh`
  runs once, the shim silently drops out; the production `.elf`
  is byte-identical to a bundle-HAL approach.
* **CI stays fast.** The `unisat-ci` Docker image doesn't need
  the 500 MB HAL tree to run the host-side `make cppcheck` /
  `ctest` / coverage gates — those never compile the ARM
  target.
* **No licence bundling question.** STMicro's SLA0044 licence is
  permissive but explicit; keeping HAL as a user-initiated fetch
  avoids distributing licence text we don't own.

## Consequences

Positive:
* `git clone` + `make target` always produces an .elf
* Shim is ~200 lines, small and auditable
* Zero cost when the real HAL is linked — weak-symbol override
* Same shim works for unit tests that reach a HAL call path

Negative:
* Production first-build requires the explicit setup step
  `make setup-hal` (one-time, documented in USAGE_GUIDE)
* A new HAL entry point used by a new driver needs a matching
  shim stub added manually (caught immediately by linker error)

## Alternatives considered

* **Submodule** — ties the user to a specific HAL version and
  makes switching versions a git-submodule dance
* **Package-manager dep** — no mature embedded package manager
  covers STM32 HAL in 2026
* **Vendored copy** — as rejected above; 15 MB bloat + licence
  distribution

## Implementation

```
firmware/stm32/Target/hal_shim.c         ← weak stubs
firmware/CMakeLists.txt:170              ← autodetect block:
    if(EXISTS "${HAL_DRIVER_DIR}/Src")
        link HAL_SOURCES, drop hal_shim
    else()
        link hal_shim, print reminder
scripts/setup_stm32_hal.sh               ← one-shot fetch
```

Tested by:
* Host build in CI: `hal_shim.c` compiled into the host target's
  unused-symbol pool; every test passes 27/27.
* ARM build (documented path): `setup-hal && make target` then
  `make size` stays under the 90 % flash/RAM budget.

A symmetric pattern is used in ADR-008 for the FreeRTOS kernel
(see scripts/setup_freertos.sh + 4b2309a).
