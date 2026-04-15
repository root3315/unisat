# Mass Budget (3U Configuration)

Reference: CubeSat Design Specification Rev. 14 (Cal Poly), ECSS-E-ST-10-02C (Verification), GEVS-SE Rev. A

## 1. Detailed Component Breakdown

### 1.1 Structure Subsystem

| Component | Part Number / Spec | Qty | Unit Mass (g) | Total (g) | MGA (%) | With Margin (g) |
|-----------|--------------------|-----|---------------|-----------|---------|-----------------|
| 3U Primary Structure | ISIS 3U Structure Kit | 1 | 280 | 280 | 5 | 294 |
| PC/104 Spacers (M3×40mm) | Custom AL6061-T6 | 8 | 3 | 24 | 5 | 25 |
| Rail Feet (anodized AL) | CDS Rev.14 compliant | 4 | 12 | 48 | 5 | 50 |
| Deployment Switch (kill) | Endurosat KS-01 | 2 | 5 | 10 | 5 | 11 |
| Solar Panel Hinges | Custom spring-loaded | 2 | 15 | 30 | 15 | 35 |
| Fasteners (M3 Ti) | DIN 912 Ti Grade 5 | 60 | 1.2 | 72 | 5 | 76 |
| Separation Springs | P-POD spec compliant | 4 | 2 | 8 | 5 | 8 |
| **Subtotal Structure** | | | | **472** | | **499** |

### 1.2 Electrical Power Subsystem (EPS)

| Component | Part Number / Spec | Qty | Unit Mass (g) | Total (g) | MGA (%) | With Margin (g) |
|-----------|--------------------|-----|---------------|-----------|---------|-----------------|
| EPS Board (PC/104) | Custom PCB, 4-layer | 1 | 85 | 85 | 10 | 94 |
| MPPT Controller IC | SPV1040 + passives | 3 | 2 | 6 | 10 | 7 |
| Battery Cell NCR18650B | Panasonic NCR18650B | 4 | 46.5 | 186 | 2 | 190 |
| Battery Holder + Tabs | Custom AL bracket | 1 | 35 | 35 | 10 | 39 |
| Battery PCM (protection) | Custom PCB | 1 | 12 | 12 | 10 | 13 |
| DC-DC Converters | TPS62130 (3.3V, 5V) | 3 | 3 | 9 | 10 | 10 |
| Load Switches | TPS22918 (8 ch) | 8 | 0.5 | 4 | 10 | 4 |
| Solar Cells (body mount) | Spectrolab UTJ | 5 | 8 | 40 | 5 | 42 |
| Solar Panel PCB (body) | FR4, 1mm | 5 | 18 | 90 | 5 | 95 |
| Deployable Solar Panel | 1-wing, GaAs cells | 1 | 65 | 65 | 10 | 72 |
| **Subtotal EPS** | | | | **532** | | **566** |

### 1.3 On-Board Computer (OBC)

| Component | Part Number / Spec | Qty | Unit Mass (g) | Total (g) | MGA (%) | With Margin (g) |
|-----------|--------------------|-----|---------------|-----------|---------|-----------------|
| OBC PCB (PC/104) | Custom, 6-layer | 1 | 45 | 45 | 10 | 50 |
| STM32F427VIT6 MCU | ARM Cortex-M4, 180MHz | 1 | 1.5 | 1.5 | 5 | 2 |
| FRAM (NV storage) | FM25V20A, 256KB | 2 | 0.5 | 1 | 5 | 1 |
| NOR Flash | W25Q128JV, 16MB | 2 | 0.5 | 1 | 5 | 1 |
| SD Card + Holder | 32GB Industrial | 1 | 4 | 4 | 5 | 4 |
| RTC Crystal | 32.768 kHz | 1 | 0.2 | 0.2 | 5 | 0.2 |
| Watchdog Timer IC | MAX6369 | 1 | 0.3 | 0.3 | 5 | 0.3 |
| Voltage Regulators | LDO, passives | - | - | 5 | 10 | 6 |
| Connectors (PC/104) | Samtec ESQ-120 | 2 | 6 | 12 | 5 | 13 |
| Misc passives | R, C, L, ESD, TVS | - | - | 8 | 15 | 9 |
| **Subtotal OBC** | | | | **78** | | **86** |

### 1.4 Communication Subsystem

| Component | Part Number / Spec | Qty | Unit Mass (g) | Total (g) | MGA (%) | With Margin (g) |
|-----------|--------------------|-----|---------------|-----------|---------|-----------------|
| UHF Transceiver Board | Custom (CC1125 based) | 1 | 55 | 55 | 10 | 61 |
| UHF PA (1W) | SKY65116-34 | 1 | 2 | 2 | 10 | 2 |
| UHF LNA + SAW filter | SPF5189Z + TA0968A | 1 | 3 | 3 | 10 | 3 |
| UHF Monopole Antenna | Tape-spring, NiTi | 1 | 12 | 12 | 10 | 13 |
| S-band Transmitter Board | Custom PCB | 1 | 60 | 60 | 15 | 69 |
| S-band PA (2W) | RFMD RFPA5522 | 1 | 5 | 5 | 10 | 6 |
| S-band Patch Antenna | Microstrip, FR4 | 1 | 30 | 30 | 10 | 33 |
| RF Cables + SMA conn | RG-178 + SMA | 4 | 5 | 20 | 10 | 22 |
| **Subtotal COMM** | | | | **187** | | **209** |

### 1.5 ADCS (Attitude Determination and Control)

| Component | Part Number / Spec | Qty | Unit Mass (g) | Total (g) | MGA (%) | With Margin (g) |
|-----------|--------------------|-----|---------------|-----------|---------|-----------------|
| ADCS Controller PCB | Custom, PC/104 | 1 | 40 | 40 | 10 | 44 |
| Magnetorquer (X, Y rods) | Custom air-core, 0.2 Am² | 2 | 30 | 60 | 10 | 66 |
| Magnetorquer (Z coil) | PCB-embedded, 0.1 Am² | 1 | 15 | 15 | 10 | 17 |
| Reaction Wheel Assembly | CubeWheel Small (3-axis) | 3 | 60 | 180 | 5 | 189 |
| RW Driver Electronics | Custom H-bridge | 3 | 8 | 24 | 10 | 26 |
| Magnetometer | HMC5883L (3-axis) | 1 | 2 | 2 | 5 | 2 |
| Sun Sensors (coarse) | Photodiode arrays | 6 | 3 | 18 | 10 | 20 |
| Gyroscope | BMI088 (3-axis) | 1 | 1 | 1 | 5 | 1 |
| **Subtotal ADCS** | | | | **340** | | **365** |

### 1.6 GNSS Subsystem

| Component | Part Number / Spec | Qty | Unit Mass (g) | Total (g) | MGA (%) | With Margin (g) |
|-----------|--------------------|-----|---------------|-----------|---------|-----------------|
| GNSS Receiver | u-blox MAX-M10S | 1 | 2 | 2 | 5 | 2 |
| GNSS Patch Antenna | Taoglas CGGP.25.4.A.02 | 1 | 8 | 8 | 10 | 9 |
| LNA + SAW filter | - | 1 | 3 | 3 | 10 | 3 |
| Coax cable | RG-178 | 1 | 5 | 5 | 10 | 6 |
| **Subtotal GNSS** | | | | **18** | | **20** |

### 1.7 Payload Subsystem

| Component | Part Number / Spec | Qty | Unit Mass (g) | Total (g) | MGA (%) | With Margin (g) |
|-----------|--------------------|-----|---------------|-----------|---------|-----------------|
| Camera Module | OV5647 + optics (f=3.6mm) | 1 | 35 | 35 | 10 | 39 |
| Camera Lens Assembly | Custom 30m GSD @ 550km | 1 | 180 | 180 | 15 | 207 |
| Camera Interface Board | Custom MIPI-CSI adapter | 1 | 20 | 20 | 10 | 22 |
| Radiation Sensor | RADFET + dosimeter PCB | 1 | 45 | 45 | 10 | 50 |
| Radiation Shielding | AL 2mm local shield | 1 | 80 | 80 | 10 | 88 |
| IoT Relay Payload | LoRa SX1276 + ant | 1 | 25 | 25 | 15 | 29 |
| **Subtotal Payload** | | | | **385** | | **435** |

### 1.8 Thermal Control

| Component | Part Number / Spec | Qty | Unit Mass (g) | Total (g) | MGA (%) | With Margin (g) |
|-----------|--------------------|-----|---------------|-----------|---------|-----------------|
| MLI Blanket (5-layer) | Kapton + Mylar | 2 | 15 | 30 | 10 | 33 |
| Kapton Film Heater (1W) | Minco HK5578 | 2 | 5 | 10 | 10 | 11 |
| Thermistors (10kOhm NTC) | Vishay NTCS0402E3 | 12 | 0.1 | 1.2 | 10 | 1.3 |
| Thermal Interface Material | Bergquist GP5000S35 | - | - | 8 | 10 | 9 |
| Thermal Washers + Isolators | Ultem spacers | 8 | 1 | 8 | 10 | 9 |
| **Subtotal Thermal** | | | | **57** | | **63** |

### 1.9 Wire Harness

| Component | Part Number / Spec | Qty | Unit Mass (g) | Total (g) | MGA (%) | With Margin (g) |
|-----------|--------------------|-----|---------------|-----------|---------|-----------------|
| PC/104 Stack Connectors | Samtec ESQ-series | 6 | 6 | 36 | 5 | 38 |
| Internal cables (AWG28) | Teflon insulated | 15 | 3 | 45 | 15 | 52 |
| Antenna deploy mechanism | Burn wire + dyneema | 2 | 8 | 16 | 10 | 18 |
| Debug/JTAG connector | 10-pin Cortex | 1 | 2 | 2 | 5 | 2 |
| Misc (tie wraps, tape) | Kapton tape, lacing cord | - | - | 12 | 20 | 14 |
| **Subtotal Harness** | | | | **111** | | **124** |

## 2. Mass Budget Summary

| Subsystem | CBE Mass (g) | MGA Average (%) | MEV Mass (g) |
|-----------|-------------|-----------------|--------------|
| Structure | 472 | 5.7% | 499 |
| EPS (incl. battery + solar) | 532 | 6.4% | 566 |
| OBC | 78 | 10.3% | 86 |
| COMM | 187 | 11.8% | 209 |
| ADCS | 340 | 7.4% | 365 |
| GNSS | 18 | 11.1% | 20 |
| Payload | 385 | 13.0% | 435 |
| Thermal | 57 | 10.5% | 63 |
| Harness | 111 | 11.7% | 124 |
| **Total** | **2,180** | **8.5% avg** | **2,367** |

```
CBE  = Current Best Estimate (measured or datasheet values)
MGA  = Mass Growth Allowance (per AIAA S-120A-2015)
MEV  = Maximum Expected Value = CBE * (1 + MGA)
```

| Parameter | Value |
|-----------|-------|
| CBE Dry Mass | 2,180 g |
| MEV Dry Mass (CBE + MGA) | 2,367 g |
| System Margin (20% on MEV) | 473 g |
| **Total Allocation** | **2,840 g** |
| CubeSat 3U Mass Limit | 4,000 g |
| **Remaining Unallocated** | **1,160 g (29.0%)** |

### 2.1 Mass Growth Allowance Tracking

Per AIAA S-120A-2015, MGA depends on design maturity:

| Design Phase | MGA Guideline | Project Status |
|--------------|---------------|----------------|
| Conceptual (SRR) | 25-35% | Complete |
| Preliminary (PDR) | 15-25% | Complete |
| **Detailed (CDR)** | **5-15%** | **Current** |
| As-Built (FRR) | 2-5% | Upcoming |
| Flight (measured) | 0% | - |

Current MGA average of 8.5% is consistent with CDR-level maturity. Components with > 10% MGA
are those still in prototype phase (camera lens, S-band, IoT payload).

## 3. Center of Mass Calculation

Coordinate system: X = along long axis (from -Z face to +Z face), Y = lateral, Z = normal to largest face.
Origin at geometric center of the 3U envelope (50mm x 50mm x 170mm from P-POD rails).

### 3.1 Component Positions and CG Contributions

| Subsystem | Mass (g) | X_cg (mm) | Y_cg (mm) | Z_cg (mm) |
|-----------|----------|-----------|-----------|-----------|
| Structure | 472 | 0.0 | 0.0 | 0.0 |
| EPS Board | 346 | -50.0 | 0.0 | 0.0 |
| Battery Pack | 186 | -50.0 | 0.0 | -15.0 |
| OBC | 78 | -20.0 | 0.0 | 0.0 |
| COMM | 187 | 10.0 | 0.0 | 5.0 |
| ADCS | 340 | 50.0 | 0.0 | 0.0 |
| GNSS | 18 | 40.0 | 15.0 | 20.0 |
| Payload (Camera) | 235 | -60.0 | 0.0 | -20.0 |
| Payload (Rad+IoT) | 150 | 20.0 | 0.0 | 10.0 |
| Thermal | 57 | 0.0 | 0.0 | 0.0 |
| Harness | 111 | 0.0 | 0.0 | 0.0 |

### 3.2 Aggregate Center of Mass

```
X_cg = SUM(m_i * x_i) / SUM(m_i)
     = (472*0 + 346*(-50) + 186*(-50) + 78*(-20) + 187*10 + 340*50
        + 18*40 + 235*(-60) + 150*20 + 57*0 + 111*0) / 2180
     = (-17300 - 9300 - 1560 + 1870 + 17000 + 720 - 14100 + 3000) / 2180
     = -19670 / 2180
     = -9.0 mm

Y_cg = (18*15) / 2180 = 0.12 mm  (essentially centered)

Z_cg = (186*(-15) + 187*5 + 18*20 + 235*(-20) + 150*10) / 2180
     = (-2790 + 935 + 360 - 4700 + 1500) / 2180
     = -4695 / 2180
     = -2.2 mm
```

**CG Location: (-9.0, 0.1, -2.2) mm from geometric center**

CDS Rev. 14 Requirement: CG must be within 2 cm of geometric center in X and 1 cm in Y, Z.
Status: **COMPLIANT** (9.0 mm < 20 mm in X, 0.1 mm < 10 mm in Y, 2.2 mm < 10 mm in Z)

## 4. Moments of Inertia Estimate

Using parallel axis theorem for each component modeled as a rectangular prism:

```
I = I_cm + m * d²
```

Where I_cm is the moment about the component's own center and d is the distance to the satellite CG.

### 4.1 Principal Moments of Inertia

| Axis | Moment of Inertia (kg*m²) | Ratio |
|------|--------------------------|-------|
| I_xx (roll, along long axis) | 0.0027 | 1.00 |
| I_yy (pitch) | 0.0089 | 3.30 |
| I_zz (yaw) | 0.0092 | 3.41 |

Products of inertia are small (< 5e-5 kg*m²) due to near-symmetric layout.

The near-equality of I_yy and I_zz with I_xx being smallest confirms the 3U elongated shape.
This is favorable for gravity-gradient stabilization as a backup to active ADCS.

### 4.2 Inertia Requirements for ADCS Sizing

The magnetorquer authority must satisfy:

```
tau_max = M_dipole * B_earth  >  3 * (I_max / T_orbit) * omega_max

Where:
  M_dipole = 0.2 Am² (per axis)
  B_earth  = 30 uT (at 550 km, minimum)
  tau_max  = 0.2 * 30e-6 = 6.0e-6 Nm

  Required: 3 * (0.0092 / 5742) * 0.1 rad/s = 4.8e-7 Nm

  Margin: 6.0e-6 / 4.8e-7 = 12.5x   --> ADEQUATE
```

## 5. Mass Contingency and Risk

| Risk | Impact (g) | Mitigation |
|------|-----------|------------|
| Camera lens heavier than estimated | +50 | Lighter optics material (Ultem vs. glass) |
| Additional radiation shielding needed | +100 | Spot shielding only, accept higher dose |
| S-band antenna redesign (higher gain) | +30 | Trade study: gain vs. mass |
| Harness routing longer than planned | +30 | Strict harness routing plan |
| Thermal design margin | +20 | Optimize MLI coverage |
| **Total contingency** | **+230** | Within unallocated margin (1,160 g) |

## 6. References

- CubeSat Design Specification (CDS) Rev. 14, Cal Poly SLO, 2020
- AIAA S-120A-2015: Mass Properties Control for Space Systems
- ECSS-E-ST-10-02C: Space Engineering - Verification (2009)
- GEVS-SE Rev. A: General Environmental Verification Standard, NASA
