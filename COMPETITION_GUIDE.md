# Competition Adaptation Guide

UniSat is designed to be easily adapted for various aerospace competitions. This guide explains how to configure the platform for each competition type.

---

## CanSat

**Focus:** Atmospheric descent with sensor data collection.

Since v1.3.0 CanSat is a **first-class profile** — no hand-editing
needed. Three variants ship out of the box:

| Profile | Regulation | Envelope | Use |
|---|---|---|---|
| `cansat_minimal` | ≤350 g | Ø66 × 115 mm | Telemetry-only, first CanSat |
| `cansat_standard` | ≤500 g, CDS | Ø68 × 80 mm | Standard ESERO / AAS |
| `cansat_advanced` | ≤500 g | Ø68 × 115 mm | Pyro parachute + camera |

### Setup

```bash
cp mission_templates/cansat_standard.json mission_config.json
# Edit mission.name, mission.operator — that's it.

make target-cansat_standard   # firmware binary for the chosen profile
make configurator             # optional: Streamlit UI to tweak subsystems
```

### What you get automatically

- Parachute deployment logic (`payloads/cansat_descent/`) with
  configurable descent rate, deploy altitude, and drogue chute.
- Sensor-driven phase transitions (launch → apogee → descent → landed)
  in `flight-software/flight_controller.py`.
- Ground-station dashboard hides orbit / imagery / ADCS pages for
  CanSat profiles — you see only what's relevant.
- Reference BOM at `hardware/bom/by_form_factor/cansat_standard.csv`
  (≈170 g kit, ≈330 g payload headroom under the 500 g limit).

### Competition scoring coverage (regulation 2026)

| Criterion | Max | What UniSat already gives you |
|---|---:|---|
| Documentation | 15 | `docs/design/universal_platform.md`, SRS, traceability CSV |
| Hardware design | 10 | Reference BOM + KiCad boards + mechanical spec |
| Software | 10 | FDIR, HMAC auth, 262 flight-software tests |
| Data collection / tx | 20 | LoRa + GNSS + IMU + baro, CSV logger, 10 Hz beacon |
| Science mission | 15 | *You provide the hypothesis and the extra sensor* |
| Test flight | 10 | SITL simulator (`run_cansat.py`) + HIL plan |
| Presentation | 20 | `docs/project/POSTER_TEMPLATE.md`, PDF/PNG export |

### Key deliverables (what judges expect)

- Sensor data collection (temperature, pressure, humidity, GPS, IMU)
- Real-time telemetry transmission (LoRa 433/868 MHz)
- Post-flight CSV dump + trajectory / descent-rate analysis
- Parachute deployment logic (built-in) with descent rate in the
  competition band (6–11 m/s)
- Mass check ≤ 500 g with 15 % margin — validator in `make configurator`

---

## CubeSat Design Competition

**Focus:** Full satellite design with CDR-level documentation.

### Configuration
Use the default `mission_config.json` — UniSat is already configured for a 3U CubeSat mission.

### Key Deliverables
- Complete `docs/` folder serves as CDR documentation
- `docs/design/architecture.md` — system block diagram
- `docs/budgets/power_budget.md` — detailed power analysis
- `docs/budgets/mass_budget.md` — component mass with margins
- `docs/budgets/link_budget.md` — communication link analysis
- `docs/budgets/thermal_analysis.md` — thermal environment modeling
- `docs/budgets/orbit_analysis.md` — orbit selection justification
- Run `simulation/mission_analyzer.py` for quantitative results
- Use `configurator/` to generate professional PDF reports

### Tips
- Customize `mission.operator` and `mission.name`
- Run all simulations and include output plots
- Emphasize modularity and scalability in presentation

---

## NASA Space Apps Challenge

**Focus:** Earth observation and data analysis.

### Configuration Changes

1. **mission_config.json:**
   - Enable `camera` with maximum resolution
   - Set `spectral_bands` based on challenge requirements
   - Configure appropriate orbit for target area

2. **Emphasize these modules:**
   - `flight-software/modules/image_processor.py` — SVD compression, geotagging
   - `ground-station/pages/04_image_viewer.py` — image gallery with map overlay
   - `simulation/orbit_simulator.py` — ground track for target coverage
   - `ground-station/pages/08_mission_planner.py` — imaging schedule

3. **Add data analysis:**
   - Create Jupyter notebooks in a `notebooks/` directory
   - Process sample satellite imagery
   - Generate NDVI or other indices from multispectral data

### Key Deliverables
- Working ground station with image visualization
- Orbit simulation showing coverage of target areas
- Data processing pipeline demo
- Environmental monitoring use case

---

## Aerospace Olympiad

**Focus:** Theoretical knowledge and calculations.

### What to Use
- `docs/budgets/orbit_analysis.md` — orbital mechanics fundamentals
- `docs/budgets/link_budget.md` — communication theory
- `docs/budgets/power_budget.md` — energy balance calculations
- `docs/budgets/thermal_analysis.md` — heat transfer in space
- `simulation/` — numerical verification of analytical results

### Preparation
1. Study each `docs/` file for theoretical background
2. Run simulations to verify hand calculations
3. Use `configurator/` to explore how parameters affect system design
4. Understand trade-offs between form factors, orbits, and subsystems

### Key Topics Covered
- Kepler's laws and orbital elements
- J2 perturbation effects
- Solar panel efficiency and eclipse cycles
- Friis transmission equation and link margins
- Thermal equilibrium in LEO
- CCSDS packet structure
- Attitude determination and control fundamentals

---

## Hackathon (24-48 hours)

**Focus:** Rapid prototype demonstrating key capabilities.

### Quick Start Strategy

**Hour 1-2:** Setup
```bash
git clone https://github.com/root3315/unisat.git
cd unisat && ./scripts/setup.sh
```

**Hour 2-6:** Customize
- Edit `mission_config.json` for your mission concept
- Run `configurator/configurator_app.py` to validate
- Pick 1-2 payloads to focus on

**Hour 6-12:** Demo
- Launch ground station: `streamlit run ground-station/app.py`
- Run mission simulation: `python simulation/mission_analyzer.py`
- Generate PDF report via configurator

**Hour 12-24:** Polish
- Customize ground station theme/branding
- Add your team's payload implementation
- Prepare presentation with simulation screenshots

### Minimal Viable Demo
1. Ground station running with simulated telemetry
2. Orbit visualization on 3D globe
3. Mission configurator generating valid configs
4. One working payload module
5. PDF mission report

---

## General Tips

1. **Always customize `mission_config.json`** — judges want to see your specific mission, not a generic template
2. **Run simulations** — quantitative results are more convincing than qualitative claims
3. **Use the ground station** — visual demos make strong impressions
4. **Document your changes** — keep a log of what you modified and why
5. **Understand the code** — be prepared to explain any part of the system
6. **Test everything** — run `./scripts/run_tests.sh` before presenting
