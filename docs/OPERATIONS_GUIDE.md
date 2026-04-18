# UniSat Operations Guide — from start to finish

This guide walks a team from an empty checkout to a flown mission for
any supported vehicle class: **CanSat** (minimal / standard / advanced),
**CubeSat** 1U through 12U, suborbital rocket payload, HAB, drone, or
custom. One code base, one firmware source tree, one ground station —
the target profile is chosen at build time.

If you are new, read §1–§4 top to bottom. If you already have a bench
set up, skip to §5 (firmware build) or §7 (ground-station bring-up).

---

## 1. Decide the mission profile

Pick exactly one:

| Profile key | Regulation | Good for |
|---|---|---|
| `cansat_minimal` | ESA CanSat 350 g | First CanSat, pure telemetry, Ø66 × 115 mm can |
| `cansat_standard` | ESA CanSat 500 g, CDS Ø68 | Standard ESERO / AAS CanSat, 80 mm height |
| `cansat_advanced` | 500 g, 115 mm tall | Pyro parachute + on-board camera |
| `cubesat_1u`      | CDS Rev. 14 | CubeSat educational / amateur |
| `cubesat_1_5u`    | CDS Rev. 14 | Intermediate when 1U is too tight |
| `cubesat_2u`      | CDS Rev. 14 | Technology demo + optional S-band |
| `cubesat_3u`      | CDS Rev. 14 | Workhorse LEO — **default profile** |
| `cubesat_6u`      | NASA 6U envelope | Fine pointing, X/Ka-band |
| `cubesat_12u`     | Research class | Star tracker + propulsion |
| `rocket_payload`  | Launch provider | Sounding / student rockets |
| `hab_payload`     | FAA Part 101 | High-altitude balloon |
| `drone_small`     | National CAA | ≤5 kg UAS |
| `rover_small`     | n/a (ground) | Surface rover |
| `custom`          | user-defined | Bespoke shape, no built-in checks |

The full envelope (mass, volume, power, allowed ADCS tiers, allowed
radio bands) is in `flight-software/core/form_factors.py`. The Streamlit
configurator shows the same data with live validation — use it when
designing a new mission.

## 2. Start a new mission

```bash
cp mission_templates/<profile_key>.json  mission_config.json
```

Open `mission_config.json` and fill in:
- `mission.name`, `mission.operator` (team name)
- orbit / launch parameters for CubeSat profiles
- `satellite.mass_kg` — **must stay inside the regulation limit** for
  the form factor; the configurator validator will flag overshoot.

For CanSat teams: remember the 170 g / 500 g distinction — the
reference BOM weighs ≈170 g, and the **remaining ≈330 g is your
science-payload headroom**. The regulation cutoff is 500 g, not 170 g.

## 3. Install tooling

### 3.1 Python side (flight-software + ground station + configurator)

```bash
python -m venv venv
. venv/Scripts/activate       # Windows
# or: source venv/bin/activate  (Linux/Mac)

pip install -r flight-software/requirements.txt
pip install -r ground-station/requirements.txt
pip install -r simulation/requirements.txt
pip install pytest pytest-cov ruff mypy
```

### 3.2 C side (firmware)

The host build pipeline works **without** an ARM toolchain — it compiles
the firmware tree as a static library for unit tests. For a real flight
binary you also need:

```bash
# Ubuntu/Debian
sudo apt-get install cmake gcc-arm-none-eabi

# macOS (Homebrew)
brew install cmake && brew tap ArmMbed/homebrew-formulae && brew install arm-none-eabi-gcc

# Windows — install ARM GNU toolchain from Arm developer site and add to PATH
```

Then one-time dependency fetch:

```bash
make setup-all        # pulls STM32Cube HAL + FreeRTOS kernel
```

### 3.3 Sanity check

```bash
./scripts/verify.sh   # Docker-based, runs the full green pipeline
```

Expected last line: `✓ UniSat green. Ready to submit.`

## 4. Explore the mission in simulation

```bash
# CanSat end-to-end flight with simulated sensors
python flight-software/run_cansat.py --max-altitude 500 --descent-rate 8.0
```

Expected output: `PRE_LAUNCH → LAUNCH_DETECT → ASCENT → APOGEE →
DESCENT → LANDED`, followed by a competition-requirement report
(descent rate, landing velocity, telemetry sample count).

For CubeSat profiles, run a full-mission analysis:

```bash
python simulation/mission_analyzer.py
```

## 5. Build the firmware for your profile

One firmware source tree → one binary per mission profile. Each
`make target-<profile>` defines `-DMISSION_PROFILE_<NAME>=1` so the
build includes only the subsystems the profile needs.

```bash
make target-cansat_standard     # -> firmware/build-arm-cansat_standard/
make target-cubesat_3u          # -> firmware/build-arm-cubesat_3u/
make target-cubesat_6u          # -> firmware/build-arm-cubesat_6u/
# ... etc for every profile registered in mission_profile.h
```

Each produces `unisat_firmware.{elf,bin,hex}` and a size report. The
CubeSat-3U reference has been verified on hardware: 31.6 KB flash
(6 % of an STM32F446), 36.3 KB RAM (28 %). Other profiles fit the
same chip with headroom.

### 5.1 Flash to the board

```bash
make flash                      # ST-Link to Nucleo-F446RE
# or:
st-flash write firmware/build-arm-cubesat_3u/unisat_firmware.bin 0x08000000
```

### 5.2 Run host tests

```bash
make test-c                     # 27 ctest targets
make test-py                    # pytest incl. full mission E2E
make coverage                   # 85 %+ C line coverage
make cppcheck                   # static-analysis gate
```

## 6. Fill the bill of materials

`hardware/bom/by_form_factor/` has a reference BOM per class. Copy the
one matching your profile, substitute with parts you can actually
procure, and verify the TOTAL stays within the regulation limit.

**For CanSat teams specifically:** the CSV TOTAL row shows the kit
mass (130–250 g). Your **final built CanSat with the science payload
must still be ≤500 g** — so the headroom column in the BOM README is
what you have for the experiment.

## 7. Bring up the ground station

```bash
cd ground-station && streamlit run app.py
```

The dashboard has 13 pages; three of them (orbit tracker, image viewer,
ADCS monitor) are gated by `utils/profile_gate.py` and **hide
automatically** when you run a CanSat, HAB, drone, or rover mission.

If you launch UHF/VHF HAM-band hardware, point the radio CLI at your
TNC:

```bash
python -m cli.ax25_listen --tcp localhost:52100
python -m cli.ax25_send  --tcp localhost:52100 --src UN8SAT-1 \
    --dst GS0TEST-1 --msg "HELLO WORLD"
```

For CanSat / HAB with ISM / LoRa radios, substitute your radio's TCP
bridge (LoRa gateway, APRS digipeater) for the AX.25 CLI.

## 8. Bench / Hardware-in-the-loop test

`docs/testing/hil_test_plan.md` has a 10-item test matrix — bench BOM,
procedure per test, pass/fail criteria. Minimum gates before flight:

1. **Power**: 60-minute continuous run on the chosen battery chemistry.
2. **Radio range**: confirm link budget at the ground-separation you
   actually expect (launch field, balloon burst altitude, …).
3. **Sensor plausibility**: IMU and barometer produce sane values when
   the vehicle sits on the bench and when shaken by hand.
4. **Telemetry decoder round-trip**: receive a frame you transmitted
   and read the temperature on the dashboard.
5. **Safe-mode entry/exit**: pull power for 10 s — the state machine
   must come back up in `SAFE` and recover to `NOMINAL` on its own.
6. **Drop test (CanSat only)**: 10–50 m drop from a UAV or balloon,
   parachute deploys, descent rate in the 6–11 m/s competition band.

If any of these fails, don't fly yet — investigate first.

## 9. Pre-launch checklist

Print and walk through `docs/operations/commissioning_runbook.md`. The
short form:

- [ ] Mass check on a precision scale ≤ regulation limit
- [ ] Dimension check against the profile envelope
- [ ] Battery at ≥ 90 % SoC
- [ ] Firmware matches the committed SHA (`make pin-docker` then
      `git rev-parse HEAD` logged into mission log)
- [ ] HMAC key loaded in flight (see key-store documentation under
      `docs/reliability/` and `docs/security/`)
- [ ] Ground station acks the beacon at least 30 s continuously
- [ ] Safe-mode exit has been demonstrated at the launch site
- [ ] GO/NO-GO poll: OPS, RF, EPS, ADCS (CubeSat only), PAYLOAD

## 10. Flight day

Two roles, minimum:

**OPS** watches `02_telemetry.py` on the ground-station dashboard and
logs phase transitions as they happen.

**RF** watches link margin (`06_link_budget.py`) and the AX.25 /
ISM-band decoder terminal for dropped frames.

If the vehicle goes silent for > 30 s:
1. Check the antenna orientation — most telemetry gaps are LOS issues.
2. Do **not** power-cycle the ground station — it buffers the last
   two minutes of telemetry.
3. Wait one full beacon interval before declaring lost.

## 11. Post-flight analysis

```bash
# CanSat: pull the SD-card CSV from the retrieved vehicle
cp /media/sdcard/flight_YYYYMMDD_HHMMSS.csv data/
python scripts/analyze_cansat_flight.py data/flight_*.csv
# → produces altitude profile, descent-rate plot, GPS track
```

For CubeSat, the telemetry archive on the ground station is already
post-processable — the Streamlit dashboard pages show the full mission
as time-series plots and let you export PNG / PDF.

## 12. Competition submission

Document what you flew:

- **Report** — mission, design, science rationale, results. Start from
  `docs/POSTER_TEMPLATE.md` or `docs/TECHNICAL_DOCUMENTATION.md`.
- **Bill of materials** — your modified `hardware/bom/.../*.csv`.
- **Test evidence** — bench-test video, drop-test video, mass-check
  photo, radio-link margin plot.
- **Source code archive** — `git archive --format zip -o unisat.zip HEAD`.
- **Pre-launch / flight / post-flight logs** — paper or screenshots,
  whichever the competition requires.

---

## Quick reference — one command per task

| Task | Command |
|---|---|
| Full green pipeline in Docker | `./scripts/verify.sh` |
| Host build + all tests | `make all` |
| Build firmware for profile X | `make target-<profile>` |
| Flash to Nucleo-F446RE | `make flash` |
| Launch configurator UI | `make configurator` |
| Launch ground station | `cd ground-station && streamlit run app.py` |
| Simulate CanSat flight | `python flight-software/run_cansat.py` |
| Simulate CubeSat mission | `python simulation/mission_analyzer.py` |
| Mass / volume validator (CLI) | `python -m configurator.validators.mass_validator` |
| Regenerate SBOM | `make sbom` |
| Regenerate AX.25 goldens | `make goldens` |

## Troubleshooting

Issue | Likely cause | Fix
---|---|---
`make target-<profile>` — "unknown profile" | Profile not registered in `firmware/stm32/Core/Inc/mission_profile.h` | Add the macro there + add to `form_factors.py`
Streamlit "module not found" | venv not activated | Re-run `. venv/Scripts/activate`
Mass validator over-reports | Old config used "1U" alias | Switch to canonical `cubesat_1u`; alias still works but canonical is future-proof
Pyserial missing under tests | Optional dep, skipped on CI | `pip install pyserial` locally if you need the hardware-loop tests

---

*Keep this guide short enough to stay useful. For deep design docs
start from `docs/architecture.md` and `docs/universal_platform.md`.*
