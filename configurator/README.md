# UniSat Mission Configurator

Web-based mission builder with automatic budget validation.

## Quick Start

```bash
cd configurator
pip install -r requirements.txt
streamlit run configurator_app.py
```

## Features

- **Form Factor Selection**: 1U / 2U / 3U / 6U with templates
- **Subsystem Toggle**: Enable/disable each subsystem
- **Budget Validation**: Mass, power, and volume checks in real-time
- **Config Generator**: Export `mission_config.json`
- **Report Generator**: Text mission summary
- **BOM Generator**: Bill of Materials with pricing

## Validators

| Validator | Checks | Limits |
|-----------|--------|--------|
| `mass_validator.py` | Total mass with 20% margin | 1U: 1.33kg, 3U: 4.0kg |
| `power_validator.py` | Generation vs consumption | Net positive required |
| `volume_validator.py` | Component fit | Per form factor dimensions |

## Templates

Pre-configured mission profiles in `templates/`:
- `1u_default.json` — CanSat / minimal
- `2u_default.json` — Technology demo
- `3u_default.json` — Earth observation (recommended)
- `6u_default.json` — Full capability

## Generators

| Generator | Output |
|-----------|--------|
| `config_generator.py` | `mission_config.json` |
| `report_generator.py` | Mission report (text/PDF) |
| `bom_generator.py` | Components CSV with pricing |
