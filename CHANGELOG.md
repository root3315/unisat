# Changelog

All notable changes to UniSat will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-02-18

### Added

#### Firmware (STM32F4 + FreeRTOS)
- OBC main controller with 6 FreeRTOS tasks
- CCSDS-based telemetry packet formatting
- ADCS algorithms: B-dot detumbling, sun pointing, nadir/target pointing
- Full quaternion math library (multiply, inverse, normalize, Euler/DCM conversion)
- EPS subsystem: MPPT (Perturb & Observe), battery manager, power distribution
- HAL drivers for 8 sensors: LIS3MDL, BME280, TMP117, MPU9250, SBM20, u-blox, MCP3008, Sun Sensor
- Watchdog with per-task monitoring and 10-second timeout
- Error handler with EEPROM logging and safe mode transition
- Communication module for UHF (AX.25) and S-band

#### Flight Software (Python + asyncio)
- Asynchronous flight controller with state machine
- Dynamic module loading from mission_config.json
- Camera handler with scheduled and on-demand capture
- SVD image compression with configurable rank
- Telemetry manager with CCSDS packing
- SQLite data logger with 1GB rotation
- SGP4-based orbit predictor
- Orbit-based task scheduler
- Health monitor (CPU, RAM, temperature, storage)
- Safe mode with automatic activation on 24h communication loss
- Power manager with priority-based load shedding
- Abstract payload interface for plugin modules

#### Ground Station (Streamlit + Plotly)
- Mission dashboard with subsystem health indicators
- Real-time telemetry charts (temperature, pressure, voltage, radiation)
- 3D orbit visualization on interactive globe
- Image gallery with geolocation overlay
- 3D satellite attitude visualization
- Power generation/consumption monitoring
- HMAC-SHA256 authenticated command center
- Communication pass prediction and imaging planner
- Data export (CSV, JSON, CCSDS)
- Automated health report with anomaly detection

#### Simulation
- Keplerian orbit propagator with J2 perturbation
- Power budget simulator (eclipse/sunlight cycles)
- Six-face thermal model (solar, albedo, Earth IR, cosmic background)
- Link budget calculator (SNR, BER, range)
- Comprehensive mission analyzer

#### Configurator
- Web-based mission configurator (Streamlit)
- Form factor templates: 1U, 2U, 3U, 6U
- Mass, power, and volume validators
- mission_config.json generator
- PDF mission report generator
- Bill of Materials (BOM) generator

#### Payloads
- Abstract payload interface
- Radiation monitor (SBM-20 Geiger counter)
- Earth observation camera
- IoT relay module
- Magnetometer survey
- Spectrometer module

#### Documentation
- CDR-level system architecture
- CCSDS communication protocol specification
- Power budget analysis (Nominal / Peak / Safe Mode)
- Mass budget with 20% margin
- UHF and S-band link budget
- Thermal analysis (hot/cold case)
- Orbit analysis (ground track, eclipse, revisit time)
- Test plan with pass/fail matrix
- Assembly guide
- Competition adaptation guide (CanSat, CubeSat, NASA Space Apps, Olympiad, Hackathon)

#### Infrastructure
- GitHub Actions CI/CD (Python tests, firmware build, linting)
- Documentation auto-generation workflow
- Setup, test, build, flash, and simulation scripts
