# UniSat Lab — interactive Streamlit playground

One browser tab that exposes every hands-on surface of the repo:

- Form-factor registry (mass / volume / power / bands)
- Mission-profile picker + live envelope validator
- CanSat SITL with live altitude + velocity charts
- Per-profile bill of materials viewer + CSV download
- Test runner (pytest / ruff / mypy) with streamed output
- Firmware compile-time profile matrix

## Run

```bash
# from the repo root
pip install streamlit pandas                    # one-time
streamlit run tools/playground.py
```

Windows CMD:

```cmd
venv\Scripts\activate
streamlit run tools\playground.py
```

Opens at <http://localhost:8501> by default.

## Tabs

### 1. Form factors

Browse all 14 registered form factors from `flight-software/core/form_factors.py`. Filter by family (CanSat / CubeSat / rocket / HAB / drone / rover). Click a row to see ADCS tiers, radio bands, and regulation notes for that class.

### 2. Mission profile

Pick a mission type, toggle subsystems, see in real time whether the resulting configuration stays inside the form-factor envelope (mass / volume / power). Expands into a full feature-flag resolver readout showing which optional modules the platform would enable.

### 3. CanSat SITL

Simulate a CanSat flight with adjustable max altitude (100–1500 m) and target descent rate (3–15 m/s). Produces a live altitude + velocity chart, per-phase sample counts, and a competition verdict (descent rate inside [6, 11] m/s window or not).

Uses the same dynamics model as `flight-software/run_cansat.py` — kept as a pure function so results feed straight into Streamlit charts.

### 4. Bill of materials

Pick any of the 10 per-form-factor BOMs under `hardware/bom/by_form_factor/`. Shows line items + kit mass. Download the raw CSV.

### 5. Test runner

Run pytest per suite (flight-software / ground-station / configurator / simulation), `ruff check`, or `mypy --strict` from the browser. Output streams back into a code block with pass/fail status.

### 6. Firmware

Shows the 9 compile-time firmware profiles (`make target-<profile>`), their macros in `mission_profile.h`, and the measured baseline footprint (31.6 KB flash / 36.3 KB RAM on STM32F446RE).

## Not meant for

- Live flight operations — use `ground-station/app.py` (that's the 13-page Streamlit dashboard wired into real telemetry).
- Mission configuration generation — use `configurator/configurator_app.py` for the full wizard that produces `mission_config.json`.
