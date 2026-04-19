# UniSat — Characterisation data templates

This directory holds the measured characteristics of the firmware
running on the real STM32F446RE target hardware. The numbers the
design documents quote (168 MHz clock, ≤ 60 % CPU load at 10 Hz
telemetry, 5 krad TID tolerance of the STM32F446, …) are
*calculated* or *vendor-claimed*; the files here hold *measured*
values from a specific OBC unit, identified by serial number.

For Phase 5 / TRL-5 the characterisation data itself is not yet
populated — this directory establishes the **format** so that
measurements can be filed systematically when the HIL bench (see
`docs/testing/hil_test_plan.md`) is brought online. Each template
file describes what measurement goes where, what units, and which
tool produced it.

## Templates

| File | Measurement | Source | Tool |
|------|-------------|--------|------|
| `wcet.md` | Worst-case execution time per FreeRTOS task | SWV + DWT cycle counter | ST-Link / openocd + manual analysis |
| `stack_usage.md` | FreeRTOS task stack high-water mark | `uxTaskGetStackHighWaterMark()` over 48 h soak | firmware TLM downlink |
| `heap_usage.md` | heap_4 free bytes min/max/fragmentation | `xPortGetFreeHeapSize()`, dump post-soak | firmware TLM downlink |
| `flash_ram_footprint.md` | `.text/.data/.bss` section sizes, %-of-capacity | `arm-none-eabi-size` | Phase 1 build-time gate |
| `power_profile.md` | mA draw per mode (idle / nominal / imaging / safe / TX) | bench USB ammeter + scope | manual |
| `boot_time.md` | µs from reset to first FreeRTOS task spin | SWV trace with timestamp | manual |
| `i2c_bus_timing.md` | SCL period, ACK latency per sensor | logic analyser | Saleae / OWON |
| `rf_link_budget.md` | Measured BER vs SNR at 437 MHz | RTL-SDR loopback | direwolf |

## Policy

* **One file per metric.** Each file states: measurement units,
  setup diagram, repetition count, results table, and the date +
  OBC serial.
* **Never delete.** When a firmware change invalidates an earlier
  measurement, prepend a new section with the new value and
  annotate the previous section as *superseded by §N of commit
  <sha>*. Rolling history is the audit trail reviewers look for
  when validating a TRL-5 claim.
* **Keep raw data separately.** Reference large traces / CSVs /
  scope captures by path and SHA-256, don't commit the blob.
  Branch-policy target ≤ 50 MB.

## Gap versus a genuine TRL-5 claim

A honest TRL-5 characterisation package must cover the four
environments listed below. The files in this directory are the
*software-side* bookkeeping; the *hardware-side* proof (vibration,
thermal-vacuum, radiation) lives outside the repository and is
referenced by external report number.

| Environment | Measurement needed | Where reported |
|-------------|-------------------|----------------|
| Room-temperature bench | All `.md` files in this directory | this repository |
| Thermal-vacuum | Functional telemetry + beacon cadence across −40..+80 °C sweep | external TVAC report |
| Vibration (launch profile) | Pre/post bench-run telemetry equivalence | external vibration report |
| Radiation (TID ≥ 10 krad) | Post-irradiation bench-run delta | external cyclotron report |

The external-report fields are placeholders for operator-supplied
PDFs. The repository does not claim TRL 5 without them — see
`docs/project/GAPS_AND_ROADMAP.md` §"Out of scope" for the explicit
disclaimer.
