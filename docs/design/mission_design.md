# Mission Design

Reference: ECSS-M-ST-10C (Project Planning), ECSS-E-ST-10C (System Engineering), CubeSat Design Specification Rev. 14

## 1. Mission Objectives

### 1.1 Primary Objectives

| ID | Objective | Success Metric | Priority |
|----|-----------|----------------|----------|
| MO-1 | Demonstrate modular CubeSat platform (1U-6U) | Platform operates nominally for > 6 months | Essential |
| MO-2 | Earth observation with multispectral imaging | >= 10 images at 30m GSD downlinked | Essential |
| MO-3 | Radiation environment monitoring (LEO) | Continuous dose rate data for > 3 months | Essential |
| MO-4 | IoT message relay demonstration | >= 100 messages relayed | Desired |
| MO-5 | Technology validation for ADCS subsystem | 3-axis stabilization to < 1 deg accuracy | Essential |
| MO-6 | Technology validation for EPS subsystem | MPPT efficiency > 90%, autonomous power management | Essential |

### 1.2 Mission Success Criteria

| Level | Definition | Criteria |
|-------|-----------|----------|
| Minimum Success | Basic platform operation | Beacon received, TM downlinked, ADCS detumbled (MO-1 partial) |
| Partial Success | Primary payload operates | At least 1 image + 1 month radiation data (MO-2, MO-3 partial) |
| Full Success | All primary objectives met | MO-1 through MO-6 fully achieved over 12 months |
| Extended Success | Beyond design life | Operations continue past 24 months |

## 2. Requirements Traceability Matrix (RTM)

### 2.1 Mission-to-System Requirements

| Mission Req. | System Requirement | Subsystem | Verification | Status |
|-------------|-------------------|-----------|-------------|--------|
| MO-1 | SYS-01: Operate for >= 2 years in LEO | All | A/T | Open |
| MO-1 | SYS-02: Mass < 4.0 kg (3U) | Structure | I | Open |
| MO-1 | SYS-03: Fit in standard 3U deployer | Structure | I | Open |
| MO-2 | SYS-04: GSD <= 30 m at nadir | Camera | A/T | Open |
| MO-2 | SYS-05: >= 10 images downlinked in 6 months | COMM, Camera | T | Open |
| MO-2 | SYS-06: Pointing accuracy < 1 deg (3-axis) | ADCS | T | Open |
| MO-3 | SYS-07: Radiation dose measurement 0.01-100 mGy/day | Payload | T | Open |
| MO-3 | SYS-08: Radiation data stored onboard >= 30 days | OBC | A/T | Open |
| MO-4 | SYS-09: Relay LoRa messages within footprint | Payload | T | Open |
| MO-5 | SYS-10: Detumble from 10 deg/s to < 0.5 deg/s in 3 orbits | ADCS | A/T | Open |
| MO-5 | SYS-11: 3-axis pointing with RW, < 1 deg accuracy | ADCS | A/T | Open |
| MO-6 | SYS-12: Positive energy balance in nominal mode | EPS | A | Open |
| MO-6 | SYS-13: Autonomous safe mode on low power | EPS, OBC | T | Open |

### 2.2 System-to-Subsystem Requirements

| System Req. | Subsystem Req. | Allocated To | Spec Value |
|-------------|---------------|-------------|-----------|
| SYS-04 | CAM-01: Focal length >= 50 mm | Camera | f = 50 mm |
| SYS-04 | CAM-02: Sensor >= 5 MP | Camera | OV5647, 2592x1944 |
| SYS-04 | ADCS-01: Pointing knowledge < 0.5 deg | ADCS | Sun sensor + magnetometer |
| SYS-05 | COMM-01: S-band downlink >= 256 kbps | COMM | QPSK, LDPC r=1/2 |
| SYS-05 | COMM-02: >= 4 usable GS passes/day | COMM | Tashkent, 10 deg min el. |
| SYS-06 | ADCS-02: Reaction wheels >= 1 mNm torque | ADCS | 3x CubeWheel |
| SYS-10 | ADCS-03: Magnetorquer dipole >= 0.2 Am^2 | ADCS | Air-core rods |
| SYS-12 | EPS-01: Solar generation >= 5 W (orbit avg, EOL) | EPS | GaAs + deployable |
| SYS-12 | EPS-02: Battery capacity >= 25 Wh usable (EOL) | EPS | 4S1P NCR18650B |
| SYS-13 | OBC-01: Safe mode entry < 10 seconds | OBC | Autonomous watchdog |

## 3. Concept of Operations (CONOPS)

### 3.1 Mission Timeline

```
Day     Phase              Key Activities
-----   ---------          --------------------------------
  0     LAUNCH             Separation from deployer
  0     LEOP               Antenna deployment (30 min timer)
                           Kill switch release
                           First beacon TX
 0-1    DETUMBLE           B-dot detumbling (magnetorquers)
                           First GS pass, telemetry reception
 1-3    COMMISSIONING-1    Subsystem checkout (EPS, OBC, COMM)
                           GNSS first fix
                           Solar panel deployment
 3-7    COMMISSIONING-2    ADCS calibration (mag + sun sensors)
                           Camera first light
                           S-band link verification
 7-14   EARLY OPS          First science images
                           Radiation sensor activation
                           IoT payload commissioning
 14+    NOMINAL OPS        Routine science operations
                           Weekly imaging campaigns
                           Continuous radiation monitoring
 12 mo  MID-LIFE REVIEW    Performance assessment
                           Orbit maintenance decision
 24 mo  END OF LIFE        Passivation (battery discharge)
                           Transponder off
                           Natural deorbit begins
```

### 3.2 Nominal Operations Concept

```
Per-Orbit Activity Timeline (95.7 min orbit):

Time(min) Activity              Power Mode       Notes
--------  ---------             ----------       -----
  0:00    Eclipse entry         ECLIPSE_STANDBY  Heater active if needed
  0:00    Radiation monitoring  NOMINAL          Continuous background
 15:00    GNSS fix attempt      NOMINAL          Update orbit state
 33:30    Eclipse exit          NOMINAL          Solar charging resumes
 40:00    ADCS pointing (if scheduled) SCIENCE   Point at target
 42:00    Image capture         SCIENCE          3 sec exposure
 43:00    ADCS return to nadir  NOMINAL          Default orientation
 50:00    GS pass (if visible)  COMM             UHF TM + S-band data
 58:00    GS pass ends          NOMINAL          Resume standby
 62:00    Housekeeping TM store NOMINAL          Log to SD card
 95:42    Orbit complete        --               Next orbit begins
```

### 3.3 Ground Segment Operations

| Activity | Frequency | Duration | Personnel |
|----------|-----------|----------|-----------|
| Automated beacon monitoring | Continuous | - | 0 (automated) |
| Scheduled TM downlink pass | 4-6 per day | 8-12 min each | 1 operator |
| Command uplink session | 1-2 per day | 5 min | 1 operator + 1 reviewer |
| Science planning | Weekly | 2 hours | 1 scientist + 1 operator |
| Orbit determination update | Daily | 30 min | Automated (GNSS) |
| Anomaly response | As needed | Variable | 2+ personnel |

## 4. Orbit Selection Rationale

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Type | Sun-Synchronous (SSO) | Consistent lighting for imaging, thermal stability |
| Altitude | 550 km | Balance: 30m GSD achievable, 7-22 year deorbit |
| Inclination | 97.59 deg | SSO requirement for 550 km |
| LTAN | 10:30 | Morning crossing: low cloud cover, good illumination angle |
| Expected Lifetime | 2 years (nominal), 5+ years (possible) | Atmospheric drag at 550 km |
| Orbital Period | 95.7 min | ~15 orbits/day |

### 4.1 Altitude Trade Study

| Altitude | GSD | Deorbit (yr) | Eclipse (min) | Link Margin | Selected |
|----------|-----|-------------|---------------|-------------|----------|
| 400 km | 23 m | 2-5 | 36 | +16 dB UHF | No (short life) |
| 500 km | 29 m | 5-12 | 35 | +14 dB UHF | No (marginal GSD) |
| **550 km** | **32 m** | **7-22** | **34** | **+14 dB UHF** | **Yes** |
| 600 km | 35 m | 12-30 | 33 | +13 dB UHF | No (exceeds 25yr) |
| 700 km | 40 m | 50+ | 31 | +12 dB UHF | No (debris risk) |

## 5. Risk Register

### 5.1 Technical Risks

| ID | Risk | Likelihood | Impact | Risk Level | Mitigation |
|----|------|-----------|--------|-----------|------------|
| R-01 | ADCS fails to detumble | Low | High | Medium | B-dot algorithm tested in HITL; magnetorquers oversized 10x |
| R-02 | Battery degradation exceeds model | Medium | High | High | Conservative DoD (15%), redundant cell monitoring, heater |
| R-03 | S-band link margin insufficient | Low | Medium | Low | Upgraded to 2.4m dish GS antenna; LDPC coding; fallback to UHF only |
| R-04 | Camera optics misalignment (vibration) | Medium | Medium | Medium | Epoxy-bonded lens; vibration test at qualification level |
| R-05 | Solar panel deployment failure | Low | Critical | Medium | Redundant burn wires; spring-loaded hinges; ground test >10 cycles |
| R-06 | Software crash / watchdog loop | Medium | Medium | Medium | Watchdog timer; safe mode fallback; flight-proven RTOS patterns |
| R-07 | Radiation-induced SEU (single event upset) | Medium | Low | Low | EDAC on memory; TMR on critical registers; periodic scrubbing |
| R-08 | Thermal violation (battery overheat) | Medium | High | High | Thermal isolators; heater control; duty-cycle limits in software |
| R-09 | Antenna fails to deploy | Low | Critical | Medium | Redundant deployment mechanism; 30-min timer + ground command backup |
| R-10 | GNSS fails to acquire fix in orbit | Low | Low | Low | Orbit propagator fallback (SGP4); TLE upload from ground |

### 5.2 Programmatic Risks

| ID | Risk | Likelihood | Impact | Mitigation |
|----|------|-----------|--------|------------|
| R-11 | Launch delay > 6 months | High | Medium | Flexible launch broker; multiple manifests |
| R-12 | Key personnel unavailable | Medium | Medium | Cross-training; documentation |
| R-13 | Budget overrun on GS equipment | Low | Low | Phased procurement; borrow equipment |
| R-14 | Frequency coordination delayed | Medium | High | Apply to IARU early; have backup frequencies |
| R-15 | Component obsolescence | Low | Medium | Maintain approved vendor list; buy spares early |

### 5.3 Risk Matrix

```
            Impact -->
            Negligible  Minor  Moderate  Major  Critical
  Very       |         |      |         |       |
  High       |         |      |         |       |
             +---------+------+---------+-------+---------
  High       |         | R-11 |         |       |
             +---------+------+---------+-------+---------
  Medium     |    R-07 | R-06 | R-04    | R-02  |
             |         | R-12 |  R-08   |       |
             +---------+------+---------+-------+---------
Likelihood   |    R-10 | R-13 | R-03    | R-01  | R-05
  Low        |         |      | R-14    |       | R-09
             +---------+------+---------+-------+---------
  Very       |         |      | R-15    |       |
  Low        |         |      |         |       |
             +---------+------+---------+-------+---------

Legend: Green = acceptable, Yellow = monitor, Red = mitigate actively
```

## 6. Launch Vehicle Interface

### 6.1 Deployer Compatibility

| Deployer | Vendor | Envelope | Mass Limit | Interface | Compatible |
|----------|--------|----------|-----------|-----------|------------|
| P-POD Mk III | Cal Poly | 3U (100x100x340.5mm) | 4.0 kg | Rail + spring | Yes |
| ISIPOD | ISIS | 3U (100x100x340.5mm) | 4.0 kg | Rail + spring | Yes |
| QuadPack | ISIS | 4x 3U | 4.0 kg each | Rail + spring | Yes |
| NRCSD | NanoRacks | 6U (can accommodate 3U) | 4.0 kg (3U) | Rail | Yes |

### 6.2 CDS Compliance Checklist

| Requirement | CDS Section | Status |
|-------------|-------------|--------|
| Maximum mass 4.0 kg | 3.2.1 | Compliant (2.84 kg with margin) |
| Dimensions 100x100x340.5 mm | 3.2.2 | To be verified (fit check) |
| Rail material: AL 7075 or equiv. | 3.2.4 | Compliant (AL 6061-T6, approved) |
| Rail surface finish Ra < 1.6 um | 3.2.5 | To be verified (profilometer) |
| CG within 2 cm of geometric center | 3.2.9 | Compliant (9mm offset) |
| No hazardous materials | 3.3.1 | Compliant (Li-ion qualified) |
| Deployment switches (2x) | 3.4.1 | Compliant (Endurosat KS-01) |
| Remove-Before-Flight pin | 3.4.2 | Compliant (RBF disables TX) |
| No RF emission before deployment | 3.4.3 | Compliant (30-min timer) |
| Battery charge state 30-50% at launch | 3.5.1 | Procedure in place |

### 6.3 Launch Environment (Generic LEO Rideshare)

| Parameter | Value | Source |
|-----------|-------|--------|
| Quasi-static acceleration | 6.5 g (axial), 2.0 g (lateral) | Launcher user manual |
| Random vibration | 14.1 g_rms (qualification) | GEVS-SE |
| Acoustic | 140 dB OASPL | Launcher user manual |
| Shock (separation) | 1000 g SRS at 1 kHz | Deployer spec |
| Thermal (pre-launch, fairing) | +10C to +40C | Launcher user manual |
| Depressurization rate | < 5 kPa/s | Launcher user manual |

## 7. Ground Segment Architecture

```
+--------------------+     Internet     +------------------+
|  Mission Control   |<================>| Data Processing  |
|  Center (MCC)      |                  | Server           |
|  - Pass planning   |                  | - TM archival    |
|  - Command gen.    |                  | - Image processing|
|  - Health monitor  |                  | - Science data   |
+--------+-----------+                  +------------------+
         |
         | LAN / VPN
         |
+--------v-----------+
|  Ground Station     |
|  Tashkent           |
|  - UHF Yagi + rotor |
|  - S-band dish       |
|  - SDR (USRP B210)  |
|  - GS software       |
|  - Auto-tracking     |
+--------+------------+
         |
         | RF (437 MHz / 2.4 GHz)
         |
    ~~~~~v~~~~~
    Satellite
    ~~~~~~~~~~~
```

### 7.1 Ground Station Equipment List

| Item | Model/Spec | Purpose |
|------|-----------|---------|
| UHF Antenna | 9-element cross Yagi, RHCP | TT&C link |
| S-band Antenna | 2.4m parabolic dish, RHCP | Science data downlink |
| Rotator | Yaesu G-5500 (Az/El) | Antenna tracking |
| SDR | Ettus USRP B210 (70MHz-6GHz) | Modem (TX/RX) |
| LNA (UHF) | NooElec SAWbird+ (NF=0.5dB) | Signal amplification |
| LNA (S-band) | Custom (NF=0.7dB, G=25dB) | Signal amplification |
| PA (UHF uplink) | 4W, 430-440 MHz | Command uplink |
| Computer | Linux workstation | GS software host |
| UPS | 1 kVA | Power backup |
| GPS Receiver | u-blox M8 | Time synchronization (UTC) |

## 8. Mission Phases Detailed

### 8.1 LEOP (Launch and Early Orbit Phase) -- Days 0-1

| Event | Time After Deploy | Automated | Action |
|-------|-------------------|-----------|--------|
| Separation from deployer | T+0 | Yes | Kill switches release |
| Deployment timer starts | T+0 | Yes | 30-min wait (CDS req.) |
| Battery check | T+1 min | Yes | Verify SOC > 20% |
| OBC boot sequence | T+1 min | Yes | Load flight config |
| Antenna deployment | T+30 min | Yes | Burn-wire activation |
| First beacon TX | T+31 min | Yes | UHF beacon at 0.1 Hz |
| ADCS sensors ON | T+32 min | Yes | Magnetometer + gyro |
| B-dot detumble start | T+33 min | Yes | Magnetorquer control |
| First GS contact | T+1-8 hr | GS | TM reception, initial assessment |
| Detumble complete | T+3-5 hr | Yes | Angular rate < 0.5 deg/s |

### 8.2 Commissioning -- Days 1-14

| Day | Activity | Success Criterion |
|-----|----------|-------------------|
| 1-2 | EPS checkout: solar current, battery V/I/T | All values in expected range |
| 2-3 | COMM checkout: UHF link quality, S-band test | > 95% packet success, S-band sync |
| 3-4 | GNSS first fix, orbit determination | Position fix < 10m, velocity < 0.1 m/s |
| 4-5 | Solar panel deployment (if deployable) | Panel current increase confirmed |
| 5-6 | ADCS calibration: mag bias, sun sensor alignment | Residuals < 1% FS |
| 6-7 | ADCS pointing test: nadir lock | Pointing error < 5 deg |
| 7-8 | Camera first light (test image) | Image received and decoded |
| 8-10 | ADCS fine pointing (reaction wheels) | Pointing error < 1 deg |
| 10-12 | Payload commissioning (radiation, IoT) | Data received and validated |
| 12-14 | End-to-end mission rehearsal | Full imaging + downlink cycle |

## 9. Data Budget

### 9.1 Daily Data Generation

| Source | Rate | Daily Volume | Priority |
|--------|------|-------------|----------|
| OBC Housekeeping | 48 bytes/s | 4.1 MB | High |
| EPS Telemetry | 72 bytes/s | 6.2 MB | High |
| ADCS Attitude | 84 bytes/s | 7.3 MB | Medium |
| GNSS Position | 5 bytes/s | 0.4 MB | Low |
| COMM Status | 3 bytes/s | 0.3 MB | Low |
| Radiation Data | 0.3 bytes/s | 0.03 MB | Medium |
| Camera (2 images/day) | Burst | 6 MB | High |
| **Total daily generation** | | **~24 MB** | |

### 9.2 Daily Downlink Capacity

| Link | Passes/day | Per-pass Volume | Daily Total |
|------|-----------|----------------|-------------|
| UHF | 6 | 240 KB | 1.4 MB |
| S-band | 4 | 6.9 MB | 27.6 MB |
| **Total downlink** | | | **29.0 MB** |

**Margin: 29.0 / 24.0 = 1.21 (21% data margin)** -- adequate for nominal operations.
Onboard storage (32 GB SD) provides ~1,300 days of buffering at full rate.

## 10. References

- ECSS-M-ST-10C Rev. 1: Space Project Management - Project Planning and Implementation (2009)
- ECSS-E-ST-10C: Space Engineering - System Engineering General Requirements (2009)
- ECSS-E-ST-10-06C: Space Engineering - Technical Requirements Specification (2009)
- CubeSat Design Specification (CDS) Rev. 14, Cal Poly SLO, 2020
- Wertz, J.R., "Space Mission Engineering: The New SMAD", Microcosm Press, 2011
- Maral, G. and Bousquet, M., "Satellite Communications Systems", Wiley, 6th Ed.
- NASA Systems Engineering Handbook, NASA SP-2016-6105 Rev. 2
