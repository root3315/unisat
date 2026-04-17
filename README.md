<p align="center">
  <img src="docs/diagrams/system_block_diagram.svg" alt="UniSat Logo" width="600">
</p>

<h1 align="center">UniSat — Universal Modular CubeSat Platform</h1>

<p align="center">
  <a href="https://github.com/root3315/unisat/blob/master/scripts/verify.sh"><img src="https://img.shields.io/badge/verify-.%2Fscripts%2Fverify.sh-brightgreen.svg" alt="Verify"></a>
  <a href="https://github.com/root3315/unisat/blob/master/docs/superpowers/specs/2026-04-17-track1-ax25-design.md"><img src="https://img.shields.io/badge/AX.25-v2.2_full-success.svg" alt="AX.25"></a>
  <a href="https://github.com/root3315/unisat/blob/master/docs/verification/ax25_trace_matrix.md"><img src="https://img.shields.io/badge/tests-C_16%20%2B%20Py_34-brightgreen.svg" alt="Tests"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License"></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/python-3.11+-blue.svg?logo=python&logoColor=white" alt="Python"></a>
  <a href="#"><img src="https://img.shields.io/badge/firmware-STM32F4-green.svg?logo=stmicroelectronics" alt="STM32"></a>
  <a href="#"><img src="https://img.shields.io/badge/platform-CubeSat_1U--6U-orange.svg" alt="CubeSat"></a>
</p>

<p align="center">
  <b>Professional open-source CubeSat software platform for competitions and real missions</b>
</p>

---

## Overview

**UniSat** is a complete, modular software platform for CubeSat satellites supporting form factors from 1U to 6U. It covers the entire satellite software stack: from STM32 firmware running FreeRTOS to a Python-based ground station with real-time telemetry visualization.

Designed to be competition-ready for CanSat, CubeSat Design, NASA Space Apps, and similar aerospace competitions, while maintaining professional-grade code quality suitable for real missions.

---

## Обзор (Русский)

**UniSat** — полноценная модульная программная платформа для спутников формата CubeSat (1U–6U). Покрывает весь стек ПО спутника: от прошивки STM32 на FreeRTOS до наземной станции на Python с визуализацией телеметрии в реальном времени.

Проект готов к участию в конкурсах: CanSat, CubeSat Design, NASA Space Apps, аэрокосмические олимпиады и хакатоны. При этом код профессионального уровня, пригодный для реальных миссий.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    GROUND STATION (Python/Streamlit)         │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────────┐  │
│  │Dashboard │ │Telemetry │ │  Orbit   │ │Command Center │  │
│  │          │ │  Charts  │ │ Tracker  │ │  (HMAC-AUTH)  │  │
│  └──────────┘ └──────────┘ └──────────┘ └───────────────┘  │
└─────────────────────────┬───────────────────────────────────┘
                          │ UHF 437 MHz / S-band 2.4 GHz
                          │ AX.25 / CCSDS Protocol
┌─────────────────────────┴───────────────────────────────────┐
│                      CUBESAT (1U-6U)                         │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │         FLIGHT CONTROLLER (Raspberry Pi Zero 2 W)     │   │
│  │  ┌────────┐ ┌────────┐ ┌────────┐ ┌──────────────┐  │   │
│  │  │Camera  │ │Orbit   │ │Health  │ │  Scheduler   │  │   │
│  │  │Handler │ │Predict │ │Monitor │ │  (asyncio)   │  │   │
│  │  └────────┘ └────────┘ └────────┘ └──────────────┘  │   │
│  └──────────────────────┬───────────────────────────────┘   │
│                         │ UART                               │
│  ┌──────────────────────┴───────────────────────────────┐   │
│  │              OBC FIRMWARE (STM32F4 + FreeRTOS)        │   │
│  │  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────────┐  │   │
│  │  │ADCS  │ │EPS   │ │COMM  │ │GNSS  │ │Telemetry │  │   │
│  │  │B-dot │ │MPPT  │ │UHF   │ │u-blox│ │  CCSDS   │  │   │
│  │  │Sun   │ │BatMgr│ │S-band│ │      │ │          │  │   │
│  │  └──────┘ └──────┘ └──────┘ └──────┘ └──────────┘  │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌────────────────────┐  ┌───────────────────────────────┐  │
│  │   SOLAR PANELS     │  │      PAYLOAD (swappable)      │  │
│  │   GaAs 29.5% eff.  │  │  Radiation / Camera / IoT /   │  │
│  │   6 panels (3U)    │  │  Magnetometer / Spectrometer   │  │
│  └────────────────────┘  └───────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## Features

| Subsystem | Description | Technology |
|-----------|-------------|------------|
| **OBC Firmware** | Real-time task management, watchdog, safe mode | STM32F4 + FreeRTOS (C) |
| **ADCS** | B-dot detumbling, sun/nadir/target pointing | Quaternion math, PID control |
| **EPS** | MPPT solar charging, battery management | Perturb & Observe algorithm |
| **Communication** | UHF 9600 bps + S-band 256 kbps | **AX.25 v2.2 full** (streaming decoder, bit-stuffing, CRC-16/X.25, §3.12 addresses) + CCSDS Space Packet + HMAC-SHA256 |
| **Flight Software** | Async mission control, imaging, orbit prediction | Python 3.11+ asyncio |
| **Ground Station** | 10-page dashboard with real-time telemetry | Streamlit + Plotly |
| **Simulation** | Orbit, power, thermal, link budget | Python scientific stack |
| **Configurator** | Web-based mission builder with validation | Streamlit |
| **Payloads** | 5 swappable payload modules | Plugin architecture |

---

## Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/root3315/unisat.git
cd unisat
```

### 2. Install dependencies

```bash
chmod +x scripts/setup.sh
./scripts/setup.sh
```

### 3. Run the ground station

```bash
cd ground-station
pip install -r requirements.txt
streamlit run app.py
```

### 4. Run simulation

```bash
cd simulation
pip install -r requirements.txt
python mission_analyzer.py
```

**Подробное руководство:** [`docs/USAGE_GUIDE.md`](docs/USAGE_GUIDE.md)
— от выбора типа миссии (CanSat / CubeSat / HAB / Rocket / Drone)
до подачи на конкурс.

**Что ещё можно добавить:** [`docs/GAPS_AND_ROADMAP.md`](docs/GAPS_AND_ROADMAP.md)
— честный статус, приоритизированный список открытых задач.

### 5. End-to-end AX.25 SITL demo (one command)

```bash
# Requires Docker Desktop running. No local gcc/cmake/pytest needed.
./scripts/verify.sh
```

That script builds the `unisat-ci` Docker image once (~30 s), then
runs the full green pipeline inside it: firmware host build →
ctest → pytest → end-to-end SITL beacon demo. Expected final line:
`✓ UniSat green. Ready to submit.`

For more granular control:
- `make all` — build + tests
- `make ci` — same, inside Docker
- `make demo` — just the SITL beacon path
- `make test-c` / `make test-py` — split suites
- `make help` — list all targets

---

## Project Status

| Check | Status |
|---|---|
| Firmware host build (all subsystems) | ✅ clean (`unisat_core`) |
| C unit tests (`ctest`) | ✅ **16 / 16 passing** |
| Python tests (`pytest`) | ✅ **34 / 34 passing** incl. 200 hypothesis + 500 fuzz cases |
| AX.25 golden vectors cross-validation | ✅ 28/28 byte-identical C ↔ Python |
| SHA-256 FIPS 180-4 oracle | ✅ `"abc"` + `""` canonical digests |
| HMAC-SHA256 RFC 4231 vectors | ✅ §4.2 + §4.3 on both C and Python |
| End-to-end SITL demo | ✅ C encoder → TCP → Python decoder, `fcs_valid: true` |
| Driver reality audit | ✅ all 8 sensors confirmed real (docs/verification/driver_audit.md) |
| Requirement traceability | ✅ auto-generated (docs/verification/ax25_trace_matrix.md) |

| Track 1b command dispatcher (HMAC T1 mitigated) | ✅ wired end-to-end |

Open items — see [`docs/GAPS_AND_ROADMAP.md`](docs/GAPS_AND_ROADMAP.md):
replay protection (T2), Streamlit↔AX.25 live bridge, flight-software
end-to-end scenario test.

### 6. Build firmware manually (optional)

If you don't want to use Docker:

```bash
cd firmware
cmake -B build -S .
cmake --build build
ctest --test-dir build --output-on-failure
```

Cross-compile for STM32F446 (requires `arm-none-eabi-gcc`):

```bash
cd firmware
cmake -B build-arm -S . -DCMAKE_TOOLCHAIN_FILE=arm.cmake
cmake --build build-arm
# Output: build-arm/unisat_firmware.{elf,bin,hex}
```

---

## Supported Form Factors

| Form Factor | Mass Limit | Dimensions (mm) | Solar Panels | Use Case |
|-------------|-----------|------------------|--------------|----------|
| **1U** | 1.33 kg | 100 × 100 × 113.5 | 4 | Education, CanSat |
| **2U** | 2.66 kg | 100 × 100 × 227.0 | 4 | Technology demo |
| **3U** | 4.00 kg | 100 × 100 × 340.5 | 6 | Earth observation |
| **6U** | 12.00 kg | 100 × 226.3 × 340.5 | 8 | Full mission |

Configure via `mission_config.json` — all subsystems adapt automatically.

---

## Competition Adaptation

Ready-to-submit adaptations for аэрокосмических конкурсов. Подробное
пошаговое руководство по каждому типу — в [USAGE_GUIDE.md](docs/USAGE_GUIDE.md) §7.

| Конкурс | Template | Ключевое | Время подготовки |
|---|---|---|---|
| **CanSat** | `mission_templates/cansat_standard.json` | Парашют, IMU, 500 г | 1 вечер |
| **CubeSat Design** | `mission_templates/cubesat_sso.json` | 3U, CDR docs, HMAC auth | 1 неделя |
| **NASA Space Apps** | Любой + NDVI analyzer | Earth observation | 48 ч |
| **Rocket competition** | `mission_templates/rocket_competition.json` | Dual-deploy | 2–3 дня |
| **HAB** | `mission_templates/hab_standard.json` | GNSS, камера | 1 день |
| **Aerospace Olympiad** | — | `simulation/analytical_solutions.py` | — |

Also: [COMPETITION_GUIDE.md](COMPETITION_GUIDE.md) (short form).

---

## Project Structure

```
unisat/
├── firmware/             # STM32F446 firmware (C11 + FreeRTOS)
│   ├── stm32/Core/       #   OBC, COMM, GNSS, CCSDS, telemetry,
│   │                     #   command_dispatcher (HMAC-auth)
│   ├── stm32/Drivers/    #   9 sensor drivers + AX25 + Crypto +
│   │                     #   VirtualUART (SITL TCP shim)
│   ├── stm32/ADCS/       #   B-dot, quaternion, sun/target pointing
│   ├── stm32/EPS/        #   MPPT, battery manager
│   └── tests/            #   16 Unity test targets
├── flight-software/      # Python async flight controller (RPi Zero 2 W)
├── ground-station/       # Streamlit UI + AX.25 CLI + HMAC tooling
│   ├── utils/ax25.py     #   AX.25 v2.2 Python mirror
│   ├── utils/hmac_auth.py#   HMAC-SHA256 mirror (RFC 4231)
│   ├── cli/              #   ax25_listen / ax25_send TCP tools
│   └── tests/            #   34 pytest incl. hypothesis + fuzz
├── simulation/           # 10 simulators (orbit, power, thermal, link)
├── configurator/         # Web-based mission configurator + BOM gen
├── hardware/             # KiCad schematics, BOM, mechanical CAD
├── payloads/             # 5 swappable payload templates
├── mission_templates/    # 5 ready-to-use mission_config.json
├── tests/golden/         # Shared AX.25 test vectors (C + Python)
├── docs/                 # 25+ md docs (USAGE_GUIDE, TECHNICAL_DOC,
│                         # ADRs, threat model, tutorials, verification)
├── docker/Dockerfile.ci  # Reusable CI image (cmake + pytest baked)
├── scripts/verify.sh     # One-command reproducibility
├── Makefile              # make all / test / demo / ci / help
├── CHANGELOG.md          # Semantic-versioned history
└── README.md             # This file
```

---

## Documentation

**Start here:**
- [USAGE_GUIDE.md](docs/USAGE_GUIDE.md) — step-by-step от клонирования до подачи на конкурс
- [TECHNICAL_DOCUMENTATION.md](docs/TECHNICAL_DOCUMENTATION.md) — полная техническая дока (~1100 строк)
- [GAPS_AND_ROADMAP.md](docs/GAPS_AND_ROADMAP.md) — честный статус + что ещё можно добавить

**CDR-level design docs:**
- [System Architecture](docs/architecture.md) · [Mission Design](docs/mission_design.md)
- [Communication Protocol](docs/communication_protocol.md) (AX.25 + CCSDS wire format)
- [Power Budget](docs/power_budget.md) · [Mass Budget](docs/mass_budget.md) · [Link Budget](docs/link_budget.md)
- [Thermal Analysis](docs/thermal_analysis.md) · [Orbit Analysis](docs/orbit_analysis.md)
- [Testing Plan](docs/testing_plan.md) · [Assembly Guide](docs/assembly_guide.md)
- [API Reference](docs/API_REFERENCE.md) · [Requirements Traceability](docs/REQUIREMENTS_TRACEABILITY.md)

**Architecture decisions, security, verification:**
- [ADR-001 — No CSP](docs/adr/ADR-001-no-csp.md) · [ADR-002 — Style Adapter](docs/adr/ADR-002-style-adapter.md)
- [AX.25 Threat Model](docs/security/ax25_threat_model.md)
- [AX.25 Walkthrough Tutorial](docs/tutorials/ax25_walkthrough.md) — byte-by-byte beacon разбор
- [AX.25 Verification Trace Matrix](docs/verification/ax25_trace_matrix.md) (auto-generated)
- [Driver Reality Audit](docs/verification/driver_audit.md) — все 8 сенсоров verified real
- [Track 1 Design Spec](docs/superpowers/specs/2026-04-17-track1-ax25-design.md) — 775 lines
- [Track 1 Implementation Plan](docs/superpowers/plans/2026-04-17-track1-ax25-implementation.md) — 4022 lines

---

## Testing

**One command:**
```bash
./scripts/verify.sh   # Docker-based, no local toolchain needed
```

**Via Makefile:**
```bash
make all              # build + test (C + Python)
make test-c           # ctest only (16 targets)
make test-py          # pytest only (34 tests + hypothesis/fuzz)
make demo             # end-to-end SITL AX.25 beacon demo
make help             # list all targets
```

**Manual:**
```bash
cd firmware && cmake -B build -S . && cmake --build build
ctest --test-dir build --output-on-failure
cd ../ground-station && python -m pytest tests/test_ax25.py -v
```

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on how to contribute to UniSat.

---

## License

This project is licensed under the MIT License — see [LICENSE](LICENSE) for details.

---

## Acknowledgments

- CCSDS (Consultative Committee for Space Data Systems) for protocol standards
- FreeRTOS for the real-time operating system
- SGP4 algorithm authors for orbit prediction
- CubeSat Design Specification (CalPoly) for mechanical standards
