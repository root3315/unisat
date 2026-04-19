# CanSat Minimal — Operations Guide

Profile key: `cansat_minimal` · Mass cap: **350 g** · Volume: **226 cm³**
Template: [`mission_templates/cansat_minimal.json`](../../mission_templates/cansat_minimal.json) ·
BOM: [`hardware/bom/by_form_factor/cansat_minimal.csv`](../../hardware/bom/by_form_factor/cansat_minimal.csv)

---

## 1. Mission class

A pared-down CanSat for first-time teams, school programmes, and
educational outreach. No GNSS, no camera, no deployable payload —
just the four sensors needed to describe a free-fall descent:
accelerometer, gyro, barometer, and a UHF beacon.

Typical flight profile: released at ~500 m from a small rocket or
drone, descends under a single parachute, transmits telemetry until
landing.

## 2. Physical envelope

| Parameter              | Value                               |
|------------------------|-------------------------------------|
| Mass (with 20 % margin)| ≤ 350 g                             |
| Outer diameter         | 60 mm                               |
| Inner (usable) dia.    | 56 mm (2 mm wall)                   |
| Height                 | 80 mm                               |
| Internal volume        | 226 cm³                             |
| Power generation       | 0 W (battery-only)                  |
| Nominal consumption    | 0.6 W                               |
| Battery                | 1× 18650 LiPo, ~2.5 Wh              |

## 3. Regulatory context

* **Educational CanSat** (looser than ESERO) — no mandatory rulebook.
* **Radio**: ISM 433 MHz LoRa module, ≤ 100 mW ERP.  No licence required in EU / US / CIS for this band/power.
* **Airspace**: launch vehicle (rocket or drone) must comply with local aviation authority; the CanSat itself has no airspace burden below 500 m AGL.

## 4. Subsystem matrix

| Subsystem             | Required | Allowed | Forbidden |
|-----------------------|----------|---------|-----------|
| OBC (STM32F446)       | ✅       |         |           |
| EPS (LiPo + regulator)| ✅       |         |           |
| IMU (MPU-6050 class)  | ✅       |         |           |
| Barometer             | ✅       |         |           |
| UHF 433 MHz telemetry | ✅       |         |           |
| Descent controller    | ✅       | passive parachute |  |
| GNSS                  |          | ⚠ (adds 40 g) | |
| Camera                |          |         | ❌ (volume) |
| ADCS                  |          |         | ❌ (no attitude control on CanSat) |
| S-band                |          |         | ❌ (no range benefit) |

## 5. Build

```bash
make target-cansat-minimal
# produces firmware/build-arm-cansat-minimal/unisat_firmware.elf
# or a host binary if arm-none-eabi-gcc is absent
```

The compile-time macro is `MISSION_PROFILE_CANSAT_MINIMAL=1`. See
`firmware/stm32/Core/Inc/mission_profile.h` for the full expansion.
All orbital features (`PROFILE_FEATURE_ORBIT_PREDICTOR`, `SBAND`,
`IMAGERY`, `ADCS_ACTIVE`, `WHEELS`) are 0; the `DESCENT_CTRL` gate
is 1.

## 6. Mission config

```bash
cp mission_templates/cansat_minimal.json mission_config.json
```

Minimum fields to review and adjust:

* `mission.operator` — your team name.
* `mission.competition.name` — the event you are entering.
* `subsystems.comm_uhf.frequency_mhz` — pick a channel in the 433.05–434.79 MHz band that is free at your launch site.
* `ground_station.location` — coordinates of the launch pad (defaults to 0,0).

The configurator UI can generate the same file interactively:

```bash
make configurator
# Platform → "CanSat" → Form Factor → "cansat_minimal"
```

## 7. Mass & volume validation

Expected output from the validator with the default subsystem set
(`obc`, `imu`, `barometer`, `comm_uhf`, `descent_controller`):

| Metric        | Value   | Status |
|---------------|---------|--------|
| Total mass    | 0.288 kg| ≤ 0.35 kg ✅ |
| 20 % margin   | 0.048 kg| included |
| Total volume  | 89 cm³  | ≤ 226 cm³ ✅ |
| Utilization   | 39 %    | plenty of headroom |

If adding a GNSS module pushes the result over budget, disable the
camera placeholder or drop to a 14500-cell battery.

## 8. Typical mission phases

The mission_types registry (`flight-software/core/mission_types.py`)
defines these for `cansat_standard`; `cansat_minimal` inherits them:

```
pre_launch  →  launch_detect  →  ascent  →  apogee  →  descent  →  landed
```

Each phase gates which modules are active:

| Phase         | Active modules                                | Duration |
|---------------|-----------------------------------------------|----------|
| `pre_launch`  | telemetry, health, imu, barometer             | until launch ARM |
| `launch_detect`| imu (accel threshold 3 g), barometer         | ≤ 10 min |
| `ascent`      | + data_logger @ 10 Hz                         | ≤ 2 min  |
| `apogee`      | + descent_controller (eject parachute)        | ≤ 30 s   |
| `descent`     | full telemetry, high-rate logging             | ≤ 5 min  |
| `landed`      | telemetry + comm only (conserve battery)      | ≤ 1 h    |

## 9. Testing checklist (bench)

> **Legend:** `[x]` = verified in software / CI / SITL (passes in the current release); `[ ]` = requires bench hardware, RF range test, or flight-day field activity — team must sign off manually.


- [x] `make target-cansat-minimal` completes with no warnings.
- [x] `./scripts/verify.sh` is green.
- [ ] Ground station receives telemetry on the chosen 433 MHz channel at ≥ -110 dBm.
- [x] IMU detects a simulated 3 g launch event and transitions `pre_launch → launch_detect` in the SITL harness.
- [ ] Barometer reads pressure within ± 1 hPa of a reference device.
- [x] Descent-controller fires within 50 ms of apogee detection (SITL-injected pressure profile).
- [ ] Battery survives 90 minutes of continuous operation on a single charge.
- [ ] Watchdog feeds for 30 minutes with no missed periods (check `CommandDispatcher_GetStats`).

## 10. Flight-day checklist

- [ ] Battery > 90 % charged.
- [ ] Configurator-generated `mission_config.json` flashed.
- [ ] Correct UHF channel programmed.
- [ ] Parachute folded and restraint verified.
- [ ] Ground station tracking the beacon for ≥ 5 min before integration.
- [ ] Arm switch in **SAFE** position until just before release.
- [ ] Ground-side clock synchronised with OBC within ± 1 s.
- [ ] HMAC key loaded; `key_rotation` policy reports **ok** (see `ground-station/utils/key_rotation.py`).

## 11. Known limitations

* **No GNSS** in the default BOM — position recovery relies on visual tracking + RF direction-finding.
* **Single IMU** (no redundancy) — an MPU-6050 failure ends the mission.
* **No camera** — descent video is not available on this profile. Upgrade to `cansat_advanced` for a 5 MP camera.
* **ISM 433 MHz at 100 mW** gives ≤ 5 km range in line-of-sight conditions; not suitable for stratospheric-balloon deployments.

## 12. Post-flight debrief

Capture and archive:

1. Full AX.25 ground-station capture (`.bin` + timestamp) under `flight_logs/<YYYY-MM-DD>/`.
2. On-board CSV log from the data_logger module (pull over USB post-recovery).
3. Photographs of any visible damage to the structure / electronics.
4. Completed flight-day checklist with any deviations noted.
5. Lessons-learned summary — file under `docs/operations/flight_reports/`.

Data to analyse:

* Launch-detect latency (`ascent - pre_launch` timestamp delta).
* Peak acceleration / angular rate during ascent and at apogee.
* Descent-rate profile (should be 5–12 m/s per the configured limits).
* Telemetry coverage (% packets received vs. expected at 5 Hz).

---

**Previous profile**: — · **Next profile**: [cansat_standard.md](cansat_standard.md)
