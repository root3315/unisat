# Rocket Avionics Bay — Operations Guide

Profile key: `rocket_avionics` · Mass cap: **500 g** · Volume: **250 cm³**
Template: [`mission_templates/rocket_competition.json`](../../mission_templates/rocket_competition.json) ·

---

## 1. Mission class

Competition-class suborbital rocketry avionics (IREC / SA Cup / Team
America). 50 × 50 × 100 mm bay that sits inside the rocket's
electronics coupler, drives dual-deploy parachute pyrotechnics, and
logs flight data at high rate.

## 2. Physical envelope

| Parameter              | Value                               |
|------------------------|-------------------------------------|
| Mass cap               | 500 g                               |
| Dimensions             | 50 × 50 × 100 mm (rail envelope)    |
| Volume                 | 250 cm³                             |
| Power generation       | 0 W (battery-only)                  |
| Nominal consumption    | 2.0 W                               |
| Battery                | 2× 14500 Li-ion, ~3 Wh              |

## 3. Regulatory context

* **IREC (Spaceport America Cup)** rulebook — thrust-weight ≥ 5,
  dual-deploy parachute mandatory above 10 000 ft AGL.
* **NAR / Tripoli** HPR certification for the operator.
* **FAA Part 101** (USA) for amateur rockets ≤ 150 000 ft AGL.
* **Radio**: ISM 915 MHz or 433 MHz, ≤ 250 mW ERP.

## 4. Subsystem matrix

| Subsystem              | Status |
|------------------------|--------|
| OBC                    | ✅    |
| High-g IMU (± 16 g)    | ✅    |
| Barometer (MS5611)     | ✅    |
| GNSS                   | ✅    |
| UHF / ISM telemetry    | ✅    |
| Dual-deploy controller | ✅    |
| Camera                 | ⚠ (optional, mass-limited) |
| ADCS                   | ❌    |
| S-band                 | ❌    |

## 5. Build

```bash
make target-rocket-avionics
```

Compile-time macro: `MISSION_PROFILE_ROCKET_AVIONICS=1`. Sets
`PROFILE_FEATURE_DESCENT_CTRL=1`, `PROFILE_FEATURE_ORBIT_PREDICTOR=0`.

## 6. Mission config

```bash
cp mission_templates/rocket_competition.json mission_config.json
```

Key fields:

* `mission.competition.target_altitude_m` — 10 000 ft / 3048 m is
  the IREC basic category; 30 000 ft / 9144 m for advanced.
* `mission.competition.dual_deploy` — true mandatory for IREC.
* `subsystems.comm_uhf.frequency_mhz` — 915 MHz (US) or 433 MHz (EU).
* `satellite.dimensions_mm` — match your rocket's coupler bay.

## 7. Mass & volume validation

| Metric       | Value   | Status |
|--------------|---------|--------|
| Total mass   | 0.34 kg | ≤ 0.50 kg ✅                  |
| Volume used  | 145 cm³ | 58 % of 250 cm³ ✅            |

Adding a small camera is feasible if the payload specialist can keep
it under 80 g.

## 8. Typical mission phases

Rocket-specific phases (from `mission_types.ROCKET_COMPETITION`):

```
ground_checkout → armed → boost → coast → apogee
                                              ↓
                                      drogue_descent
                                              ↓ altitude < main_deploy
                                      main_descent
                                              ↓
                                            landed
```

| Phase             | Sensor focus                        |
|-------------------|-------------------------------------|
| `ground_checkout` | IMU, barometer, telemetry           |
| `armed`           | Launch-detect predicate: accel > 3g |
| `boost`           | High-g IMU (up to 15g peak)         |
| `coast`           | Barometer primary, IMU secondary    |
| `apogee`          | Eject drogue on pressure reversal   |
| `drogue_descent`  | Measure descent rate ~15–25 m/s     |
| `main_descent`    | Main eject at ~300 m AGL, rate ~5 m/s|
| `landed`          | GNSS downlink for recovery          |

## 9. Testing checklist (bench)

> **Legend:** `[x]` = verified in software / CI / SITL (passes in the current release); `[ ]` = requires bench hardware, RF range test, or flight-day field activity — team must sign off manually.


- [ ] High-g IMU confirms ± 16 g range on a shake-table drop test.
- [x] Barometer reads ascent + descent consistent with an altitude profile from a previous flight or simulation.
- [ ] Ejection charges fire at commanded altitude in a drop test (actual pyro inside a blast chamber).
- [ ] Redundant altimeter (if fitted) agrees with primary within 5 % during pressure sweep.
- [ ] GNSS reacquires fix within 30 s post-boost.
- [ ] Launch-detect predicate triggers within 10 ms of 3 g threshold crossing.
- [ ] Data logger writes at 200 Hz for 10 min without loss.

## 10. Flight-day (launch-day) checklist

- [ ] Pre-launch weight + CG measurement matches predicted.
- [ ] Battery > 95 % charged.
- [ ] Pyro continuity on both channels confirmed.
- [ ] Armed-in-holdoff-mode until rocket is on the rail.
- [ ] Telemetry link heard by ground station from the rail.
- [ ] Weather within rulebook wind / visibility limits.
- [ ] `KeyRotationPolicy` reports `ok` on ground console.

## 11. Known limitations

* **No active attitude control** — aerodynamic stability only. Fin
  design + centre-of-pressure must be correct on the rocket.
* **GNSS shadowing during boost** — expect fix outage for the first
  10–15 s of ascent. Do not use GNSS in `launch_detect` logic.
* **Single OBC**: pyro firing failure ends the flight. Many teams
  fly a second redundant altimeter (Featherweight, EasyMini) in
  parallel — UniSat plays well with them but does not depend on them.

## 12. Post-flight debrief

Capture:

* On-board flight data (200 Hz IMU / 50 Hz barometer / 10 Hz GNSS).
* Ground-station PCAP of the telemetry link.
* Photographs of the rocket on recovery.
* Parachute unfurl / damage assessment.

Analyse against rulebook:

* Apogee within 10 % of target (IREC scoring).
* Dual-deploy timing correct.
* Recovery GNSS coordinate within search perimeter.

File a flight report under `docs/operations/flight_reports/<event>_<date>.md`.

---

**Previous profile**: [cubesat_12u.md](cubesat_12u.md) · **Next profile**: [hab_payload.md](hab_payload.md)
