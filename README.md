<p align="center">
  <img src="docs/diagrams/system_block_diagram.svg" alt="UniSat Logo" width="600">
</p>

<h1 align="center">UniSat — Universal Modular CubeSat Platform</h1>

<p align="center">
  <a href="https://github.com/root3315/unisat/actions"><img src="https://img.shields.io/github/actions/workflow/status/root3315/unisat/ci.yml?branch=main&label=CI&logo=github" alt="CI"></a>
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
| **Communication** | UHF 9600 bps + S-band 256 kbps | AX.25, CCSDS packets |
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

### 5. Build firmware

```bash
cd firmware
mkdir build && cd build
cmake ..
make
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

UniSat is designed to be adapted for various aerospace competitions. See [COMPETITION_GUIDE.md](COMPETITION_GUIDE.md) for detailed instructions:

- **CanSat** — Remove orbital modules, add parachute descent
- **CubeSat Design** — Full configuration, CDR-level documentation
- **NASA Space Apps** — Focus on Earth observation and data analysis
- **Aerospace Olympiad** — Theoretical justification with simulation data
- **Hackathon** — Quick prototype using the web configurator

---

## Project Structure

```
unisat/
├── firmware/          # STM32 firmware (C + FreeRTOS)
├── flight-software/   # Flight controller (Python + asyncio)
├── ground-station/    # Ground station (Streamlit + Plotly)
├── simulation/        # Mission simulation tools
├── configurator/      # Web-based mission configurator
├── hardware/          # KiCad schematics, mechanical CAD
├── payloads/          # Swappable payload modules
├── docs/              # CDR-level documentation
└── scripts/           # Build, test, deploy scripts
```

---

## Documentation

All documentation is written to CDR (Critical Design Review) standards:

- [System Architecture](docs/architecture.md)
- [Mission Design](docs/mission_design.md)
- [Communication Protocol](docs/communication_protocol.md)
- [Power Budget](docs/power_budget.md)
- [Mass Budget](docs/mass_budget.md)
- [Link Budget](docs/link_budget.md)
- [Thermal Analysis](docs/thermal_analysis.md)
- [Orbit Analysis](docs/orbit_analysis.md)
- [Testing Plan](docs/testing_plan.md)
- [Assembly Guide](docs/assembly_guide.md)

---

## Testing

```bash
# Run all Python tests
./scripts/run_tests.sh

# Run specific test suites
pytest flight-software/tests/ -v
pytest ground-station/tests/ -v

# Build and test firmware
cd firmware/build && cmake .. && make
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
