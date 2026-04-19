# CubeSat 3U — Operations Guide

Profile key: `cubesat_3u` · Mass cap: **4.0 kg** · Volume: **3405 cm³**
Template: [`mission_templates/cubesat_3u.json`](../../mission_templates/cubesat_3u.json) ·
BOM: [`hardware/bom/by_form_factor/cubesat_3u.csv`](../../hardware/bom/by_form_factor/cubesat_3u.csv)

---

## 1. Mission class

**UniSat TRL-5 reference profile** — every subsystem in the project
is characterised against this envelope. 3U is also the most common
professional CubeSat size worldwide: single 1U payload bay plus
2U platform for EPS / ADCS / comms.

Suitable for: Earth observation, technology demonstration, rideshare
constellations (Kepler, Lemur), university flagship missions.

## 2. Physical envelope

| Parameter              | Value                               |
|------------------------|-------------------------------------|
| Mass cap               | 4.0 kg                              |
| Dimensions             | 100 × 100 × 340.5 mm                |
| Volume                 | 3405 cm³                            |
| Power generation       | ~8.0 W orbit-average (body-mounted) |
| Nominal consumption    | 6.0 W                               |
| Battery                | 2P3S 18650, ~60 Wh                  |

Add deployable solar panels for ~20 W generation if the mission
budget allows; not assumed in the default BOM.

## 3. Regulatory context

* **CDS rev 14 §3.1** — 3U standard.
* **ITU**: UHF + S-band coordination, or deep-space DSN request for very niche missions.
* **Launch provider**: NanoRacks, ISILaunch, D-Orbit ION, SpaceX Rideshare — well-trodden ICDs.
* **Orbital-debris**: end-of-life plan required (< 25-year decay for LEO).

## 4. Subsystem matrix

| Subsystem            | Status |
|----------------------|--------|
| Reaction wheels ADCS | ✅ (3 axes, first allowed here) |
| Magnetorquer detumble| ✅    |
| Star tracker         | ⚠ (optional, adds 150 g)    |
| UHF telemetry        | ✅    |
| S-band downlink      | ✅    |
| GNSS                 | ✅    |
| Camera (12 MP)       | ✅    |
| Payload              | ✅    |
| Propulsion           | ⚠ (cold-gas fits, electric needs 6U+) |

## 5. Build

```bash
make target-cubesat-3u
```

Compile-time macro: `MISSION_PROFILE_CUBESAT_3U=1` (also the default
when no `-D` is passed). Sets:

* `PROFILE_FEATURE_WHEELS=1` (first profile that allows this).
* `PROFILE_FEATURE_SBAND=1`.
* `PROFILE_FEATURE_IMAGERY=1`.
* `PROFILE_FEATURE_RADIATION=1`.

## 6. Mission config

```bash
cp mission_templates/cubesat_3u.json mission_config.json
```

Key fields:

* `orbit.altitude_km` / `inclination_deg` — default 550 / 97.6° SSO.
* `subsystems.adcs.tier` — `wheels` (first profile where this resolves).
* `subsystems.adcs.star_tracker` — true if fitted.
* `subsystems.payload.type` — your payload.
* `mission.telemetry_hz` — 1.0 Hz default; up to 4 Hz if S-band pass budget permits.

## 7. Mass & volume validation

| Metric       | Value   | Status |
|--------------|---------|--------|
| Total mass   | 3.55 kg | ≤ 4.0 kg ✅ (11 % margin) |
| Volume used  | 1180 cm³| 35 % of 3405 cm³ ✅       |

Adding a star tracker + extra battery cells uses ~70 % of the
remaining margin — still flight-approvable.

## 8. Typical mission phases

```
startup → deployment → detumbling → nominal ⇌ science / comm_window / low_power
                                        ↓ fault
                                    safe_mode
                                        ↓ ack
                                    nominal
```

Reference timings:

| Phase        | Nominal duration          |
|--------------|---------------------------|
| `startup`    | 5 min (post-release)      |
| `deployment` | 30 min (antennas, panels) |
| `detumbling` | 30–90 min (B-dot)         |
| `nominal`    | ongoing                   |
| `science`    | 10–20 min bursts / orbit  |
| `comm_window`| 6–10 min passes           |
| `low_power`  | eclipse-driven, ~30 min   |
| `safe_mode`  | until ground ack          |

## 9. Testing checklist (ground qualification)

> **Legend:** `[x]` = verified in software / CI / SITL (passes in the current release); `[ ]` = requires bench hardware, RF range test, or flight-day field activity — team must sign off manually.


- [ ] **Thermal-vacuum**: -20 °C to +60 °C, 5 cycles, 6 h each (typical launch provider ICD).
- [ ] **Random vibration**: 14 g-rms, 3 axes, 2 min each.
- [ ] **Shock**: half-sine 1500 g, 0.5 ms, one shot per axis.
- [ ] **EMC**: MIL-STD-461E CE102 / RE102.
- [ ] **Thermal cycling**: 8 cycles from -40 °C to +85 °C at board level.
- [ ] **Radiation**: 60Co TID to 2 krad (see `docs/hardware/radiation_budget.md`).
- [x] **48-hour soak**: `UNISAT_SOAK_SECONDS=172800 pytest flight-software/tests/test_long_soak.py`.
- [x] **End-to-end SITL**: `scripts/simulate_mission.sh mission_config.json` ≥ 1 orbit.

## 10. Flight-day checklist

Same as 2U plus:

- [ ] Reaction-wheel bias torque characterised and stored in NV memory.
- [ ] Magnetic offset of final satellite measured and encoded in ADCS config.
- [ ] Star-tracker dark-frame calibration uploaded if fitted.
- [ ] Downlink key rotated at T-7 days; `KeyRotationPolicy.counter_used == 0`.

## 11. Known limitations

* **Magnetic torquers lose authority near the magnetic equator** — 3U reference attitude accuracy is 0.5° with wheels, 2° without.
* **Deep-space or beyond 800 km** requires a rad-hard secondary OBC; UniSat 1.x targets ≤ 700 km.
* **Propulsion-on-3U** budgets are tight — stick with attitude impulse (magnetorquer + wheel desat), not station-keeping.

## 12. Post-flight debrief

This is the reference profile; log the most data:

* Every pass: AX.25 PCAP, raw telemetry, command log, image thumbnails.
* Daily: SoC profile, wheel momentum, FDIR fault count, reboot count.
* Weekly: orbit decay trend from TLE vs. prediction, SADM + thermal performance.
* Monthly: science data products, publication-ready plots.

Canonical location: `docs/operations/flight_reports/` with
sub-folders by month.

---

**Previous profile**: [cubesat_2u.md](cubesat_2u.md) · **Next profile**: [cubesat_6u.md](cubesat_6u.md)
