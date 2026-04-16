# Assembly Guide

Reference: ECSS-Q-ST-70C (Materials and Processes), IPC-A-610 (Acceptability of Electronic Assemblies), CDS Rev. 14

## 1. Safety and ESD Precautions

**CRITICAL: Electrostatic Discharge (ESD) can permanently damage flight hardware.**

| Requirement | Standard |
|-------------|----------|
| ESD wrist strap | Required at all times when handling PCBs |
| ESD mat (grounded) | Required on work surface |
| Humidity | 40-60% RH (ideal), never below 30% |
| Ionizer | Recommended near soldering station |
| ESD bags | Store all boards in pink anti-static bags when not in use |
| Personnel grounding | Touch grounded metal before handling boards |

**Cleanroom requirements:** ISO Class 8 (100,000 particles/ft³) minimum. If no cleanroom available, use a clean bench with HEPA filter and lint-free wipes.

## 2. Required Tools and Materials

### 2.1 Tools

| Tool | Specification | Purpose |
|------|---------------|---------|
| Soldering station | Hakko FX-951 or equivalent, temp-controlled | PCB assembly |
| Solder tips | Conical 0.4mm, chisel 1.6mm | Fine pitch + power |
| Solder wire | Sn63/Pb37, 0.5mm, flux core (or SAC305 for Pb-free) | Joints |
| Flux pen | No-clean RMA flux | Rework |
| Solder wick | 1.5mm copper braid | Desoldering |
| Torque driver | Wiha TorqueVario-S, 0.1-0.6 Nm | M3 fasteners |
| Hex bits | 2.0mm, 2.5mm | M3 socket head |
| Tweezers | ESD-safe, fine tip (Erem 2ASASL) | SMD components |
| Multimeter | Fluke 87V or equivalent | Electrical test |
| Oscilloscope | 100 MHz, 2-ch minimum | Signal debug |
| USB microscope | 20-200x magnification | Solder inspection |
| Wire stripper | For AWG28-30 | Harness |
| Crimping tool | JST-XH, Molex Picoblade | Connectors |
| Heat gun | 200-400°C adjustable | Heat shrink, rework |
| Isopropyl alcohol | 99%+ IPA | PCB cleaning |
| Lint-free wipes | Texwipe TX714 or equivalent | Cleaning |

### 2.2 Torque Specifications

| Fastener | Torque (Nm) | Thread Locker | Notes |
|----------|-------------|---------------|-------|
| M3×6 (PCB standoff) | 0.30 | Loctite 222 (purple) | Do not overtighten PCBs |
| M3×8 (structure) | 0.40 | Loctite 222 | Frame assembly |
| M3×12 (through-stack) | 0.40 | Loctite 222 | PC/104 stack |
| M3×40 (rail bolts) | 0.50 | Loctite 243 (blue) | CDS rail fasteners |
| M2.5 (antenna hinge) | 0.20 | None | Must be removable |
| SMA connector | 0.56 | None | Use torque wrench |

## Assembly Order

### Phase 1: Board Preparation
1. Populate OBC board (STM32F446RE, passives, connectors)
2. Populate EPS board (SPV1040, MOSFETs, inductors)
3. Populate COMM board (CC1125 + matching network)
4. Flash firmware via SWD: `./scripts/flash_stm32.sh`

### Phase 2: Battery Pack
1. Spot-weld 4× NCR18650B cells in 4S1P configuration
2. Add BMS protection board
3. Attach thermistor to center cell
4. Test: voltage should read 14.4-16.8V

### Phase 3: Solar Panel Integration
1. Solder solar cells to PCB (handle with care — fragile)
2. Connect panels to EPS board via JST connectors
3. Test MPPT under lamp: should show charging current

### Phase 4: Sensor Integration
1. Mount LIS3MDL, BME280, TMP117 on sensor board
2. Connect I2C bus (SDA/SCL with 4.7k pull-ups)
3. Mount MPU9250, connect SPI bus
4. Mount sun sensor photodiodes on each face
5. Run sensor self-test: `Sensors_SelfTest()`

### Phase 5: ADCS Assembly
1. Wind magnetorquer coils (200 turns each, 0.2mm wire)
2. Mount reaction wheels with brushless motors
3. Calibrate magnetometer (rotate 360° on each axis)

### Phase 6: Final Assembly
1. Stack all PCBs with M3 spacers (8mm gap)
2. Mount in CubeSat frame
3. Deploy antennas (verify mechanism)
4. Final electrical test (all buses, all sensors)
5. Vibration test (if available)

## 4. Integration Test After Each Phase

| Phase | Test | Expected Result | PASS/FAIL |
|-------|------|-----------------|-----------|
| 1 | Power OBC, check LED blink | 1 Hz heartbeat on PC13 | |
| 1 | SWD connect, read WHO_AM_I | STM32 responds | |
| 2 | Measure pack voltage | 14.4-16.8V | |
| 2 | Charge at 0.5C, verify cutoff | Stops at 16.8V | |
| 3 | Illuminate panel, measure MPPT output | Current > 0 | |
| 4 | Run `Sensors_SelfTest()` | All sensors OK | |
| 4 | I2C scan | 4 devices found (0x1C, 0x42, 0x48, 0x76) | |
| 5 | Command detumble mode | Magnetorquers activate | |
| 5 | Spin test on air bearing | Angular rates decrease | |
| 6 | Beacon TX, receive on SDR | CCSDS packets decoded | |
| 6 | Fit in deployer mockup | Slides freely, switches activate | |

## 5. Common Mistakes to Avoid

1. **Reversed battery polarity** — Always verify with multimeter before connecting
2. **Overtorqued PCB screws** — PCBs crack at > 0.4 Nm on M3
3. **Cold solder joints** — Use proper temperature (350°C for leaded, 380°C for SAC305)
4. **Missing pull-ups on I2C** — Check 4.7k on SDA/SCL before power-on
5. **SPI CS lines floating** — Add 10k pull-up to each CS line
6. **Antenna deploy before 30 min** — CDS requires 30 min wait after separation
7. **No strain relief on harness** — Use Kapton tape at cable exits
8. **Contamination on solar cells** — Handle with gloves, clean with IPA before closing

## 6. Pre-Close Checklist (Before Sealing in Frame)

- [ ] All PCB standoffs torqued to spec with thread locker
- [ ] All cable connectors seated and strain-relieved
- [ ] No loose wires or solder balls (inspect under microscope)
- [ ] Battery charged to 30-50% SOC (launch requirement)
- [ ] Kill switches functional (both depressed = power off)
- [ ] RBF (Remove Before Flight) pin installed
- [ ] Antenna stowed with burn wire intact
- [ ] Thermal interface pads applied between battery and structure
- [ ] Photos taken of each assembly step for documentation

## 7. Post-Close Acceptance Test

- [ ] All sensors responding via telemetry
- [ ] Battery charging from solar simulator
- [ ] UHF beacon transmitting (verify with SDR)
- [ ] GNSS acquiring fix (outdoor or simulator)
- [ ] Camera capturing and storing images
- [ ] Safe mode triggers on low voltage simulation
- [ ] Reaction wheels spin up and down
- [ ] Magnetorquers produce measurable field
- [ ] Mass < 4.0 kg on calibrated scale
- [ ] Dimensions within CDS envelope (measure 3 axes)
- [ ] Center of mass within 2 cm of geometric center
