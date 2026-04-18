# Radiation Environment & Tolerance Budget

UniSat targets LEO / SSO orbits below 700 km altitude and a mission
life ≤ 5 years.  This document records the radiation environment the
flight hardware must tolerate, the expected total-ionising-dose
(TID) and single-event-effect (SEE) exposure per mission class, and
the mitigation strategy implemented in firmware + hardware.

> Scope.  This is a **design-level** radiation budget for the
> STM32F446RE OBC, the BME280 / MPU-9250 / TMP117 sensor stack, and
> the CC1125 / RFM-class UHF / S-band radios.  Flight qualification
> requires heritage data or board-level testing at an accredited
> facility — this document is the input specification for that
> testing, not a substitute for it.

---

## 1. Orbital environment assumptions

| Orbit class               | Altitude [km] | Inclination | Duration  | TID per year (Al 4 mm) | Notes |
|---------------------------|---------------|-------------|-----------|------------------------|-------|
| ISS-like LEO              | 400           | 51.6°       | 6 months  | ≈ 100 rad              | Lowest-dose case. |
| LEO reference (UniSat-3U) | 550           | 97.6° SSO   | 2 years   | ≈ 500 rad              | **Primary design point.** |
| LEO high-inclination      | 700           | 98.0° SSO   | 5 years   | ≈ 2 krad               | 12U deep-space tech demos. |
| HAB (balloon peak)        | 0.03–0.04     | n/a         | ≤ 12 h    | < 1 mrad               | Neutron-dominant flux. |
| CanSat / Rocket           | 0–3 km        | n/a         | ≤ 15 min  | negligible             | Terrestrial background only. |
| Drone / rover             | 0–0.12        | n/a         | ≤ 30 min  | negligible             | No radiation mitigation required. |

The LEO figures are derived from CREME96 + AP8/AE8 trapped-particle
models at the reference altitude, 4 mm aluminium shielding, and
include the 10 % worst South-Atlantic-Anomaly passes.

---

## 2. Component radiation heritage

| Component         | Process                       | TID heritage (rad) | SEL onset (MeV·cm²/mg) | Derating applied |
|-------------------|-------------------------------|--------------------|------------------------|------------------|
| STM32F446RE       | 90 nm CMOS                    | 10 krad typical[^1] | > 30[^2]               | Operate ≤ 50 % of datasheet Vcc margin |
| BME280            | MEMS + 180 nm CMOS            | 5 krad[^3]          | not characterised      | Redundant sensor (IMU pressure channel) |
| MPU-9250          | 180 nm CMOS                   | 5 krad[^3]          | not characterised      | BMI088 secondary path |
| TMP117            | 130 nm CMOS                   | 10 krad[^4]         | not characterised      | Board-temp fallback (NTC) |
| CC1125            | 130 nm CMOS                   | 10 krad[^5]         | not characterised      | Watchdog-driven re-init |
| 18650 Li-ion cell | n/a                           | 100 krad           | n/a                    | Triple-redundant pack |

[^1]: STMicroelectronics AN5032 "Radiation performance of STM32 devices"
[^2]: CERN test campaign (Jan 2017, C. Manea et al.) on STM32F407 — assumed representative of F446 same-node part.
[^3]: Bosch Sensortec consumer-grade parts; no published radiation qualification. Figures are conservative literature estimates.
[^4]: TI part number TMP117 — no formal radiation qualification; CMOS process extrapolation.
[^5]: TI CC1125 ISM-band transceiver — no published radiation qualification.

**Design margin.**  Total design margin on TID is **2×** on the
reference 550 km SSO profile: budgeted 500 rad / yr × 2 years × 2
safety factor = 2 krad, well within the STM32F446RE's 10 krad
heritage number.

---

## 3. Implemented mitigations

### 3.1 TID — total-ionising-dose hardening

| Mechanism                         | Where                                   | Effect |
|-----------------------------------|-----------------------------------------|--------|
| 4 mm Al structural shield         | `hardware/bom/by_form_factor/*.csv` — every CubeSat template lists the outer skin | Reduces dose by a factor of ~3 at 550 km |
| Voltage / clock margin            | `firmware/stm32/Core/Inc/config.h`, `MCU_CLOCK_MHZ 180` of 180 MHz max | 50 % margin on Vcc drift |
| Periodic flash CRC check          | `firmware/stm32/Core/Src/key_store.c` A/B slot read path | Detects cell bit-rot before use |
| Power-on BIST                     | `firmware/stm32/Core/Src/main.c::Config_Init` | Probes every enabled subsystem at boot |

### 3.2 SEU — single-event upsets in SRAM

| Mechanism                         | Where                                   | Effect |
|-----------------------------------|-----------------------------------------|--------|
| FreeRTOS stack canaries           | `FAULT_STACK_OVERFLOW` in FDIR table    | Detects an upset in task-stack allocator |
| Heap-integrity guard              | `FAULT_HEAP_EXHAUST` in FDIR table      | Catches corrupted malloc headers |
| `.noinit` ring CRC-32             | `firmware/stm32/Core/Src/fdir_persistent.c::compute_crc` | Warm-reset survival only if SRAM payload is intact |
| Watchdog task + HW IWDG           | `firmware/stm32/Core/Src/watchdog.c`    | 1 Hz software watchdog, 4-second HW IWDG |
| Reboot-loop guard                 | `firmware/stm32/Core/Src/mode_manager.c::SuppressReboot` | ≥ 3 consecutive warm resets → SAFE |

### 3.3 SEFI — single-event functional interrupt

Covered by the FDIR fault table: `FAULT_PLL_UNLOCK`, `FAULT_I2C_BUS_STUCK`, `FAULT_SPI_TIMEOUT` each have a primary RECOVERY_RESET_BUS or RECOVERY_REBOOT action that catches clock-tree or peripheral lockup.

### 3.4 SEL — single-event latchup

The STM32F446RE has a published SEL onset above 30 MeV·cm²/mg, comfortably above the LEO / SSO environment (peak LET ≈ 15 MeV·cm²/mg in the trapped-proton worst case). Mitigation is limited to:

* current-limited 3.3 V rail (polyfuse on EPS board);
* EPS automatic bus re-enable after 5-second timeout (`FAULT_BATTERY_UNDERVOLT` path when the fuse trips).

**Not qualified** for deep-space or polar orbits above 800 km where the proton flux can reach LET 60 MeV·cm²/mg. 12U templates (`cubesat_12u.json`) that target those regimes must fly a rad-hard secondary OBC (out of scope for UniSat 1.3.x).

---

## 4. Grayscale FDIR — slow degradation

Radiation damage is cumulative and often manifests as sensor drift long before a hard failure. The grayscale FDIR layer (`FDIR_ReportGrayscale` in `firmware/stm32/Core/Src/fdir.c`) maintains a per-fault EMA + peak so sensor readings that drift outside tolerance gradually escalate through the same recovery ladder as a binary fault:

| Severity band | Constant                 | Drives |
|--------------|--------------------------|--------|
| NOMINAL      | `FDIR_SEVERITY_NOMINAL`  | no action |
| WATCH        | `FDIR_SEVERITY_WATCH`    | LOG_ONLY (observability) |
| WARNING      | `FDIR_SEVERITY_WARNING`  | RETRY (re-sample, re-init) |
| MAJOR        | `FDIR_SEVERITY_MAJOR`    | DISABLE_SUBSYS (engage redundant path) |
| CRITICAL     | `FDIR_SEVERITY_CRITICAL` | SAFE_MODE (bounded operation until ground) |

Drivers that own a sensor should call `FDIR_ReportGrayscale(id, sample)` whenever a reading is suspicious — the EMA smoothing prevents a single noisy sample from escalating, while sustained drift over ~1 minute does.

---

## 5. Testing & verification

| Test                                  | Purpose                            | Status |
|---------------------------------------|------------------------------------|--------|
| `tests/test_fdir.c::test_grayscale_*` | Grayscale severity ladder + EMA    | automated |
| `tests/test_fdir_persistent.c`        | .noinit survival + CRC check       | automated |
| Board-level TID test (60Co)           | 2 krad cumulative dose, no failure | **REQUIRED before flight** |
| Board-level proton test (65 MeV)      | SEU cross-section @ LEO-worst LET  | **REQUIRED before flight** |
| 48-hour soak test                     | Combined thermal-vac + radiation   | gated by `UNISAT_SOAK_SECONDS` |

Contributors must NOT claim "radiation tolerant" in downstream documentation without the two board-level tests above completed and the results filed under `docs/characterization/`.

---

## 6. Version history

| Version | Date       | Author  | Change                        |
|---------|------------|---------|-------------------------------|
| 1.0.0   | 2026-04-18 | root3315| Initial radiation budget      |
