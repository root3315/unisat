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

## 3. Assembly Sequence Overview

```
Phase 1        Phase 2        Phase 3        Phase 4        Phase 5        Phase 6
PCB POPULATE   BATTERY PACK   SOLAR PANELS   SENSORS +      ADCS           FINAL
& FLASH FW     ASSEMBLY       INTEGRATION    PAYLOAD        ASSEMBLY       INTEGRATION
  |              |              |              |              |              |
  v              v              v              v              v              v
┌────────┐   ┌────────┐   ┌────────┐   ┌────────┐   ┌────────┐   ┌────────┐
│ OBC    │   │ 4S1P   │   │ Solder │   │ I2C:   │   │ Wind   │   │ Stack  │
│ EPS    │   │ NCR186 │   │ GaAs   │   │ LIS3MDL│   │ MTQ    │   │ all    │
│ COMM   │   │ 50B    │   │ cells  │   │ BME280 │   │ coils  │   │ PCBs   │
│ boards │   │ + BMS  │   │ to PCB │   │ TMP117 │   │ Mount  │   │ into   │
│        │   │        │   │        │   │ SPI:   │   │ react. │   │ 3U     │
│ Flash  │   │ Test   │   │ Test   │   │ MPU9250│   │ wheels │   │ frame  │
│ via SWD│   │ 14.4-  │   │ MPPT   │   │ Sun    │   │        │   │        │
│        │   │ 16.8V  │   │ output │   │ sensors│   │ Cal.   │   │ Close  │
└────────┘   └────────┘   └────────┘   └────────┘   └────────┘   └────────┘
  TEST         TEST          TEST         TEST         TEST         ACCEPT
  WHO_AM_I     V/I/T         Isolar>0     SelfTest()   B-dot spin   Full TM
```

### Phase 1: PCB Population and Firmware Flash

**OBC Board (6-layer, PC/104 form factor):**

1. Apply solder paste to pads using stencil (0.12 mm thickness)
2. Place STM32F446RE (LQFP-64) using alignment marks. Verify pin 1 orientation
3. Place passive components: decoupling caps (100 nF on each VDD), crystal (8 MHz HSE), RTC crystal (32.768 kHz)
4. Place FRAM (FM25V20A), NOR Flash (W25Q128JV), watchdog IC (MAX6369)
5. Place PC/104 connectors (Samtec ESQ-120)
6. Reflow in oven: ramp 1.5 C/s to 150 C (soak 60 s), peak 245 C (leaded) or 260 C (SAC305), dwell < 10 s
7. Inspect under microscope: check for bridges on STM32 pins, tombstoned passives
8. Hand-solder through-hole connectors (JST-XH, SWD header, UART debug)
9. Clean with IPA and lint-free wipe. Dry with compressed air

**EPS Board (4-layer):**

1. Same paste-and-reflow process as OBC
2. Key components: 3x SPV1040 MPPT ICs, TPS62130 buck converters (3.3 V, 5 V), TPS22918 load switches (8 channels)
3. Hand-solder power MOSFETs and inductors (high current paths)
4. Verify no solder bridges on QFN pads (inspect with microscope from side)

**COMM Board:**

1. Place CC1125 RF transceiver and matching network components
2. Critical: matching network values (L, C) must match calculated impedance. Use VNA to verify 50 ohm match at 437 MHz
3. Solder SMA connector for antenna (torque to 0.56 Nm with wrench)

**Firmware Flash:**

1. Connect ST-Link V2 to SWD header (SWDIO, SWCLK, GND, 3V3)
2. Run `./scripts/flash_stm32.sh` (uses OpenOCD to flash)
3. Verify: LED on PC13 blinks at 1 Hz (heartbeat)
4. Connect UART debug (115200 baud), verify boot messages

### Phase 2: Battery Pack Assembly

**SAFETY WARNING: Lithium-ion cells can catch fire if shorted, punctured, or overcharged. Wear safety glasses. Keep a Class D fire extinguisher within reach. Never leave cells unattended during charging.**

1. Inspect 4x Panasonic NCR18650B cells. Reject any with dents, scratches on wrap, or voltage < 3.0 V
2. Measure each cell voltage. Match within 50 mV (e.g., all between 3.60-3.65 V)
3. Place cells in 4S1P configuration in aluminum bracket holder
4. Spot-weld nickel strips (0.15 mm thick) for series connections. Verify weld strength (tug test > 2 N)
5. Solder BMS protection board to nickel strips. BMS provides: overcharge (4.25 V/cell), overdischarge (2.8 V/cell), overcurrent (5 A)
6. Attach 10k NTC thermistor to center cell with Kapton tape. Route wire to EPS connector
7. Apply thermal pad (1 mm silicone, 3 W/mK) to battery-structure interface
8. Test: measure pack voltage (expect 14.4-16.8 V depending on SOC)
9. Test: charge at 0.5 C (1.7 A) and verify BMS cuts off at 16.8 V (4.2 V/cell)
10. Test: verify BMS trips on simulated short (use electronic load at 6 A)

### Phase 3: Solar Panel Integration

**Solar Cell Soldering Procedure:**

Solar cells (Spectrolab UTJ, GaAs triple-junction) are extremely fragile. Handle by edges only with gloved hands. Never flex.

1. Pre-tin PCB pads with thin layer of Sn63/Pb37 solder (350 C)
2. Pre-tin back contact of solar cell (quick touch, < 2 seconds, 330 C to avoid cell damage)
3. Place cell on PCB pad, align with edge guides
4. Reflow connection using soldering iron at 330 C. Touch for < 3 seconds per joint
5. Solder front contact (tabbing wire to bus bar). Use minimum solder to avoid shadowing
6. Repeat for all cells on each panel (5 body-mounted + 1 deployable wing)
7. Test each panel individually under halogen lamp (100 W at 30 cm distance): expect V_oc ~2.6 V per cell, I_sc ~400 mA
8. Connect panels to EPS board via JST-XH connectors
9. Test MPPT under lamp: verify charging current flows to battery
10. Clean cell surfaces with IPA. Any fingerprints reduce efficiency

### Phase 4: Sensor Integration

1. Mount LIS3MDL magnetometer on sensor board at 0x1C. Verify orientation mark matches PCB silkscreen
2. Mount BME280 environmental sensor at 0x76. Ensure vent hole is not obstructed
3. Mount TMP117 precision temperature sensor at 0x48 near battery
4. Wire I2C bus: SDA, SCL with 4.7k pull-ups to 3.3 V. Keep traces short (< 10 cm)
5. Mount MPU9250 IMU via SPI (PA4 CS). Verify SPI Mode 0 clock polarity
6. Mount MCP3008 ADC for analog sensors (PA5 CS)
7. Mount 6x photodiode sun sensors (one per CubeSat face). Connect to MCP3008 channels
8. Mount SBM-20 Geiger-Muller tube for radiation payload. Connect to TIM2 counter input
9. Mount u-blox GNSS receiver on I2C at 0x42. Antenna on +Z face (zenith)
10. Run sensor self-test: `Sensors_SelfTest()` -- returns OK for each sensor
11. Run I2C scan: verify 4 devices found at 0x1C, 0x42, 0x48, 0x76

### Phase 5: ADCS Assembly

1. Wind 3 magnetorquer coils: 200 turns of 0.2 mm enameled copper wire on each bobbin
2. Expected dipole moment: ~0.2 Am^2 at 200 mA drive current
3. Verify each coil resistance: expect 8-12 ohm (test with multimeter)
4. Mount coils orthogonally (X, Y, Z body axes) in CubeSat frame recesses
5. Mount 3 reaction wheel assemblies (brushless DC motor + flywheel)
6. Connect motor drivers to EPS 5 V rail and OBC PWM outputs
7. Spin test each wheel: command 1000 RPM, verify with tachometer
8. Calibrate magnetometer: rotate satellite 360 deg on each axis, record min/max. Compute hard-iron offset and soft-iron matrix

### Phase 6: Final Assembly

```
Assembly Stack (side view):

  +Z (zenith) ─── GNSS antenna + sun sensor
  ┌──────────────────────────────┐
  │        COMM Board            │ ← UHF antenna folded on exterior
  │  CC1125 + SMA connector      │
  ├──────────────────────────────┤ ← 8 mm M3 spacers
  │        OBC Board             │ ← STM32, FRAM, Flash, debug header
  │  Main processor + memory     │
  ├──────────────────────────────┤ ← 8 mm M3 spacers
  │        Sensor Board          │ ← Magnetometer, IMU, env. sensors
  │  + Payload (SBM-20)         │
  ├──────────────────────────────┤ ← 8 mm M3 spacers
  │        EPS Board             │ ← MPPT, charger, load switches
  │  + Battery Pack (4S1P)      │
  └──────────────────────────────┘
  -Z (nadir) ─── Camera lens + 2x kill switches + RBF pin

  Total internal height: ~85 mm (leaves margin in 3U frame)
```

1. Stack all PCBs using M3 x 40 mm standoffs. Torque to 0.40 Nm with Loctite 222
2. Route all inter-board harnesses. Apply strain relief with Kapton tape at each connector
3. Mount stack in 3U aluminum frame (ISIS 3U Structure Kit)
4. Secure with M3 rail bolts. Torque to 0.50 Nm with Loctite 243 (blue)
5. Mount antenna deployment mechanism on +X face. Verify burn wire is intact
6. Mount deployable solar panel on hinge mechanism. Verify spring tension
7. Install kill switches on -Z face. Verify: both depressed = all power off
8. Install RBF (Remove Before Flight) pin on +Z face
9. Run full electrical test: all buses, all sensors, all subsystems
10. Perform fit check in P-POD mockup: slides freely, switches activate on insertion

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
