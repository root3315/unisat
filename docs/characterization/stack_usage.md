# Stack usage — FreeRTOS task high-water marks

**Measurement units:** bytes (STM32F446 is 32-bit; `configSTACK_DEPTH_TYPE`
word count × 4).
**Instrument:** `uxTaskGetStackHighWaterMark()` read at 10 s cadence.
**Soak duration:** 48 h nominal flight-mode.
**Reporting:** stack minimum free bytes per task, downlinked with
housekeeping telemetry APID 0x010.

## Method

Each task's init path writes a known sentinel pattern through the
entire stack (FreeRTOS default on `configCHECK_FOR_STACK_OVERFLOW`
= 1). A periodic probe walks the stack looking for the first word
that still holds the sentinel — the watermark. A deep-recursion
event trims the watermark downward permanently; no "healing" is
possible once a push overwrote the sentinel, so the watermark is
a true worst-case witness across the whole soak.

## Budget vs observation — TEMPLATE (populate from HIL run)

| Task | Allocated (B) | HWM observed (B) | Margin (%) | Status |
|------|--------------:|-----------------:|-----------:|:------:|
| SensorTask | 2048 | TBD | TBD | ⏳ |
| TelemetryTask | 2048 | TBD | TBD | ⏳ |
| CommTask | 4096 | TBD | TBD | ⏳ |
| ADCSTask | 4096 | TBD | TBD | ⏳ |
| WatchdogTask | 1024 | TBD | TBD | ⏳ |
| PayloadTask | 2048 | TBD | TBD | ⏳ |
| **IDLE (FreeRTOS)** | 256 | TBD | TBD | ⏳ |
| **Timer (FreeRTOS)** | 512 | TBD | TBD | ⏳ |

**Margin:** `(allocated − HWM) / allocated * 100`.
**Status legend:** ✅ ≥ 30 % free / ⚠ 15–30 % / ❌ < 15 % (bump stack) / ⏳ not yet measured.

## Allocation rationale

Sizes from `firmware/stm32/Core/Inc/main.h`:

| Define | Value (words) | Bytes |
|--------|--------------:|------:|
| `SENSOR_TASK_STACK_SIZE` | 512 | 2048 |
| `TELEMETRY_TASK_STACK_SIZE` | 512 | 2048 |
| `COMM_TASK_STACK_SIZE` | 1024 | 4096 |
| `ADCS_TASK_STACK_SIZE` | 1024 | 4096 |
| `WATCHDOG_TASK_STACK_SIZE` | 256 | 1024 |
| `PAYLOAD_TASK_STACK_SIZE` | 512 | 2048 |

`configTOTAL_HEAP_SIZE` (heap_4) is sized to accommodate the sum
of task control blocks + queue storage; tracked separately in
`heap_usage.md`.

## Dependencies

* `FreeRTOSConfig.h`: `configCHECK_FOR_STACK_OVERFLOW = 2`
  (method-2 pattern check) and `INCLUDE_uxTaskGetStackHighWaterMark = 1`.
* `vApplicationStackOverflowHook()` implemented in
  `firmware/stm32/Core/Src/error_handler.c` to raise
  `FAULT_STACK_OVERFLOW` on hook entry (primary action REBOOT per
  `docs/reliability/fdir.md`).
