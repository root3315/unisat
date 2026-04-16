# Testing Plan

Reference: ECSS-E-ST-10-02C (Verification), ECSS-E-ST-10-03C (Testing), GEVS-SE Rev. A (NASA), CubeSat Design Specification Rev. 14

## 1. Test Philosophy and Approach

### 1.1 Verification Strategy

The UniSat verification program follows a protoflight approach (combined qualification and
acceptance) as standard for university CubeSats. Tests progress from component to system level:

```
  Component/Unit     Integration        System         Acceptance/Launch
  +-----------+    +------------+    +----------+    +----------------+
  | Software  |    | Board-to-  |    | Full     |    | Final          |
  | unit tests|--->| board comm |--->| mission  |--->| functional +   |
  | HW bench  |    | Flat-sat   |    | sim &    |    | fit check in   |
  | tests     |    | end-to-end |    | env test |    | deployer       |
  +-----------+    +------------+    +----------+    +----------------+
       V-level          V-level          V-level           V-level
       Component        Integration      System            Acceptance
```

### 1.2 Verification Methods

| Method | Code | Usage |
|--------|------|-------|
| Test (T) | T | Functional verification via controlled stimuli |
| Analysis (A) | A | Verification by mathematical/simulation models |
| Review of Design (RD) | RD | Verification by inspection of documentation |
| Inspection (I) | I | Physical examination of hardware |

## 2. Complete Test Matrix

### 2.1 Unit-Level Software Tests

| Test ID | Module | Description | Pass Criteria | Method | Status |
|---------|--------|-------------|---------------|--------|--------|
| T-001 | CCSDS | Packet build/parse roundtrip | 100% data integrity, all fields match | T | Pass |
| T-002 | CCSDS | CRC-16 corruption detection | Detect all single-byte bit errors (1-8 bits) | T | Pass |
| T-003 | CCSDS | Packet with max payload (4096 bytes) | Correct length field, no overflow | T | Pass |
| T-004 | CCSDS | APID range validation | Reject APID > 0x7FF, accept valid APIDs | T | Pass |
| T-005 | CCSDS | Sequence counter rollover at 16383 | Counter wraps to 0, no packet loss | T | Pass |
| T-006 | ADCS | Quaternion normalization | norm(q) = 1.0 +/- 1e-5 after 1000 operations | T | Pass |
| T-007 | ADCS | Euler-to-Quaternion roundtrip | Error < 0.001 rad for all Euler angles | T | Pass |
| T-008 | ADCS | B-dot controller sign convention | Dipole moment opposes dB/dt (negative correlation) | T | Pass |
| T-009 | ADCS | Magnetorquer duty cycle limits | Output clamped to [-1.0, +1.0] | T | Pass |
| T-010 | ADCS | IGRF magnetic field model | Match NOAA reference values +/- 100 nT | T | Pending |
| T-011 | EPS | MPPT duty cycle clamping | 0.10 <= duty_cycle <= 0.95 | T | Pass |
| T-012 | EPS | Battery overcharge protection | Charge disabled when any cell > 4.2V | T | Pass |
| T-013 | EPS | Battery overdischarge protection | Load disconnect when any cell < 3.0V | T | Pass |
| T-014 | EPS | Power mode transition logic | Correct mode entered per SOC thresholds | T | Pass |
| T-015 | EPS | Telemetry scaling (ADC to engineering) | Voltage +/- 50mV, Current +/- 10mA of truth | T | Pass |
| T-016 | Flight | Config JSON loading | Valid config parsed without error | T | Pass |
| T-017 | Flight | Config validation (missing fields) | Graceful error, defaults applied | T | Pass |
| T-018 | Flight | Watchdog timer service | WDT reset within deadline, system reset on timeout | T | Pass |
| T-019 | Flight | Mode manager state transitions | All valid transitions succeed, invalid rejected | T | Pending |
| T-020 | Ground | Telemetry decode accuracy | All fields match encoded values exactly | T | Pass |
| T-021 | Ground | Command encode/send/ack | Command acknowledged within 5s timeout | T | Pending |
| T-022 | Ground | Pass prediction accuracy | AOS/LOS within 30s of STK reference | A | Pending |
| T-023 | Ground | TLE parsing and propagation | Position error < 5 km at 24h prediction | T | Pending |
| T-024 | Payload | Radiation sensor data parsing | Dose rate values in expected range | T | Pending |
| T-025 | Payload | Camera image capture and compression | JPEG output valid, size < 3 MB | T | Pending |

### 2.2 Integration-Level Tests

| Test ID | Subsystems | Description | Pass Criteria | Method | Status |
|---------|-----------|-------------|---------------|--------|--------|
| IT-001 | OBC + COMM | CCSDS packet TX/RX over UART | Roundtrip integrity, < 1% packet loss at 9600 bps | T | Pending |
| IT-002 | OBC + EPS | Power telemetry pipeline | ADC readings match multimeter within 2% | T | Pending |
| IT-003 | OBC + ADCS | Sensor data acquisition chain | Magnetometer + gyro data in engineering units | T | Pending |
| IT-004 | OBC + GNSS | Position fix acquisition | Valid fix < 60s from cold start | T | Pending |
| IT-005 | OBC + Camera | Image capture and storage | Image saved to SD card, retrievable via cmd | T | Pending |
| IT-006 | EPS + Solar | MPPT tracking under lamp | Power point found within 5% of V_mpp | T | Pending |
| IT-007 | EPS + Battery | Charge/discharge cycle | CC-CV profile correct, cutoffs enforced | T | Pending |
| IT-008 | COMM + GS | End-to-end link (UHF) | Beacon decoded at GS, command uplinked | T | Pending |
| IT-009 | COMM + GS | End-to-end link (S-band) | Image data downlinked and reconstructed | T | Pending |
| IT-010 | Full stack | Flat-sat integration | All subsystems communicate on shared bus | T | Pending |
| IT-011 | OBC + ADCS | Detumble simulation (HITL) | Angular rates < 1 deg/s within 3 orbits | A/T | Pending |
| IT-012 | OBC + All | Safe mode entry/recovery | Autonomous safe mode on low voltage, recovery | T | Pending |

### 2.3 System-Level Tests

| Test ID | Description | Pass Criteria | Method | Status |
|---------|-------------|---------------|--------|--------|
| ST-001 | Full mission simulation (24h) | No anomalies, telemetry continuous | T/A | Pending |
| ST-002 | Orbit + power + thermal coupled sim | Energy balance positive over 24h | A | Pending |
| ST-003 | Communication pass simulation | > 95% packet success rate per pass | T | Pending |
| ST-004 | Safe mode stress test | 10 consecutive safe mode triggers, 100% recovery | T | Pending |
| ST-005 | Imaging mission scenario | Target acquired, image captured and downlinked | T | Pending |
| ST-006 | Long-duration soak (72h powered) | No memory leaks, no WDT resets, stable telemetry | T | Pending |
| ST-007 | EMC self-compatibility | No interference between subsystems | T | Pending |
| ST-008 | Mass properties verification | Mass < 4 kg, CG within CDS limits | I | Pending |
| ST-009 | Dimensional fit check | Fits in P-POD/deployer with > 0.5mm clearance | I | Pending |
| ST-010 | Deployment mechanism test | Antenna/panel deploy within 30s, 100% success (10 trials) | T | Pending |

### 2.4 Acceptance-Level Tests

| Test ID | Description | Pass Criteria | Method | Status |
|---------|-------------|---------------|--------|--------|
| AT-001 | Final functional test (pre-ship) | All subsystems operational | T | Pending |
| AT-002 | Deployer fit check | Smooth insertion/extraction, switch activation | I/T | Pending |
| AT-003 | Battery charge state verification | SOC = 30-50% for launch (per launcher req.) | I | Pending |
| AT-004 | Kill switch verification | All power off when switches depressed | T | Pending |
| AT-005 | RBF pin verification | Remove-Before-Flight pin disables TX | T | Pending |

## 3. Environmental Test Plan

### 3.1 Vibration Testing

Reference: GEVS-SE Rev. A (NASA), CDS Rev. 14

#### 3.1.1 Random Vibration (Qualification Level)

| Frequency (Hz) | PSD (g²/Hz) | Notes |
|----------------|-------------|-------|
| 20 | 0.026 | Start of spec |
| 20-50 | +6 dB/oct ramp | |
| 50-800 | 0.16 | Flat plateau |
| 800-2000 | -6 dB/oct ramp | |
| 2000 | 0.026 | End of spec |
| **Overall** | **14.1 g_rms** | **Per axis, 2 min/axis** |

#### 3.1.2 Sine Vibration (if required by launcher)

| Frequency Range | Level | Sweep Rate |
|-----------------|-------|-----------|
| 5-20 Hz | 1.25 g (0-pk) | 2 oct/min |
| 20-100 Hz | 2.5 g (0-pk) | 2 oct/min |

#### 3.1.3 Shock Spectrum (SRS)

| Frequency (Hz) | SRS Level (g) |
|-----------------|--------------|
| 100 | 20 |
| 1000 | 500 |
| 5000 | 1000 |
| 10000 | 1000 |

#### 3.1.4 Vibration Test Procedure

```
Pre-test:
  1. Low-level sine sweep (0.5g, 5-2000 Hz) -- record resonances
  2. Functional test (abbreviated)

Qualification:
  3. Random vibration X-axis (14.1 g_rms, 2 min)
  4. Low-level sine sweep -- compare resonances (shift < 5%)
  5. Random vibration Y-axis (14.1 g_rms, 2 min)
  6. Low-level sine sweep
  7. Random vibration Z-axis (14.1 g_rms, 2 min)
  8. Low-level sine sweep

Post-test:
  9. Full functional test
  10. Visual inspection (no loose fasteners, no damage)

Pass criteria:
  - No resonance frequency shift > 5%
  - Full functional pass
  - No visible damage or loose components
```

### 3.2 Thermal Vacuum (TVAC) Testing

Reference: ECSS-Q-ST-70-04C

#### 3.2.1 Test Profile

| Parameter | Protoflight Level |
|-----------|-------------------|
| Hot extreme | +70C (qual range) |
| Cold extreme | -30C (qual range) |
| Vacuum level | < 1e-5 mbar |
| Number of cycles | 4 (protoflight) |
| Dwell time per extreme | 2 hours minimum |
| Ramp rate | 1-3 C/min |
| Total test duration | ~48 hours |

#### 3.2.2 TVAC Test Procedure

```
Phase 1: Pump-down and Bakeout
  1. Install satellite on thermal plate in vacuum chamber
  2. Connect all telemetry monitoring harnesses
  3. Pump down to < 1e-5 mbar
  4. Bakeout at +50C for 8 hours (outgassing)
  5. Baseline functional test

Phase 2: Thermal Cycling (4 cycles)
  6. Ramp to hot extreme (+70C) at 2C/min
  7. Dwell 2 hours -- full functional test during dwell
  8. Ramp to cold extreme (-30C) at 2C/min
  9. Dwell 2 hours -- full functional test during dwell
  10. Repeat steps 6-9 for cycles 2-4

Phase 3: Thermal Balance
  11. Stabilize at +20C (thermal balance test point)
  12. Record all temperatures at steady state (drift < 1C/hr)
  13. Compare with thermal model predictions

Phase 4: Repressurization
  14. Final functional test in vacuum at ambient temp
  15. Slow repressurization with dry N2
  16. Post-test functional test at ambient

Pass criteria:
  - All functional tests pass at both extremes
  - Thermal model correlation within +/- 5C
  - No condensation or outgassing issues
  - Battery temp maintained > 0C by heater
```

### 3.3 EMC/EMI Testing

Reference: ECSS-E-ST-20-07C (EMC), MIL-STD-461G

| Test | Standard | Requirement | Notes |
|------|----------|-------------|-------|
| RE102 (radiated emissions) | MIL-STD-461G | Emissions below limits 10 kHz - 18 GHz | Protects GS and co-passengers |
| CE102 (conducted emissions) | MIL-STD-461G | Conducted on power lines < limits | EPS bus quality |
| Self-compatibility | Custom | No subsystem interferes with another | UHF RX during S-band TX |
| Antenna pattern (UHF) | Custom | Gain > -3 dBi over > 80% of sphere | Monopole verification |
| Antenna pattern (S-band) | Custom | Gain > 3 dBi within +/- 60 deg | Patch antenna boresight |

### 3.4 Mechanical Testing

| Test | Requirement | Method |
|------|-------------|--------|
| Mass measurement | < 4.0 kg | Precision scale (+/- 1g) |
| CG measurement | Within CDS limits | Multi-axis balance or pendulum |
| Dimensional check | 100x100x340.5mm +/- 0.1mm | CMM or calipers |
| Rail surface roughness | Ra < 1.6 um | Profilometer |
| Deployment test (antenna) | Deploys within 30s, 10/10 trials | Burn-wire trigger in ambient + TVAC |
| Deployment test (solar panel) | Deploys within 30s, 10/10 trials | Spring mechanism verification |

## 4. Test Procedure Template

### 4.1 Generic Test Procedure Format

```
+============================================================+
| TEST PROCEDURE: [Test ID] - [Test Name]                     |
+============================================================+
| Version: 1.0          | Date: YYYY-MM-DD                   |
| Author:               | Reviewer:                           |
+------------------------------------------------------------+
| OBJECTIVE:                                                  |
|   [What this test verifies]                                 |
|                                                             |
| PREREQUISITES:                                              |
|   [ ] Equipment list and calibration status                 |
|   [ ] Software version and configuration                    |
|   [ ] Environmental conditions (temp, humidity)             |
|   [ ] Safety briefing completed                             |
|                                                             |
| SETUP:                                                      |
|   1. [Setup step 1]                                         |
|   2. [Setup step 2]                                         |
|                                                             |
| PROCEDURE:                                                  |
|   Step | Action              | Expected Result | Actual    |
|   -----|---------------------|-----------------|-----------|
|   1    | [Action]            | [Expected]      | [Record]  |
|   2    | [Action]            | [Expected]      | [Record]  |
|                                                             |
| PASS/FAIL CRITERIA:                                         |
|   PASS: [All criteria met]                                  |
|   FAIL: [Any criterion not met] -> NCR (Non-Conformance)   |
|                                                             |
| SIGNATURES:                                                 |
|   Test Operator: _____________ Date: ________              |
|   Test Witness:  _____________ Date: ________              |
|   QA Approval:   _____________ Date: ________              |
+============================================================+
```

### 4.2 Example: Battery Charge Test Procedure

```
TEST PROCEDURE: IT-007 - Battery Charge/Discharge Cycle
----------------------------------------------------------
OBJECTIVE: Verify EPS charges battery in CC-CV profile with correct cutoffs

PREREQUISITES:
  [ ] Lab power supply (0-20V, 0-5A)
  [ ] Digital multimeter (calibrated)
  [ ] Thermal chamber (or ambient 22+/-3C)
  [ ] EPS board powered and telemetry active
  [ ] Battery at 30% SOC initial state

PROCEDURE:
  Step 1: Connect solar simulator input at V_mpp = 6V, I_sc = 1A
  Step 2: Monitor battery voltage via EPS telemetry (1 Hz logging)
  Step 3: Verify CC mode: charge current = 0.5C +/- 10% (1.7A +/- 0.17A)
  Step 4: Record transition to CV mode at V_cell = 4.15V +/- 0.05V
  Step 5: Verify charge termination at I_taper < 100mA
  Step 6: Verify final V_cell = 4.20V +/- 0.02V per cell
  Step 7: Apply load (2A). Verify discharge cutoff at V_cell = 3.0V +/- 0.05V
  Step 8: Verify load switch opens within 100ms of cutoff

PASS CRITERIA: All steps within tolerance, no overshoot, no oscillation
```

## 5. CI/CD Pipeline

### 5.1 Automated Test Stages

| Trigger | Tests Run | Timeout | Required to Pass |
|---------|----------|---------|-----------------|
| On push (any branch) | Unit tests, ruff lint, mypy type check | 5 min | Yes (for merge) |
| On PR to main | Full test suite + firmware build (arm-none-eabi-gcc) | 15 min | Yes |
| On merge to main | Full suite + coverage report + build artifacts | 20 min | Yes |
| On release tag | All above + documentation PDF generation | 30 min | Yes |
| Nightly (scheduled) | Extended soak tests (simulation 1000 orbits) | 2 hours | No (report only) |

### 5.2 Test Coverage Targets

| Module | Current Coverage | Target | Notes |
|--------|-----------------|--------|-------|
| CCSDS protocol | 92% | > 90% | Well-tested |
| ADCS algorithms | 85% | > 80% | Mathematical functions |
| EPS logic | 78% | > 80% | Needs more edge cases |
| Flight controller | 65% | > 70% | Complex state machine |
| Ground station | 55% | > 70% | UI testing is hard |
| **Overall** | **72%** | **> 70%** | **Meeting target** |

## 6. Test Schedule

| Phase | Activity | Duration | Dependencies |
|-------|----------|----------|-------------|
| Phase 1 | Unit + Integration SW tests | Months 1-6 | SW development |
| Phase 2 | Board-level functional testing | Months 4-8 | PCB fabrication |
| Phase 3 | Flat-sat integration | Months 7-10 | All boards available |
| Phase 4 | Environmental testing (vib + TVAC) | Months 10-12 | Assembled flight model |
| Phase 5 | EMC testing | Month 12 | After env tests |
| Phase 6 | Acceptance + deployer fit | Month 13 | Deployer available |
| Phase 7 | Pre-ship review + battery charge | Month 14 | All tests complete |

## 7. Non-Conformance Management

When a test fails:

1. **Document** the failure in a Non-Conformance Report (NCR)
2. **Analyze** root cause (5-Why analysis)
3. **Disposition**: Use-As-Is / Repair / Rework / Scrap
4. **Retest** after corrective action
5. **Close** NCR with evidence of successful retest

## 8. References

- ECSS-E-ST-10-02C: Space Engineering - Verification (2009)
- ECSS-E-ST-10-03C: Space Engineering - Testing (2012)
- ECSS-Q-ST-70-04C: Space Product Assurance - Thermal Testing (2008)
- ECSS-E-ST-20-07C: Electromagnetic Compatibility (2012)
- NASA GEVS-SE Rev. A: General Environmental Verification Standard
- MIL-STD-461G: Electromagnetic Interference Characteristics (2015)
- CubeSat Design Specification Rev. 14, Cal Poly SLO
