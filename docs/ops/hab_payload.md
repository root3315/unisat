# HAB Payload — Operations Guide

Profile key (medium): `hab_payload_medium` · Mass cap: **2.0 kg** · Volume: **6000 cm³**
Template: [`mission_templates/hab_standard.json`](../../mission_templates/hab_standard.json) ·

Also covers `hab_payload_small` (1.0 kg, 2250 cm³) and
`hab_payload_large` (5.0 kg, 18000 cm³). Pick the size that matches
your balloon envelope + lifting gas.

---

## 1. Mission class

High-altitude-balloon (HAB) payload for educational / citizen-
science flights. Typical mission profile: launch with a latex or
mylar envelope, ascend at ~5 m/s to ~30 km, burst, descend under
a parachute, recover 100–300 km downwind.

## 2. Physical envelope

| Parameter        | Small       | Medium      | Large        |
|------------------|-------------|-------------|--------------|
| Mass cap         | 1.0 kg      | 2.0 kg      | 5.0 kg       |
| Dimensions (mm)  | 150×150×100 | 200×200×150 | 300×300×200  |
| Volume (cm³)     | 2250        | 6000        | 18000        |
| Generation       | 0.5 W (small solar cell) | 1 W | 2.5 W     |
| Consumption      | 1.5 W       | 3 W         | 6 W          |

## 3. Regulatory context

* **FAA Part 101** (USA): ≤ 6 lb / 2.7 kg per payload; ≤ 12 lb total;
  notify FSS 24 h before launch. Payload cord < 50 lb breaking
  strength.
* **EASA equivalent**: UK CAA Article 166 (≤ 2 kg payload), EU EASA
  NfL (light unmanned balloons).
* **Radio**: UHF 434 MHz or ISM 868 MHz for LoRa; APRS 144.39 MHz
  requires a licensed operator; amateur radio call-sign in beacon.
* **Airspace**: notify local ATC for controlled airspace transits.

## 4. Subsystem matrix

| Subsystem            | Status |
|----------------------|--------|
| OBC                  | ✅    |
| Barometer (MS5611)   | ✅    |
| GNSS                 | ✅    |
| UHF RTTY / LoRa      | ✅    |
| APRS (licensed op.)  | ⚠    |
| Camera (wide-angle)  | ✅    |
| Environmental sensors (temp, humidity, UV, radiation) | ✅ |
| IMU                  | ⚠ (optional) |
| ADCS                 | ❌    |
| Descent controller   | ❌ (passive parachute only) |

## 5. Build

```bash
make target-hab-medium          # default for 2.0 kg envelope
# or configure small / large manually:
# cmake -B firmware/build-arm-hab-small -S firmware \
#       -DCMAKE_C_FLAGS=-DMISSION_PROFILE_HAB_PAYLOAD_SMALL=1
```

Compile-time macro: `MISSION_PROFILE_HAB_PAYLOAD_MEDIUM=1` (or
`_SMALL` / `_LARGE`).

## 6. Mission config

```bash
cp mission_templates/hab_standard.json mission_config.json
```

Key fields:

* `mission.competition.target_altitude_m` — typical 30 000 m.
* `mission.competition.expected_ascent_rate_m_s` — typical 5.
* `subsystems.comm_uhf.frequency_mhz` — 434 MHz RTTY or 868 / 915 MHz LoRa.
* `subsystems.comm.aprs.callsign` — YOUR licensed call-sign.
* `satellite.form_factor` — `hab_payload_small/medium/large` depending on chosen size.

## 7. Mass & volume validation

Per form-factor (ALL_ENABLED subset relevant for HAB):

| Size   | Typical loaded mass | Limit   | Volume used / total |
|--------|--------------------|---------|--------------------|
| Small  | 0.82 kg            | 1.0 kg  | 270 / 2250 cm³     |
| Medium | 1.45 kg            | 2.0 kg  | 475 / 6000 cm³     |
| Large  | 2.90 kg            | 5.0 kg  | 850 / 18000 cm³    |

## 8. Typical mission phases

```
ground_setup → ascent → float → burst → descent → landed
```

| Phase        | Typical duration | Notes                         |
|--------------|-----------------|-------------------------------|
| `ground_setup`| 30 min          | Balloon inflation + checklist |
| `ascent`     | 90–180 min      | ~5 m/s nominal                |
| `float`      | 0–120 min       | Only if balloon is zero-pressure |
| `burst`      | 2–10 s          | Sudden pressure spike         |
| `descent`    | 30–90 min       | ~30 m/s initial, decreasing   |
| `landed`     | until recovery  | Downlink GPS for chase team   |

## 9. Testing checklist (bench)

- [ ] Cold test: place payload in freezer at -55 °C for 2 h. OBC continues to log.
- [ ] Battery (Energizer Ultimate Lithium, -40 °C rated) survives 6 h at -40 °C without voltage sag.
- [ ] GNSS retains fix through simulated stratospheric altitude by enabling "airborne < 1g" mode.
- [ ] Telemetry link closes at 50 km slant range with a yagi on ground.
- [ ] Camera SD card survives 6 h of -40 °C operation.
- [ ] Pressure sensor reads 5 mbar ± 0.5 mbar at 30 000 m equivalent altitude in a vacuum chamber.

## 10. Flight-day checklist

- [ ] FAA / CAA notification filed.
- [ ] Chase team briefed on predicted landing zone (run APRS.fi flight predictor).
- [ ] Helium / hydrogen tank pressure + valve checked.
- [ ] Parachute attached to cord; cord to balloon via break-away line.
- [ ] Payload battery voltage logged before sealing insulation.
- [ ] Telemetry received by two independent ground stations for 15 min before release.
- [ ] `KeyRotationPolicy` reports `ok` on ground console (ISM 868 / 915).

## 11. Known limitations

* **Thermal**: inside the payload box the temperature swings from
  +30 °C (launch on sunny day) to -60 °C (tropopause) and back.
  Use foam insulation + chemical warmer if running low-temperature
  sensitive components.
* **GNSS "airborne mode"**: consumer u-blox modules default to a
  max altitude of 12 km; the `MAX-M10S` accepts a dynamic model
  switch — issue it during `ground_setup`.
* **No active attitude control**: payload spins randomly. Camera
  footage is shaky; panoramic photography requires a gimbal or a
  dedicated rotation-compensated mount.

## 12. Post-flight debrief

Capture:

* GNSS ground track (upload to aprs.fi / habhub.org).
* On-board pressure / temperature / UV / radiation CSV.
* Camera SD card (wide-angle video + stills at 30 s interval).
* Any damage on recovery (battery voltage, antenna integrity).

Publish:

* Landing-point prediction accuracy (predicted vs. actual).
* Burst altitude vs. balloon spec.
* Science-payload results (photo processing, radiation profile, etc.).

File a flight report in `docs/operations/flight_reports/`.

---

**Previous profile**: [rocket_avionics.md](rocket_avionics.md) · **Next profile**: [drone.md](drone.md)
