# Drone / UAV — Operations Guide

Profile keys: `drone_small` (2.5 kg) · `drone_medium` (5.0 kg)
Template: [`mission_templates/drone_survey.json`](../../mission_templates/drone_survey.json) ·

---

## 1. Mission class

Payload computer for fixed-wing or multi-rotor UAVs. Mounts inside
the airframe as a secondary flight computer (primary autopilot —
Pixhawk / ArduPilot — still handles actuator control). UniSat
handles:

* on-board science / imaging payload;
* radio link to the ground-station dashboard;
* mission-phase state machine (preflight / takeoff / mission / landing);
* telemetry authentication (HMAC) for command uplink.

## 2. Physical envelope

| Parameter        | Small              | Medium              |
|------------------|--------------------|---------------------|
| Mass cap         | 2.5 kg             | 5.0 kg              |
| Dimensions (mm)  | 200 × 200 × 100    | 300 × 300 × 150     |
| Volume (cm³)     | 4000               | 13500               |
| Generation       | 0 W (battery only) | 0 W                 |
| Consumption      | 8 W                | 15 W                |

## 3. Regulatory context

* **EASA Open category**: A1 (<250 g payload) / A2 (<2 kg MTOM) / A3 (<25 kg).
* **EASA Specific category**: required for BVLOS, night, or payload > 4 kg.
* **FAA Part 107** (USA): commercial drone certificate.
* **Geofence**: hardware/firmware must enforce a configured geofence radius.
* **Radio**: ISM 2.4 GHz (MAVLink 915 MHz in US, 868 MHz in EU) or
  licensed UHF for longer range.

## 4. Subsystem matrix

| Subsystem               | Status                       |
|-------------------------|------------------------------|
| OBC                     | ✅                          |
| IMU (flight controller) | ✅ (redundant to autopilot) |
| Barometer               | ✅                          |
| GNSS                    | ✅                          |
| 2.4 GHz MAVLink link    | ✅                          |
| Camera (multispectral)  | ✅                          |
| Payload (survey kit)    | ✅                          |
| ADCS / reaction wheels  | ❌                          |
| S-band                  | ❌                          |

Note: the **autopilot** (Pixhawk etc.) is NOT a UniSat subsystem;
UniSat interfaces with it over MAVLink-over-UART. The payload
computer's IMU / barometer are secondary references, not the
control loop.

## 5. Build

```bash
# Small (EASA Open A2):
cmake -B firmware/build-arm-drone-small -S firmware \
      -DCMAKE_C_FLAGS=-DMISSION_PROFILE_DRONE_SMALL=1
cmake --build firmware/build-arm-drone-small

# Medium (Specific / BVLOS):
cmake -B firmware/build-arm-drone-medium -S firmware \
      -DCMAKE_C_FLAGS=-DMISSION_PROFILE_DRONE_MEDIUM=1
cmake --build firmware/build-arm-drone-medium
```

(Drone profiles are not on the default `make target-*` recipe list —
add a local alias if used frequently.)

## 6. Mission config

```bash
cp mission_templates/drone_survey.json mission_config.json
```

Key fields:

* `mission.competition.max_flight_time_min` — battery-limited; 30 min typical.
* `mission.competition.max_altitude_m` — set to regulatory limit (typically 120 m AGL).
* `mission.competition.geofence_radius_m` — hard-stop radius around takeoff point.
* `subsystems.comm.uhf.frequency_mhz` — 2400 MHz MAVLink or licensed UHF.
* `subsystems.payload.sensors` — list of survey sensors (multispectral, thermal, LiDAR).

## 7. Mass & volume validation

Validator-confirmed (default subsystems):

| Size   | Mass | Limit  | Volume used |
|--------|------|--------|-------------|
| Small  | 1.8 kg | 2.5 kg | 45 % of 4000 cm³  |
| Medium | 3.2 kg | 5.0 kg | 38 % of 13500 cm³ |

## 8. Typical mission phases

Drone-survey phases (`DRONE_SURVEY` in `mission_types.py`):

```
preflight → armed → takeoff → mission_flight
                                  ↓
                        return_to_home / landing / emergency
                                  ↓
                              landed
```

Loss-of-link behaviour:

* Beyond `geofence_radius_m` → `return_to_home`.
* No link for > 60 s and outside RTH range → `emergency` (controlled descent).
* Battery < 15 % → `landing`.

## 9. Testing checklist (bench)

- [ ] IMU cross-check: UniSat IMU vs. autopilot IMU agree within 0.5°/s at rest.
- [ ] MAVLink heartbeat received at 1 Hz from the autopilot over UART.
- [ ] Geofence trigger at the configured radius in a hardware-in-the-loop test.
- [ ] Camera records 4K 30 fps for 20 min without drop.
- [ ] RTH altitude correctly set to the higher of (takeoff altitude + 50 m) and (current altitude).
- [ ] Emergency-landing mode: drone commands `LAND` to the autopilot within 2 s of link loss + geofence breach.

## 10. Flight-day checklist

- [ ] Pilot has valid A2 / Specific / Part 107 certificate.
- [ ] Weather within manufacturer limits (wind < 8 m/s typical).
- [ ] Geofence uploaded and verified on the autopilot ground-control screen.
- [ ] Spotter present if required by the operation category.
- [ ] `mission_config.json` signed + loaded; `KeyRotationPolicy` reports `ok`.
- [ ] Camera SD card formatted, ≥ 32 GB free.
- [ ] Battery check on all flight batteries (cell balance < 0.05 V).
- [ ] Emergency RTH tested at 30 m AGL before the full mission.

## 11. Known limitations

* **UniSat is NOT the primary flight controller**. Never route
  actuator commands through UniSat; the autopilot must have full
  authority at all times. UniSat advises; autopilot commands.
* **Battery-only operation** — no solar; flight time is
  battery-limited.
* **GNSS-denied operation** not supported in 1.3.x — drone profiles
  assume continuous GNSS fix. If you fly indoors, disable GNSS
  explicitly in mission_config and expect the `return_to_home` logic
  to degrade to a barometric hold.
* **No onboard weather sensing** — local met data must come from an
  external station.

## 12. Post-flight debrief

Capture:

* MAVLink telemetry log (autopilot-side).
* UniSat's own logs (IMU cross-check, mission-phase trace).
* Camera + payload data.
* Battery consumption per flight segment.

Analyse:

* Geofence compliance (every point inside the polygon).
* Maximum altitude vs. permit.
* Payload coverage map (for survey flights).

File in `docs/operations/flight_reports/`.

---

**Previous profile**: [hab_payload.md](hab_payload.md) · **Next profile**: —
