# Orbit Analysis

Reference: ECSS-E-ST-10-04C (Space Environment), IADC Space Debris Mitigation Guidelines, CubeSat Design Specification Rev. 14

## 1. Orbital Elements

### 1.1 Keplerian Elements

| Element | Symbol | Value | Notes |
|---------|--------|-------|-------|
| Semi-major axis | a | 6921.14 km | R_E + h = 6371.0 + 550.0 |
| Eccentricity | e | 0.0001 | Near-circular (launcher insertion) |
| Inclination | i | 97.59 deg | Sun-synchronous requirement |
| RAAN | Omega | TBD (launch-dependent) | Determines LTAN |
| Argument of Perigee | omega | 0 deg | Circular orbit, undefined |
| True Anomaly | nu | 0 deg (epoch) | Arbitrary at epoch |
| LTAN | - | 10:30 | Local Time of Ascending Node |

### 1.2 Derived Parameters

```
Orbital Period:     T = 2*pi * sqrt(a^3 / mu)
                      = 2*pi * sqrt(6921.14^3 / 398600.4418)
                      = 5742.4 s = 95.71 min

Mean Motion:        n = 2*pi / T = 1.094e-3 rad/s = 15.04 rev/day

Orbital Velocity:   v = sqrt(mu / a) = sqrt(398600.4 / 6921.14) = 7.59 km/s

Ground Track Speed: v_gt = v * cos(i) * (R_E / a) = 7.04 km/s (approx)
```

Where mu = 398600.4418 km³/s² (Earth gravitational parameter)

## 2. Sun-Synchronous Orbit (SSO) Derivation

### 2.1 SSO Condition

A sun-synchronous orbit requires the RAAN to precess at +0.9856 deg/day (matching Earth's
orbital rate around the Sun). The J2 perturbation provides this precession:

```
dOmega/dt = -3/2 * n * J2 * (R_E/a)^2 * cos(i) / (1 - e^2)^2

Setting dOmega/dt = +0.9856 deg/day = 1.991e-7 rad/s:

cos(i) = - (dOmega/dt) * 2 * a^2 * (1-e^2)^2 / (3 * n * J2 * R_E^2)

Where:
  J2 = 1.08263e-3 (Earth oblateness)
  R_E = 6371.0 km
  a = 6921.14 km
  n = 1.094e-3 rad/s

cos(i) = -(1.991e-7) * 2 * 6921.14^2 / (3 * 1.094e-3 * 1.08263e-3 * 6371.0^2)
       = -0.1323

i = arccos(-0.1323) = 97.59 deg
```

### 2.2 SSO Inclination vs. Altitude

| Altitude (km) | Semi-major axis (km) | Required Inclination (deg) |
|----------------|----------------------|---------------------------|
| 400 | 6771 | 97.05 |
| 450 | 6821 | 97.20 |
| 500 | 6871 | 97.40 |
| **550** | **6921** | **97.59** |
| 600 | 6971 | 97.79 |
| 650 | 7021 | 97.99 |
| 700 | 7071 | 98.19 |

## 3. Perturbation Analysis

### 3.1 J2 Oblateness (Dominant Perturbation)

| Effect | Formula | Rate | Impact |
|--------|---------|------|--------|
| RAAN precession | dOmega/dt = -3/2 * n * J2 * (R_E/a)^2 * cos(i) | +0.9856 deg/day | Maintains SSO |
| Argument of perigee drift | domega/dt = 3/4 * n * J2 * (R_E/a)^2 * (5*sin^2(i) - 4) | +2.17 deg/day | Irrelevant (circular) |
| Mean anomaly secular drift | dM/dt correction | +0.003 deg/day | Absorbed into mean motion |

Higher-order zonal harmonics (J3, J4) contribute < 0.01 deg/day and are neglected for mission planning.

### 3.2 Atmospheric Drag

```
Drag acceleration: a_drag = -1/2 * rho * v^2 * (C_D * A_ref / m)

Ballistic coefficient: BC = m / (C_D * A_ref)

Where:
  C_D = 2.2 (typical for CubeSat)
  A_ref = 0.03 m² (3U cross-section: 0.1m x 0.3m)
  m = 2.18 kg (CBE mass)
  BC = 2.18 / (2.2 * 0.03) = 33.0 kg/m²
```

Atmospheric density at 550 km (NRLMSISE-00 model):

| Solar Activity (F10.7) | rho (kg/m³) | Drag Accel (m/s²) | Altitude Loss (km/yr) |
|------------------------|-------------|--------------------|-----------------------|
| Solar minimum (70 sfu) | 2.0e-13 | 5.3e-7 | 0.8 |
| Solar moderate (140 sfu) | 1.5e-12 | 3.9e-6 | 6.2 |
| Solar maximum (250 sfu) | 8.0e-12 | 2.1e-5 | 33.1 |

### 3.3 Solar Radiation Pressure (SRP)

```
SRP acceleration: a_srp = P_sr * (1 + q) * A_ref / m

Where:
  P_sr = S/c = 1361 / 3e8 = 4.54e-6 N/m² (solar radiation pressure at 1 AU)
  q = 0.6 (reflectivity, 0 = absorb, 1 = perfect mirror)
  A_ref = 0.03 m² (assuming worst-case orientation)
  m = 2.18 kg

a_srp = 4.54e-6 * 1.6 * 0.03 / 2.18 = 1.0e-7 m/s²
```

| Perturbation | Acceleration (m/s²) | Period Effect | Relative Magnitude |
|-------------|--------------------|--------------|--------------------|
| J2 | ~1e-3 | Secular precessions | Dominant |
| Drag (moderate solar) | ~4e-6 | Orbit decay | Secondary |
| SRP | ~1e-7 | Long-period oscillations | Tertiary |
| Lunar/Solar gravity | ~5e-8 | Long-period | Negligible |
| Solid Earth tides | ~1e-9 | Short-period | Negligible |

### 3.4 Orbit Maintenance (Delta-V Budget)

No orbit maintenance is planned (no propulsion system). Expected natural evolution:

| Year | Altitude Estimate (km) | Notes |
|------|----------------------|-------|
| 0 (launch) | 550.0 | Injection altitude |
| 0.5 | 547-549 | Minimal decay |
| 1.0 | 543-548 | Depends on solar cycle |
| 1.5 | 537-545 | Mission requirement: h > 500 km |
| 2.0 (EOL) | 530-540 | End of nominal mission |

## 4. Eclipse Analysis

### 4.1 Eclipse Geometry

```
          Sun direction
            <----

           /--------\        Shadow cylinder
          / SUNLIT   \       (cylindrical approximation)
   ------/   ORBIT    \------ 
  |     /     ___       \     |
  |    |    /     \    |     |  Eclipse region
  |     |  | EARTH |   |     |
  |    |    \_____/    |     |
  |     \              /     |
   ------\            /------
          \ ECLIPSE  /
           \--------/

Eclipse condition: satellite enters Earth's shadow cone
Eclipse half-angle: alpha_e = arcsin(R_E / (R_E + h)) = 66.9 deg
```

### 4.2 Eclipse Duration vs. Beta Angle

The beta angle is the angle between the orbital plane and the Earth-Sun line.
For SSO at 10:30 LTAN, beta varies seasonally:

```
Eclipse fraction: f_e = (1/pi) * arccos(sqrt(h^2 + 2*R_E*h) / ((R_E+h)*cos(beta)))

This is valid when |beta| < beta_star, where:
  beta_star = arcsin(R_E / (R_E + h)) = arcsin(6371/6921) = 66.9 deg
  (Above beta_star: no eclipse, full sunlight)
```

| Beta (deg) | Eclipse Duration (min) | Eclipse Fraction (%) | Season (10:30 LTAN) |
|------------|----------------------|---------------------|---------------------|
| 0 | 35.7 | 37.3 | Equinox (worst) |
| 10 | 35.3 | 36.9 | Near equinox |
| 20 | 34.1 | 35.6 | Moderate |
| 30 | 31.9 | 33.3 | Moderate |
| 40 | 28.4 | 29.7 | Approaching solstice |
| 50 | 22.8 | 23.8 | Near solstice |
| 60 | 12.7 | 13.3 | Near full sun |
| 66.9 | 0.0 | 0.0 | Full sun period |

For a 10:30 LTAN SSO at 550 km, the beta angle ranges approximately from 
-23.4 + 10.5 = -12.9 deg to +23.4 + 10.5 = +33.9 deg over a year, meaning eclipses occur 
year-round but vary in duration.

## 5. Ground Station Access Statistics

### 5.1 Tashkent Ground Station (41.3N, 69.2E)

Analysis performed using SGP4 propagator over 30-day simulation:

| Minimum Elevation | Passes/Day | Avg Duration (min) | Max Duration (min) | Total Contact/Day (min) |
|-------------------|-----------|-------------------|--------------------|------------------------|
| 0 deg | 8-10 | 9.2 | 14.1 | 78 |
| 5 deg | 6-8 | 8.0 | 12.8 | 54 |
| **10 deg** | **5-7** | **7.2** | **11.5** | **43** |
| 20 deg | 3-5 | 5.8 | 9.2 | 22 |
| 30 deg | 2-3 | 4.5 | 7.1 | 11 |

### 5.2 Access Gap Analysis

| Metric | Value |
|--------|-------|
| Average gap between passes | 2.5 hours |
| Maximum gap (worst case) | 8.2 hours |
| Minimum gap (consecutive high passes) | 92 min (1 orbit) |
| Passes with max elevation > 60 deg | ~2 per day |
| Passes with max elevation > 30 deg | ~4 per day |

### 5.3 Ground Station Pass Geometry

```
Elevation
(deg)
  90 |
     |                 *  (max elevation)
  60 |               *   *
     |             *       *
  30 |           *           *
     |         *               *
  10 |       *                   *      (AOS/LOS at 10 deg min elev)
   5 |     * AOS                   * LOS
   0 |---*--+--+--+--+--+--+--+--+--*--> Time (min from AOS)
     0   1  2  3  4  5  6  7  8  9  10

Typical high-elevation pass profile (max el = 75 deg)
Total duration: ~11 min above 10 deg elevation
```

### 5.4 Data Volume Per Pass

| Link | Rate (effective) | 5-min pass | 8-min pass | 12-min pass |
|------|-----------------|-----------|-----------|-------------|
| UHF Downlink | 4,080 bps | 150 KB | 240 KB | 360 KB |
| S-band Downlink | 117,760 bps | 4.3 MB | 6.9 MB | 10.4 MB |
| UHF Uplink | 4,080 bps | 150 KB | 240 KB | 360 KB |

## 6. Repeat Ground Track Analysis

### 6.1 Ground Track Repeat Condition

A repeat ground track occurs when:

```
N_orbits * T_orbit = M_days * T_sidereal_day

Where T_sidereal_day = 86164.1 s

For T_orbit = 5742.4 s:
  Revs per sidereal day = 86164.1 / 5742.4 = 15.005

Near-repeat patterns:
  15 revs in 1 day:  drift = 0.005 * 360/15 = 0.12 deg/day longitude
  211 revs in 14 days:  near-exact repeat
  422 revs in 28 days:  even closer repeat
```

### 6.2 Ground Track Coverage

| Parameter | Value |
|-----------|-------|
| Inter-track spacing at equator | 360 / 15 = 24 deg = 2670 km |
| Track width (nadir imaging, FOV 30 deg) | ~290 km |
| Coverage gap at equator | ~2380 km |
| Days to fill equatorial gaps (no maneuver) | ~14 days |
| Latitude for daily coverage | > 72 deg |
| Near-polar coverage | Complete (overlapping tracks) |

### 6.3 Imaging Revisit Analysis

For a camera with 30 deg cross-track FOV at 550 km:

```
Swath width = 2 * h * tan(FOV/2) = 2 * 550 * tan(15) = 295 km
```

| Latitude | Revisit Time (days) | Overlap Fraction |
|----------|---------------------|-----------------|
| 0 deg (equator) | 3-4 | 0% (gaps exist) |
| 20 deg | 2-3 | ~5% |
| 40 deg | 1-2 | ~25% |
| 60 deg | < 1 | ~55% |
| 80 deg | < 1 | ~90% |

## 7. Deorbit Timeline Analysis

### 7.1 Orbital Lifetime Estimation

Using the exponential decay model with atmospheric density from NRLMSISE-00:

```
dh/dt = -(rho * v * C_D * A) / (2 * m) * T / pi

Lifetime integration (numerical, from 550 km to 200 km reentry):
```

| Scenario | F10.7 avg | Initial Alt (km) | Lifetime (years) | Compliant (< 25 yr) |
|----------|-----------|-------------------|-------------------|---------------------|
| Solar minimum (quiet sun) | 70 | 550 | 18-22 | YES |
| Solar moderate | 140 | 550 | 7-10 | YES |
| Solar maximum (active) | 200 | 550 | 3-5 | YES |
| Worst case (prolonged min) | 70 | 550 | ~22 | YES (marginal) |

### 7.2 Altitude Decay Profile (Moderate Solar Activity)

```
Altitude
(km)
550 |*
525 | *
500 |  *
475 |   *
450 |    *
425 |     **
400 |       **
375 |         **
350 |           ***
325 |              ***
300 |                 ****
275 |                     ******
250 |                           ********
225 |                                   *****
200 |                                        ** (reentry)
    +---+---+---+---+---+---+---+---+---+---+---> Years
    0   1   2   3   4   5   6   7   8   9   10

Moderate solar activity (F10.7 = 140 sfu)
BC = 33 kg/m²
```

### 7.3 Compliance with Debris Mitigation Guidelines

| Guideline | Requirement | UniSat Status |
|-----------|-------------|---------------|
| IADC (25-year rule) | Deorbit within 25 years of EOL | COMPLIANT (7-22 years) |
| French Space Operations Act | 25-year limit | COMPLIANT |
| US Government Orbital Debris Policy (2024) | 5-year limit for new missions | **NON-COMPLIANT in worst case** |
| ESA Zero Debris Charter | Best-effort minimization | Under review |

**Risk:** The new US 5-year guideline may not be met under prolonged solar minimum. 
Mitigation options: (1) deploy drag sail at EOL, (2) lower initial altitude to 500 km, 
(3) accept risk if not launching under US jurisdiction.

## 8. Orbit Determination and Propagation

### 8.1 GNSS-Based OD

| Parameter | Value |
|-----------|-------|
| GNSS receiver | u-blox MAX-M10S |
| Position accuracy | < 2.5 m (3D RMS) |
| Velocity accuracy | < 0.05 m/s (RMS) |
| Fix rate | 1 Hz (configurable to 0.1 Hz for power saving) |
| Cold start time | < 30 s |
| TLE update frequency | Every orbit (via GNSS fix) |

### 8.2 Propagation Model

For onboard orbit propagation (between GNSS fixes):

| Model | Accuracy (24h propagation) | CPU Load |
|-------|---------------------------|----------|
| SGP4/SDP4 (two-line elements) | ~1 km | Minimal |
| J2 analytical | ~100 m | Low |
| Numerical (RK4, J2+drag) | ~10 m | Moderate |

Selected: SGP4 for coarse planning, J2 analytical for imaging predictions.

## 9. References

- Vallado, D.A., "Fundamentals of Astrodynamics and Applications", 4th Ed., Chapter 9
- ECSS-E-ST-10-04C: Space Environment (2008)
- IADC-02-01: Space Debris Mitigation Guidelines, Rev. 2 (2020)
- US Government Orbital Debris Mitigation Standard Practices (2024 update)
- Picone, J.M., et al., "NRLMSISE-00 Empirical Model of the Atmosphere", JGR, 2002
- Wertz, J.R., "Space Mission Engineering: The New SMAD", Chapters 5-6
