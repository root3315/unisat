# Changelog

All notable changes to UniSat will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2026-04-17

### Added — AX.25 Link Layer (Track 1)

- Pure C11 AX.25 v2.2 library at `firmware/stm32/Drivers/AX25/` —
  FCS (CRC-16/X.25 with RFC oracle `"123456789" → 0x906E`),
  bit-level stuffing across byte boundaries, address encode/decode
  per §3.12, UI-frame encode + pure decoder, first-class streaming
  decoder (`ax25_decoder_t`) with HUNT/FRAME state machine.
- Python mirror at `ground-station/utils/ax25.py` — same algorithm,
  same exception hierarchy, shared test fixtures.
- 28 golden test vectors (`tests/golden/ax25_vectors.json` + `.inc`)
  consumed by both C and Python runners — bit-identical results
  required (REQ-AX25-015).
- Project-style facade `ax25_api.h` (ADR-002) so firmware callers
  use `AX25_Xxx()` naming while the core library stays reusable.
- SITL TCP virtual UART (`firmware/stm32/Drivers/VirtualUART/`)
  replacing HAL UART under `SIMULATION_MODE`; one end-to-end demo
  binary `scripts/sitl_fw.c`.
- Ground-station CLIs (`ground-station/cli/ax25_listen.py`,
  `ax25_send.py`) — TCP listener/sender that speak the same AX.25
  wire format as the firmware.
- `scripts/demo.py` + `Makefile` targets — `make demo` runs the
  full C-encoder → TCP → Python-decoder path, asserts 2 beacons.
- Comprehensive docs: design spec (775 lines), implementation plan
  (4022 lines), ADR-001 (no CSP), ADR-002 (style adapter), threat
  model, byte-by-byte walkthrough tutorial, auto-generated
  verification trace matrix.
- GitHub Actions workflow `.github/workflows/ax25.yml`
  (linux-only for free-tier economy).

### Added — Track 1b (command authentication primitives)

- HMAC-SHA256 library at `firmware/stm32/Drivers/Crypto/` — portable
  C11, zero platform dependencies, suitable for flight-software
  task context. RFC 4231 test vectors (§4.2, §4.3) asserted.
- Constant-time tag comparison (`hmac_sha256_verify`).
- Python mirror at `ground-station/utils/hmac_auth.py` (stdlib
  `hmac` + `hashlib`), same RFC vectors asserted to guarantee
  cross-implementation agreement.
- Beacon TX path now properly layered:
  48 B raw (`Telemetry_PackBeacon`) → CCSDS Space Packet
  (`CCSDS_BuildPacket` + `CCSDS_Serialize`) → AX.25 UI frame
  (`COMM_SendAX25`).

### Fixed

- `gnss.c`, `payload.c`, `sensors.c`, `obc.c` updated to the
  handle-based driver APIs (previously invoked legacy handle-less
  calls that broke the host build). Full `unisat_core` library
  now compiles cleanly on host.
- `CMakeLists.txt`: removed `EXCLUDE_FROM_ALL` workaround —
  `unisat_core` is a first-class build target so any future
  regression in any subsystem fails CI before a test target
  touches it.
- Orphan tests (`test_ccsds`, `test_adcs_algorithms`, `test_eps`,
  `test_telemetry`) wired into `ctest`. All green.
- `Telemetry_PackBeacon` now emits the 48-byte raw beacon layout
  per `communication_protocol.md` §7.2; the legacy CCSDS-wrapped
  variant preserved as `Telemetry_PackBeaconCcsds`.

### Infrastructure

- `docker/Dockerfile.ci` — locally-built image with `cmake` +
  `pytest` + `hypothesis` pre-installed. Cuts each verification
  run from ~60 s to ~5 s.
- `docs/verification/driver_audit.md` — full audit of the 8
  sensor drivers (MPU9250, LIS3MDL, BME280, TMP117, MCP3008,
  UBLOX, SBM20, SunSensor): every one confirmed a real
  vendor-datasheet-compliant protocol (no stubs).

### Test counts

- C (`ctest`): 15 targets, all pass (up from 4 broken-wired).
- Python (`pytest`): 34 tests, all pass (incl. 200 hypothesis
  property-based + 500 fuzz + RFC 4231 HMAC).

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
