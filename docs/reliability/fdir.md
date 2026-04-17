# Fault Detection, Isolation, Recovery (FDIR)

**Module:** `firmware/stm32/Core/Src/fdir.c`
**Header:** `firmware/stm32/Core/Inc/fdir.h`
**Tests:**  `firmware/tests/test_fdir.c` — 9/9 green.
**Phase:**  TRL-5 hardening, Phase 3.

FDIR is the satellite's autonomous supervision layer. It sits
above the hardware IWDG and the subsystem-level error handlers,
and answers the only question operations actually cares about:

> when something goes wrong, what does the satellite do next?

The module is deliberately *advisory*: it tracks faults, classifies
severity, and recommends a recovery action. The actual mode change
(bus reset, subsystem disable, safe-mode entry, reboot) is enacted
by the caller — the subsystem supervisor task, the safe-mode
manager, or `error_handler.c`. Keeping FDIR advisory means:

* unit tests cover the escalation logic without linking a real
  safe-mode implementation;
* a bug in safe-mode never hides an FDIR escalation;
* downlink telemetry can report "FDIR recommended SAFE_MODE at
  tick X but the supervisor was already in SAFE_MODE so no mode
  change occurred", which is an important distinction for
  ground-side anomaly review.

## Recovery severity ladder

```
LOG_ONLY
 └─► RETRY                      (transient — re-try the operation)
      └─► RESET_BUS             (peripheral / bus reset sequence)
           └─► DISABLE_SUBSYS   (isolate the failing subsystem;
                                 mission continues in degraded mode)
                └─► SAFE_MODE   (beacon-only, min power, stable
                                 attitude, wait for ground)
                     └─► REBOOT (NVIC_SystemReset after persisting
                                 the reason in non-volatile fault log)
```

Each fault has a **primary** action and an **escalation** action;
escalation kicks in once the fault has fired `threshold` times
inside `FDIR_RECENT_WINDOW_MS` (default 60 s).

## Fault table (source of truth)

Derived from the static `g_table[]` in `fdir.c`. Changing an entry
here requires changing the code — there is no runtime config file.

| id | name | primary | escalation | threshold |
|---:|------|---------|------------|----------:|
| 0 | `watchdog_task_miss` | RESET_BUS | REBOOT | 3 |
| 1 | `i2c_bus_stuck` | RESET_BUS | DISABLE_SUBSYS | 5 |
| 2 | `spi_timeout` | RETRY | DISABLE_SUBSYS | 5 |
| 3 | `sensor_out_of_range` | LOG_ONLY | DISABLE_SUBSYS | 10 |
| 4 | `battery_undervolt` | SAFE_MODE | REBOOT | 2 |
| 5 | `over_temperature` | DISABLE_SUBSYS | SAFE_MODE | 3 |
| 6 | `under_temperature` | LOG_ONLY | SAFE_MODE | 3 |
| 7 | `stack_overflow` | REBOOT | REBOOT | 1 |
| 8 | `heap_exhaust` | SAFE_MODE | REBOOT | 2 |
| 9 | `pll_unlock` | REBOOT | REBOOT | 1 |
| 10 | `comm_loss` | SAFE_MODE | REBOOT | 2 |
| 11 | `keystore_empty` | LOG_ONLY | SAFE_MODE | 1 |

### Rationale for the thresholds

* **watchdog_task_miss = 3.** A single miss can be caused by a
  priority inversion that resolves itself; two misses is still
  plausible under unusual load; three is the point where something
  structural is wrong and reboot is safer than continuing.
* **I2C = 5 / SPI = 5.** The sensor bus is shared between 4 I²C
  devices + GNSS; a stuck SDA during one sensor read can still
  recover if the bus-reset sequence (9 clocks + STOP) is applied
  on the second or third attempt. Five gives enough head-room for
  a genuinely transient event without wasting the day on a hard
  failure.
* **sensor_out_of_range = 10.** Aggressive attitude rotation can
  momentarily clip the magnetometer or gyro; a single out-of-range
  sample is not a fault, it's data. Ten in one minute means the
  sensor is either broken or in sustained saturation — either way
  disable it.
* **battery_undervolt = 2.** The battery manager (EPS) already
  runs MPPT + load-shedding. A single undervolt trip means we're
  at the floor; two in one minute means the load profile is wrong
  for current illumination and we need to drop to SAFE_MODE to
  let the cells recover.
* **over_temperature = 3 / under_temperature = 3.** Thermal time
  constants on a 1U bus are minutes, so three over-threshold
  reads in 60 s is a genuine trend.
* **stack_overflow = 1 / pll_unlock = 1.** No warning needed —
  these are hard structural failures; reboot immediately.
* **heap_exhaust = 2.** One NULL-malloc is recoverable (caller
  should be paranoid anyway); two means the arena is fragmented
  and SAFE_MODE then REBOOT is the cleanest.
* **comm_loss = 2.** One 24 h window with no uplink could be a
  ground outage; two means the issue is on-board.
* **keystore_empty = 1.** Boot with no key means the satellite
  cannot accept authenticated commands. Not recoverable by itself;
  SAFE_MODE keeps the beacon alive so ground can reload via a
  fallback contingency procedure.

## API usage patterns

### From a driver (transient fault)

```c
if (HAL_I2C_Mem_Read(...) != HAL_OK) {
    FDIR_Report(FAULT_I2C_BUS_STUCK);
    switch (FDIR_GetRecommendedAction(FAULT_I2C_BUS_STUCK)) {
    case RECOVERY_RESET_BUS:
        i2c_bus_reset();          /* 9 clocks + STOP */
        break;
    case RECOVERY_DISABLE_SUBSYS:
        sensors_disable_group(SENSOR_GROUP_I2C);
        break;
    default:
        break;
    }
    return -1;
}

/* On success, tell FDIR the fault is behind us so a single later
 * glitch doesn't tip the window into escalation. */
FDIR_ClearRecent(FAULT_I2C_BUS_STUCK);
```

### From a subsystem supervisor (periodic)

```c
if (FDIR_GetRecommendedAction(FAULT_BATTERY_UNDERVOLT)
        >= RECOVERY_SAFE_MODE) {
    mode_manager_enter_safe(SAFE_MODE_REASON_POWER);
}
```

### From telemetry (downlink)

```c
FDIR_Stats_t st = FDIR_GetStats();
beacon_pack_u32(buf, 40, st.total_faults);
beacon_pack_u32(buf, 44, st.escalations);
beacon_pack_u32(buf, 48, st.safe_mode_entries);
beacon_pack_u32(buf, 52, st.reboots_scheduled);
```

## Testing

`firmware/tests/test_fdir.c` covers:

1. Empty state after init.
2. Single report returns primary action.
3. Escalation triggers at exactly the threshold.
4. Cross-fault isolation — reporting fault A doesn't bump B.
5. Recent-window slides — stale events don't accumulate into
   escalation, the window resets cleanly.
6. `ClearRecent` drops recent_count to 0 but preserves total_count.
7. `ResetAll` zeroes both per-fault state and aggregate stats.
8. Out-of-range id (e.g. 99) is handled without crashing.
9. Aggregate stats (`safe_mode_entries`, `reboots_scheduled`)
   track eagerly so downlink telemetry reflects current policy.

Run locally:
```
make build && ctest --test-dir firmware/build -R fdir --output-on-failure
```

Expected output:
```
1/1 Test #18: fdir ............................   Passed    0.01 sec
100% tests passed, 0 tests failed out of 1
```

## What FDIR explicitly does NOT do

* **It does not execute recoveries.** The caller is responsible.
  Rationale above.
* **It does not persist state across reboots in this phase.** The
  per-fault counters are `.bss` and reset to zero on warm boot.
  A follow-up (Phase 4 non-volatile fault log) will add an
  `.noinit` shadow so a REBOOT recommendation survives with the
  triggering reason attached.
* **It does not directly talk to HAL.** Tick source is behind a
  weak hook (`__fdir_hal_tick`) so host tests can inject a
  deterministic clock and the firmware links on a bare-metal
  smoke build with no HAL dependency.
