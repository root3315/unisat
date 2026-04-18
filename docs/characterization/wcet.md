# WCET — Worst-Case Execution Time per FreeRTOS task

**Measurement units:** microseconds (µs).
**Clock:** STM32F446 AHB 168 MHz, verified against HSE trim.
**Instrument:** DWT cycle counter, read at task entry + exit.
**Reporting cadence:** every 1 s via the existing TLM downlink;
characterisation run averages ≥ 10 000 samples per task over
60 min of nominal flight-mode operation.

## Method

Each task is wrapped in a macro `WCET_PROBE(task_id)` that does:

```c
uint32_t t0 = DWT->CYCCNT;
/* ... task body ... */
uint32_t dt = DWT->CYCCNT - t0;
if (dt > wcet_max[task_id]) wcet_max[task_id] = dt;
wcet_sum[task_id] += dt;
wcet_count[task_id]++;
```

`wcet_*[]` is exported via a TLM-only APID (0x0F0). Ground parses
the counter, divides by `SystemCoreClock / 1_000_000` to get µs.

## Results — TEMPLATE (populate from HIL run)

| Task | Period (ms) | WCET (µs) | Mean (µs) | Stddev (µs) | Samples | Budget (µs) | Status |
|------|------------:|----------:|----------:|------------:|--------:|------------:|:------:|
| SensorTask | 1000 | TBD | TBD | TBD | TBD | 800 | ⏳ |
| TelemetryTask | 1000 | TBD | TBD | TBD | TBD | 500 | ⏳ |
| CommTask | 100 | TBD | TBD | TBD | TBD | 50 | ⏳ |
| ADCSTask | 1000 | TBD | TBD | TBD | TBD | 500 | ⏳ |
| WatchdogTask | 1000 | TBD | TBD | TBD | TBD | 100 | ⏳ |
| PayloadTask | 5000 | TBD | TBD | TBD | TBD | 2000 | ⏳ |

**Status legend:** ✅ within budget / ⚠ ≥ 80 % of budget / ❌ exceeds budget / ⏳ not yet measured.

## Budget derivation

Per REQ-TLM-001 the beacon cadence is 30 s, so aggregate CPU
load at 1 Hz telemetry must stay below 60 % to leave headroom
for comm TX, payload bursts, and fault recovery. The per-task
budgets above sum to ≤ 600 000 µs across 1 s = 60 % CPU.

## Dependencies

* `firmware/stm32/Core/Inc/wcet_probe.h` — macro definition
  (Phase 6 follow-up, not yet in repo).
* SWO pin (PB3) routed to ST-Link V2-1 SWV, 2 MHz tracing.
* Ground-side unpacker: `scripts/parse_wcet_tlm.py` (Phase 6
  follow-up).

---

## Host baseline — algorithmic primitives (available today)

The FreeRTOS-task table above waits on the HIL bench. In the
meantime, the four time-critical *algorithmic* primitives
(`encode_ui_frame`, `decoder_push_byte`, `decode_ui_frame`,
`hmac_sha256`) are measured on the host via `bench_ax25` —
10 000 iterations each, ~10 seconds total.

| Primitive | Host mean (µs) | Host min (µs) | Budget (µs) | Status |
|---|---:|---:|---:|:---:|
| `ax25_encode_ui_frame` (48 B) | **5.75** | 3.86 | 5 000 | ✅ |
| `ax25_decoder_push_byte` (whole frame) | **7.16** | 4.14 | 2 000 | ✅ |
| `ax25_decode_ui_frame` (pure) | **1.53** | 1.24 | 2 000 | ✅ |
| `hmac_sha256` (48 B beacon) | **6.37** | 3.98 | 5 000 | ✅ |

Raw JSON:
[`host_wcet_baseline.json`](host_wcet_baseline.json).

**Host ≠ target**. Cortex-M4 at 168 MHz runs pure-C integer code
roughly 10-20× slower than an x86_64 desktop. Projected ARM
upper bounds (20× host mean) stay 14-65× below budget, so the
algorithms themselves are not the bottleneck — any budget violation
found on HIL will come from task-scheduling jitter, interrupt
latency, or HAL wait-states, not from these primitives.

### How to regenerate

```bash
cd firmware
cmake -B build -S .
cmake --build build --target bench_ax25
./build/bench_ax25 | tee ../docs/characterization/host_wcet_baseline.json
```

Commit the updated JSON and the table above together in one PR so
the baseline stays honest.
