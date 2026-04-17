# Power profile — bench measurement template

**Measurement units:** milliampere (mA) at 3.3 V bus.
**Instrument:** Keysight U1242C DMM (mA range) in series with
the OBC 3V3 rail, or USB inline ammeter on 5 V with the LDO
efficiency (0.85) factored in.
**Scope:** OBC board only (STM32F446 + sensors + radio IC).
Propulsion, magnetorquer drivers, and camera are measured
separately under their own power sub-files when those boards
arrive at the bench.

## Modes

| Mode | Description | Expected (mA) | Measured (mA) | Notes |
|------|-------------|--------------:|--------------:|-------|
| Boot | Reset → first main() instruction | ≤ 80 | TBD | First 10 ms |
| Idle | FreeRTOS idle, no TX, no payload | ≤ 60 | TBD | Steady state |
| Nominal | All sensors polling at 1 Hz, beacon every 30 s | ≤ 90 | TBD | Reference state |
| Imaging | Payload camera active + compression | ≤ 180 | TBD | Bursts ≤ 5 s |
| TX | UHF radio PA on during beacon transmit | ≤ 320 | TBD | 1 s burst |
| Safe mode | Only telemetry + comm + health | ≤ 70 | TBD | Reduced duty |
| Stop | STOP mode with IWDG wake-up every 2 s | ≤ 2 | TBD | Between passes |

All "Expected" values come from the link budget + datasheet
typical-current tables. Actual measurements populate the
"Measured" column during HIL bench work; anything > 120 % of
expected triggers a design review.

## Energy-balance sanity check

With daily orbit-average current drawn at ≤ 90 mA and solar array
output ≥ 3 W peak on UniSat OBC form factor (6 × 0.295 efficient
2 × 4 cm panels, per `docs/power_budget.md`), the battery SOC
should remain ≥ 50 % over a 24 h sunlit / eclipse cycle. Bench
measurement populates the left-hand side of that inequality;
on-orbit telemetry (EPS APID 0x011) populates the right-hand
side post-launch.

## Dependencies

* Bench: DC power supply at 5 V / 1 A current-limited, inline
  ammeter, USB logic analyser probing UART-1 so the OBC mode is
  observable during the measurement.
* Firmware: mode-switch command hooks in
  `firmware/stm32/Core/Src/command_dispatcher.c` (Phase 6
  follow-up) so a ground operator can drive the OBC through
  every row of the table without physical access.
