# UniSat Simulation Suite

Mission simulation tools for orbit, power, thermal, and link budget analysis.

## Available Simulators

| Module | Description | Output |
|--------|-------------|--------|
| `orbit_simulator.py` | Keplerian + J2 propagation | Ground track, lat/lon/alt |
| `power_simulator.py` | Eclipse cycles, solar generation | SOC profile, energy balance |
| `thermal_simulator.py` | 6-face thermal model | Temperature per face over time |
| `link_budget_calculator.py` | Friis equation, SNR, BER | Link margin, max data rate |
| `mission_analyzer.py` | Combined analysis | Full mission report |
| `visualize.py` | Plotly chart generation | HTML interactive plots |
| `ndvi_analyzer.py` | Vegetation index from multispectral | NDVI map, classification |
| `analytical_solutions.py` | Closed-form orbital mechanics | Exact solutions for validation |

## Quick Start

```bash
cd simulation
pip install -r requirements.txt
python mission_analyzer.py      # Full analysis
python analytical_solutions.py  # Analytical solutions
python ndvi_analyzer.py         # NDVI demo
```

## Running Individual Simulations

```bash
python orbit_simulator.py      # 1.5 orbits ground track
python power_simulator.py      # 3 orbits power budget
python thermal_simulator.py    # 3 orbits thermal
python link_budget_calculator.py  # UHF + S-band budgets
```

## Generating Plots

```bash
python visualize.py  # Saves HTML files: ground_track, power_budget, thermal
```

## Customizing Parameters

All simulators read from `../mission_config.json`. Change orbit altitude, inclination, panel count, etc. and re-run.

## For Competitions

- **CubeSat Design**: Run `mission_analyzer.py` for quantitative results
- **Olympiad**: Use `analytical_solutions.py` for theoretical validation
- **NASA Space Apps**: Use `ndvi_analyzer.py` for Earth observation analysis
