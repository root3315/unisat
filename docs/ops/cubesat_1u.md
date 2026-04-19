# CubeSat 1U — Operations Guide

Profile key: `cubesat_1u` · Mass cap: **1.33 kg** · Volume: **1135 cm³**
Template: [`mission_templates/cubesat_1u.json`](../../mission_templates/cubesat_1u.json) ·
BOM: [`hardware/bom/by_form_factor/cubesat_1u.csv`](../../hardware/bom/by_form_factor/cubesat_1u.csv)

---

## 1. Mission class

Entry-level orbital mission for universities or first-launch teams.
100 × 100 × 113.5 mm standard CubeSat cell with a single-board OBC,
minimal ADCS (magnetorquer only), and a tech-demo payload.
Typical mission life 3–12 months in a ≤ 450 km decaying LEO.

## 2. Physical envelope

| Parameter              | Value                               |
|------------------------|-------------------------------------|
| Mass cap               | 1.33 kg (CDS rev 14)                |
| Dimensions             | 100 × 100 × 113.5 mm                |
| Volume                 | 1135 cm³                            |
| Power generation       | ~2.5 W orbit-average, body-mounted  |
| Nominal consumption    | 2.0 W                               |
| Battery                | 2× 18650 Li-ion, ~20 Wh             |

## 3. Regulatory context

* **CubeSat Design Specification rev 14** §3.1 (Cal Poly SSDL).
* **ITU frequency coordination** required for amateur UHF 435–438 MHz (typical 1U amateur-radio allocation).
* **Launch provider**: NanoRacks / ISS Kibo, SpaceX Rideshare, ISRO PSLV, etc. — each has its own qualification matrix (ICD, thermal-vac, random-vibration).
* **License**: national space agency approval, FCC experimental licence (US), UK Space Agency license, etc.

## 4. Subsystem matrix

| Subsystem                | Required | Allowed | Forbidden |
|--------------------------|----------|---------|-----------|
| OBC (STM32F446)          | ✅       |         |           |
| EPS                      | ✅       | 4-panel body-mounted | |
| UHF beacon               | ✅       |         |           |
| Magnetorquer ADCS        |          | ✅      |           |
| GNSS                     |          | ✅      |           |
| Camera                   |          | ⚠ (space tight) | |
| S-band downlink          |          |         | ❌ **(registry gate)** |
| Reaction wheels          |          |         | ❌ **(registry gate)** |
| Propulsion               |          |         | ❌        |

The registry's form-factor gate refuses to enable S-band or reaction
wheels on a 1U — there is neither the volume nor the power budget
to support them.

## 5. Build

```bash
make target-cubesat-1u
```

Compile-time macro: `MISSION_PROFILE_CUBESAT_1U=1`. Sets:
* `PROFILE_FEATURE_SBAND=0`
* `PROFILE_FEATURE_WHEELS=0`
* `PROFILE_FEATURE_ADCS_ACTIVE=1` (magnetorquers only)
* `PROFILE_FEATURE_ORBIT_PREDICTOR=1`
* `PROFILE_FEATURE_RADIATION=1`

## 6. Mission config

```bash
cp mission_templates/cubesat_1u.json mission_config.json
```

Fields to review:

* `orbit.altitude_km` / `inclination_deg` — defaults 400 / 51.6° (ISS-like).
* `subsystems.comm_uhf.frequency_mhz` — ITU-coordinated amateur allocation.
* `subsystems.adcs.tier` — `magnetorquer` (enforced by registry).
* `subsystems.payload.type` — describe your experiment.
* `ground_station.location` — your antenna coordinates.

## 7. Mass & volume validation

With the default subsystem set:

| Metric       | Value   | Status |
|--------------|---------|--------|
| Total mass   | 1.258 kg| ≤ 1.33 kg ✅ (limited margin) |
| 20 % margin  | 0.210 kg| included                         |
| Volume used  | 365 cm³ | 32 % of 1135 cm³ ✅             |

A 1U has **very tight** mass margin. Adding a camera typically
requires dropping one solar panel and accepting a 10 % power cut.

## 8. Typical mission phases

Inherited from the `cubesat_leo` mission type:

```
startup → deployment → detumbling → nominal
               ↓ timeout / fault
             safe_mode ⇌ low_power
             science / comm_window (from nominal)
```

Entry points:

| Phase        | Trigger                                      | Duration |
|--------------|----------------------------------------------|----------|
| `startup`    | T+0 s after release                          | 5 min    |
| `deployment` | antennas open + body solar cells deployed    | 30 min   |
| `detumbling` | B-dot controller reduces rates < 0.5 °/s     | ≤ 60 min |
| `nominal`    | long-term operations                         | ongoing  |
| `safe_mode`  | beacon-only when ground contact lost > 24 h  | until ack|

## 9. Testing checklist (ground qualification)

- [ ] Thermal-vacuum cycle: -20 °C to +60 °C, 3 cycles × 4 h, no faults.
- [ ] Random vibration 14 g-rms @ 20 Hz – 2 kHz, 3 axes × 2 min.
- [ ] Sine sweep 5 Hz – 100 Hz at 2 g, check structural resonances.
- [ ] EMC: conducted + radiated emissions per MIL-STD-461 E or equivalent.
- [ ] Deployment dry-run: antennas + solar panels release within 30 s of timer expiry.
- [ ] 48-hour soak test (`UNISAT_SOAK_SECONDS=172800 pytest flight-software/tests/test_long_soak.py`).
- [ ] End-to-end SITL mission (`scripts/simulate_mission.sh mission_config.json`).

## 10. Flight-day checklist

Spacecraft delivery to launch provider:

- [ ] All ICD-required signatures on airworthiness certificate.
- [ ] Flight key loaded; `KeyRotationPolicy` reports `ok`.
- [ ] Remove-before-flight pin installed and tagged.
- [ ] Battery charged to 80 % (long-duration storage floor).
- [ ] Ground-station tracking software loaded with the launch TLE.
- [ ] ITU frequency coordination confirmed in writing.

## 11. Known limitations

* **No redundancy** in OBC / EPS / comms — every subsystem is a single point of failure. Suitable for low-cost first missions, not high-reliability flights.
* **Passive thermal control**: the MLI + kapton heater handles eclipse / insolation swings but cannot respond to prolonged off-nominal attitude. Rely on ADCS to keep the sun-side within 30° of the solar panel normal.
* **Magnetorquer-only ADCS**: no 3-axis pointing, only detumble + sun-tracking. Any imaging payload is coarse (≥ 1° pointing jitter).
* **No S-band**: downlink ≤ 9.6 kbps UHF. Budget imagery accordingly.

## 12. Post-flight debrief

For CubeSats the "post-flight" is the whole mission: debriefs happen
after each ground-station pass.

Per pass, capture:

* AX.25 downlink (PCAP in `flight_logs/<date>_<pass>.pcap`).
* Beacon parameters (voltage, temperature, fault log tail).
* Command log (which commands were sent, how many replies received).

Weekly summary:

* Orbit-average SoC trend (should trend up post-detumble, stable in nominal).
* Fault counts from FDIR telemetry (any escalation?).
* Reboot count from FDIR persistent meta (reboot-loop guard should read 0).

File monthly mission-status reports under `docs/operations/flight_reports/`.

---

**Previous profile**: [cansat_advanced.md](cansat_advanced.md) · **Next profile**: [cubesat_1_5u.md](cubesat_1_5u.md)
