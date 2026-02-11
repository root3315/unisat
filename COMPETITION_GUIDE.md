# Competition Adaptation Guide

UniSat is designed to be easily adapted for various aerospace competitions. This guide explains how to configure the platform for each competition type.

---

## CanSat

**Focus:** Atmospheric descent with sensor data collection.

### Configuration Changes

1. **mission_config.json:**
   - Set `form_factor` to `"1U"` or `"custom"`
   - Disable `adcs` (no attitude control needed)
   - Disable `gnss` or keep for GPS tracking
   - Disable `s_band` (use only UHF or LoRa)
   - Set `orbit.type` to `"suborbital"`
   - Set `orbit.altitude_km` to launch altitude (e.g., 1.0)

2. **Add parachute module:**
   - Create `payloads/parachute/` with descent rate calculations
   - Modify `flight_controller.py` to include deployment sequence

3. **Simplify ground station:**
   - Focus on `02_telemetry.py` for real-time data
   - Remove orbit tracker (not applicable)
   - Add descent trajectory visualization

### Key Deliverables
- Sensor data collection (temperature, pressure, humidity, GPS)
- Real-time telemetry transmission
- Post-flight data analysis
- Parachute deployment logic

---

## CubeSat Design Competition

**Focus:** Full satellite design with CDR-level documentation.

### Configuration
Use the default `mission_config.json` — UniSat is already configured for a 3U CubeSat mission.

### Key Deliverables
- Complete `docs/` folder serves as CDR documentation
- `docs/architecture.md` — system block diagram
- `docs/power_budget.md` — detailed power analysis
- `docs/mass_budget.md` — component mass with margins
- `docs/link_budget.md` — communication link analysis
- `docs/thermal_analysis.md` — thermal environment modeling
- `docs/orbit_analysis.md` — orbit selection justification
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
- `docs/orbit_analysis.md` — orbital mechanics fundamentals
- `docs/link_budget.md` — communication theory
- `docs/power_budget.md` — energy balance calculations
- `docs/thermal_analysis.md` — heat transfer in space
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
