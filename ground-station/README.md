# UniSat Ground Station

Streamlit-based mission control with 10 interactive pages.

## Quick Start

```bash
cd ground-station
pip install -r requirements.txt
streamlit run app.py
```

Open http://localhost:8501 in your browser.

## Pages

| # | Page | Description |
|---|------|-------------|
| 01 | Dashboard | Mission status, subsystem health indicators |
| 02 | Telemetry | Real-time Plotly charts (temp, voltage, radiation) |
| 03 | Orbit Tracker | 3D globe with ground track and satellite position |
| 04 | Image Viewer | Earth observation gallery with geolocation |
| 05 | ADCS Monitor | Quaternion display, reaction wheel gauges |
| 06 | Power Monitor | Battery SOC gauge, solar vs consumption charts |
| 07 | Command Center | HMAC-authenticated telecommand interface |
| 08 | Mission Planner | Pass predictions, imaging schedule |
| 09 | Data Export | Download telemetry as CSV/JSON/CCSDS |
| 10 | Health Report | Anomaly detection, system diagnostics |

## Utilities

| Module | Description |
|--------|-------------|
| `utils/telemetry_decoder.py` | Decode CCSDS packets by APID |
| `utils/ccsds_parser.py` | Parse raw bytes, CRC-16 validation |
| `utils/orbit_visualizer.py` | SGP4 propagation, pass prediction |
| `utils/map_renderer.py` | Plotly globe/map figure builders |

## Demo Mode

By default, the ground station runs with simulated data. To connect to real hardware, configure the serial port in the sidebar settings.

## Adding a Custom Page

Create `pages/11_my_page.py`:
```python
import streamlit as st
st.set_page_config(page_title="My Page", layout="wide")
st.title("My Custom Page")
# Your visualization code here
```

Streamlit auto-discovers pages in the `pages/` directory.
