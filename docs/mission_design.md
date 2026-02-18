# Mission Design

## Mission Objectives
1. Demonstrate modular CubeSat platform (1U-6U)
2. Earth observation with multispectral imaging (30m GSD)
3. Radiation environment monitoring (LEO)
4. IoT message relay demonstration
5. Technology validation for ADCS and EPS subsystems

## Orbit Selection

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Type | Sun-Synchronous (SSO) | Consistent lighting for imaging |
| Altitude | 550 km | Balance: resolution vs lifetime |
| Inclination | 97.6° | SSO requirement |
| LTAN | 10:30 | Morning crossing for imaging |
| Expected Lifetime | 2 years | Atmospheric drag at 550 km |
| Orbital Period | ~96 min | 15 orbits/day |

## Mission Phases
1. **Launch & Deployment** (Day 0): Separation from deployer, antenna deployment
2. **Commissioning** (Days 1-7): System checkout, ADCS detumbling, sensor calibration
3. **Nominal Operations** (Day 8+): Science data collection, imaging, telemetry
4. **End of Life**: Passive deorbit (< 25 years per guidelines)

## Ground Segment
- Primary ground station: Tashkent (41.3°N, 69.2°E)
- ~6-8 passes per day, average 8 min per pass
- UHF for housekeeping, S-band for bulk data downlink
