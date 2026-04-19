# Thermal Analysis

Reference: ECSS-E-ST-31C (Thermal Control), ECSS-Q-ST-70-04C (Thermal Testing), NASA-STD-7009A

## 1. Thermal Environment Definition

### 1.1 External Heat Sources

| Source | Nominal | Hot Case | Cold Case | Notes |
|--------|---------|----------|-----------|-------|
| Solar Radiation (S) | 1361 W/m² | 1414 W/m² (perihelion) | 1322 W/m² (aphelion) | AM0 spectrum |
| Earth Albedo (a*S) | 408 W/m² | 481 W/m² (a=0.34) | 317 W/m² (a=0.24) | Varies with surface |
| Earth IR (OLR) | 237 W/m² | 258 W/m² (tropical) | 218 W/m² (polar) | Outgoing longwave |
| Cosmic Background | 2.725 K | 2.725 K | 2.725 K | Negligible flux |

### 1.2 View Factors (3U CubeSat at 550 km)

```
Earth angular radius: rho = arcsin(R_E / (R_E + h)) = arcsin(6371/6921) = 66.9 deg
Earth solid angle from satellite: Omega = 2*pi*(1 - cos(rho)) = 3.73 sr
View factor to Earth (nadir face): F_nadir = 0.88
View factor to Earth (side faces): F_side = 0.30
View factor to Deep Space: F_space = 1 - F_earth (per face)
```

| Face | F_earth | F_space | Solar Exposure |
|------|---------|---------|----------------|
| +Z (nadir) | 0.88 | 0.12 | Intermittent |
| -Z (zenith) | 0.02 | 0.98 | Direct sun (SSO) |
| +X (ram) | 0.30 | 0.70 | Depends on attitude |
| -X (wake) | 0.30 | 0.70 | Depends on attitude |
| +Y (sun-facing, SSO) | 0.30 | 0.70 | Continuous in sunlit |
| -Y (anti-sun) | 0.30 | 0.70 | Never direct |

## 2. Thermal Properties of Materials

### 2.1 Surface Optical Properties

| Surface Treatment | alpha_s | epsilon_IR | alpha/epsilon | Application |
|-------------------|---------|------------|---------------|-------------|
| Black anodize (AL) | 0.88 | 0.85 | 1.04 | Structure exterior |
| Bare aluminum (polished) | 0.15 | 0.05 | 3.00 | Not used (poor radiator) |
| White paint (AZ-93) | 0.14 | 0.92 | 0.15 | Radiator faces (option) |
| Solar cell (GaAs + coverglass) | 0.91 | 0.81 | 1.12 | Solar panels |
| Kapton (gold coated) | 0.42 | 0.63 | 0.67 | MLI outer layer |
| MLI (10-layer effective) | 0.42 | 0.02 | 21.0 | Blanket insulation |

### 2.2 Material Thermal Properties

| Material | Conductivity (W/mK) | Specific Heat (J/kgK) | Density (kg/m³) |
|----------|---------------------|----------------------|-----------------|
| AL 6061-T6 (structure) | 167 | 896 | 2700 |
| FR4 (PCB) | 0.3 (through-plane) | 1100 | 1850 |
| Copper (PCB traces) | 385 | 385 | 8960 |
| Kapton (polyimide) | 0.12 | 1090 | 1420 |
| Li-ion cell (NCR18650B) | 3.0 (axial), 0.5 (radial) | 1040 | 2700 |
| Thermal interface pad | 5.0 | 1000 | 2600 |

## 3. Thermal Node Model

### 3.1 Lumped-Parameter Node Description

The satellite is divided into 14 thermal nodes for the lumped-parameter analysis:

```
        +------ Node 6: -Z face (zenith) ------+
        |                                        |
        |   +---Node 10: ADCS Board---+          |
        |   +---Node 9: COMM Board----+          |
  Node  |   +---Node 8: OBC Board-----+    Node  |
  3: +Y |   +---Node 7: EPS Board-----+    4: -Y |
  face   |   +---Node 12: Battery------+    face   |
        |   +---Node 11: Camera-------+          |
        |   +---Node 13: Payload------+          |
        |                                        |
        +------ Node 5: +Z face (nadir) --------+
                                                  
  Node 1: +X face (ram)       Node 2: -X face (wake)
  Node 14: Solar panel (deployable)
```

### 3.2 Thermal Conductances Between Nodes

| From Node | To Node | Conductance (W/K) | Path Description |
|-----------|---------|-------------------|------------------|
| Structure faces (1-6) | Adjacent faces | 0.50 | AL frame conduction |
| Structure (any) | Internal boards | 0.25 | PC/104 standoffs (4x M3 AL) |
| EPS Board (7) | Battery (12) | 0.40 | Thermal pad + bracket |
| OBC Board (8) | COMM (9) | 0.15 | PC/104 connector + standoffs |
| COMM (9) | ADCS (10) | 0.15 | PC/104 connector + standoffs |
| Battery (12) | +X face (1) | 0.10 | Thermal isolators (Ultem) |
| Camera (11) | +Z face (5) | 0.30 | AL mounting bracket |
| Payload (13) | Structure | 0.20 | Mounting screws + interface |

### 3.3 Radiative Couplings

| From Node | To Node | Coupling GR (W/K⁴) | Notes |
|-----------|---------|---------------------|-------|
| Face 1-6 | Deep space | epsilon * sigma * A * F | Per face, see view factors |
| Face 5 (+Z) | Earth (237 W/m²) | F_nadir * A | Absorbed Earth IR |
| Internal boards | Adjacent boards | Small (< 0.01 W/K⁴) | Negligible internal radiation |

## 4. Boundary Conditions

### 4.1 Hot Case Definition (worst-case hot)

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Solar constant | 1414 W/m² | Perihelion (January) |
| Albedo factor | 0.34 | Tropical ocean + clouds |
| Earth IR | 258 W/m² | Tropical subsolar point |
| Beta angle | 71.6 deg | Full sun (no eclipse) |
| Internal dissipation | 6.46 W | Science mode (max power) |
| Attitude | +Y sun-pointing | Maximum solar input on one face |
| BOL optical properties | Fresh alpha_s = 0.88 | No UV degradation yet |

### 4.2 Cold Case Definition (worst-case cold)

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Solar constant | 1322 W/m² | Aphelion (July) |
| Albedo factor | 0.24 | Polar/ocean (low albedo) |
| Earth IR | 218 W/m² | Polar winter region |
| Beta angle | 0 deg | Maximum eclipse (35.7 min) |
| Internal dissipation | 1.21 W | Safe mode (minimum power) |
| Attitude | Tumbling (worst orientation) | Minimum solar input |
| EOL optical properties | Degraded alpha_s = 0.95, epsilon = 0.82 | 2-year UV/atomic oxygen |

## 5. Temperature Predictions

### 5.1 Steady-State Equilibrium (Analytical)

For a single isothermal node, energy balance gives:

```
alpha_s * S * A_proj + epsilon * q_IR * A_earth + Q_int
    = epsilon * sigma * A_total * T^4

T = [ (alpha_s * S * A_proj + epsilon * q_IR * A_earth + Q_int)
      / (epsilon * sigma * A_total) ] ^ (1/4)
```

Where sigma = 5.67e-8 W/m²K⁴ (Stefan-Boltzmann constant)

### 5.2 Hot Case Results

| Node | Component | Predicted T (C) | Acceptance Limit (C) | Margin (C) |
|------|-----------|-----------------|---------------------|------------|
| 3 | +Y Face (sun-facing) | +72 | +100 | +28 |
| 5 | +Z Face (nadir) | +48 | +100 | +52 |
| 4 | -Y Face (anti-sun) | +18 | +100 | +82 |
| 7 | EPS Board | +52 | +70 | +18 |
| 8 | OBC (STM32F4) | +55 | +75 | +20 |
| 9 | COMM Module | +49 | +70 | +21 |
| 10 | ADCS Board | +47 | +70 | +23 |
| 11 | Camera Sensor | +53 | +50 | **-3 (VIOLATION)** |
| 12 | Battery Pack | +42 | +40 | **-2 (VIOLATION)** |
| 13 | Payload | +45 | +60 | +15 |

**Action Items for Hot Case Violations:**
- Camera: Add white-paint radiator on nadir face or duty-cycle limit imaging to < 5 min
- Battery: Add thermal isolator between battery and EPS board; consider radiator on -Y face

### 5.3 Cold Case Results

| Node | Component | Predicted T (C) | Acceptance Limit (C) | Margin (C) |
|------|-----------|-----------------|---------------------|------------|
| 1-6 | Structure faces | -38 to -18 | -40 | +2 to +22 |
| 7 | EPS Board | -12 | -20 | +8 |
| 8 | OBC (STM32F4) | -15 | -30 | +15 |
| 9 | COMM Module | -18 | -20 | +2 |
| 10 | ADCS Board | -16 | -20 | +4 |
| 11 | Camera Sensor | -22 | -20 | **-2 (VIOLATION)** |
| 12 | Battery (heater ON) | +2 | -5 | +7 |
| 13 | Payload | -14 | -20 | +6 |

**Action Item:** Camera requires survival heater or improved thermal coupling to warm boards.

## 6. Heater Duty Cycle Analysis

### 6.1 Battery Heater

The battery heater maintains cells above 0C for safe charging.

```
Heater sizing:
  Q_loss = G_conductive * (T_bat - T_structure) + epsilon * sigma * A * (T_bat^4 - T_env^4)
  
  During eclipse cold case:
    T_structure ~ -25C (248 K)
    T_bat_target = +5C (278 K)
    G_cond = 0.40 W/K (to EPS board) + 0.10 W/K (to structure) = 0.50 W/K
    Q_loss_cond = 0.50 * (278 - 248) = 15.0 W  << This seems high

  Corrected (with thermal isolation):
    G_cond_isolated = 0.08 W/K (Ultem spacers + minimal contact)
    Q_loss = 0.08 * 30 = 2.4 W

  With 2x 1W heaters: P_heater = 2.0 W
  Steady state T_bat = T_structure + P_heater / G_cond = -25 + 2.0/0.08 = 0C (marginal)
```

### 6.2 Heater Duty Cycle Profile

| Orbit Phase | Duration (min) | Heater State | Power (W) | Energy (Wh) |
|-------------|---------------|-------------|-----------|-------------|
| Sunlit (hot case) | 62 | OFF | 0.0 | 0.0 |
| Sunlit (cold case) | 62 | ON 30% duty | 0.6 | 0.62 |
| Eclipse (cold case) | 34 | ON 100% duty | 2.0 | 1.13 |
| Eclipse (nominal) | 34 | ON 60% duty | 1.2 | 0.68 |

Average heater power over orbit (cold case): **1.25 W**
This is accounted for in the power budget eclipse standby mode.

### 6.3 Thermostat Control Logic

```
if T_battery < T_ON (0 C):
    heater = ON (PID or bang-bang)
elif T_battery > T_OFF (5 C):
    heater = OFF

Hysteresis band: 5C (prevents rapid cycling)
Thermistor accuracy: +/- 0.5C (NTC, Steinhart-Hart calibration)
Heater response time: ~30 seconds to +1C (low thermal mass heater pad)
```

## 7. Component Derating Table

Per ECSS-Q-ST-30-11C (Derating of EEE Components):

| Component | Qual. Range (C) | Derated Range (C) | Derating Rule | Hot Margin | Cold Margin |
|-----------|----------------|-------------------|---------------|------------|-------------|
| STM32F427 MCU | -40 to +85 | -30 to +75 | 80% of range | +20C | +15C |
| NCR18650B Battery | -10 to +45 | -5 to +40 | Charge: 0C to 40C | **-2C** | +7C |
| CC1125 UHF Radio | -40 to +85 | -30 to +75 | 80% of range | +26C | +12C |
| OV5647 Camera | -20 to +60 | -15 to +50 | 75% of range | **-3C** | +7C |
| BMI088 Gyroscope | -40 to +85 | -30 to +75 | 80% of range | +28C | +14C |
| HMC5883L Magnetometer | -30 to +85 | -25 to +75 | 80% of range | +28C | +10C |
| MAX-M10S GNSS | -40 to +85 | -30 to +75 | 80% of range | +26C | +15C |
| Spectrolab UTJ Cells | -100 to +100 | -80 to +90 | 90% of range | +18C | +42C |
| RFPA5522 S-band PA | -40 to +85 | -30 to +70 | 80% of range | +21C | +12C |

**Bold** values indicate tight margins requiring design action (see Section 5 action items).

## 8. Thermal Test Plan

### 8.1 Test Levels (per ECSS-Q-ST-70-04C)

| Level | Purpose | Temperature Range | Duration |
|-------|---------|------------------|----------|
| Qualification | Design verification | +/- 10C beyond acceptance | 4 cycles min |
| Acceptance | Workmanship screening | Predicted +/- 5C | 8 cycles min |
| Protoflight | Combined qual + acceptance | Qual range, acceptance cycles | 4 cycles |

### 8.2 Thermal Vacuum Test Profile

```
Temperature
(C)
 +80 |          ____          ____          ____          ____
     |         /    \        /    \        /    \        /    \
 +60 |        / HOT  \      /      \      /      \      /      \
     |       / DWELL  \    /        \    /        \    /        \
 +20 |      /  (2 hr)  \  /          \  /          \  /          \
     |     /            \/            \/            \/            
   0 |----/                                                       
     |                                                            
 -20 |                                                            
     |                  /\            /\            /\            
 -40 |                 /  \          /  \          /  \           
     |                / COLD\       /    \        /    \          
 -50 |               / DWELL \     /      \      /      \        
     |              /  (2 hr) \   /        \    /        \       
     +----+----+----+----+----+----+----+----+----+----+---> Time
      Cycle 1        Cycle 2       Cycle 3       Cycle 4

Pressure: < 1e-5 mbar (high vacuum)
Ramp rate: 1-2 C/min (max 5 C/min for qualification)
Dwell time: 2 hours at each extreme (functional test during dwell)
```

### 8.3 Thermal Cycling (Ambient Pressure)

For board-level screening before integration:

| Parameter | Value |
|-----------|-------|
| Hot limit | +75C |
| Cold limit | -30C |
| Ramp rate | 5C/min |
| Dwell time | 15 min per extreme |
| Number of cycles | 20 |
| Functional test | Every 5th cycle |

### 8.4 Pass/Fail Criteria

| Test | Criterion |
|------|-----------|
| Thermal balance (TVAC) | Model correlation within +/- 5C of prediction |
| Functional (hot dwell) | All subsystems operational, telemetry nominal |
| Functional (cold dwell) | All subsystems operational, battery charging |
| Heater verification | Battery temp maintained > 0C during cold dwell |
| Survival (cold, unpowered) | No damage after 2 hr at -50C, resume operation |
| Post-test inspection | No delamination, cracking, or discoloration |

## 9. Thermal Design Improvements (Trade Study)

| Option | Mass Impact | Power Impact | Thermal Benefit | Priority |
|--------|------------|-------------|-----------------|----------|
| White paint on -Y face | Negligible | None | -10C hot case reduction | High |
| MLI on battery module | +15 g | None | +8C cold case improvement | High |
| Copper thermal strap (bat-radiator) | +20 g | None | -5C hot case for battery | Medium |
| Camera duty-cycle limit | None | Software | Prevents camera overheat | High |
| Additional heater (camera) | +10 g | +0.5 W | +5C cold case for camera | Medium |
| Thermal gap filler (all boards) | +8 g | None | Better board-to-frame coupling | Low |

## 10. References

- ECSS-E-ST-31C: Space Engineering - Thermal Control (2008)
- ECSS-Q-ST-70-04C: Space Product Assurance - Thermal Testing (2008)
- ECSS-Q-ST-30-11C: Derating - EEE Components (2011)
- Gilmore, D.G., "Spacecraft Thermal Control Handbook", Vol. 1, 2nd Ed.
- NASA-STD-7009A: Standard for Models and Simulations
- Panasonic NCR18650B Datasheet (thermal specifications)
