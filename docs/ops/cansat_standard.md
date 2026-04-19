# CanSat Standard — Operations Guide

Profile key: `cansat_standard` · Mass cap: **500 g** · Volume: **290 cm³**
Template: [`mission_templates/cansat_standard.json`](../../mission_templates/cansat_standard.json) ·
BOM: [`hardware/bom/by_form_factor/cansat_standard.csv`](../../hardware/bom/by_form_factor/cansat_standard.csv)

---

## 1. Mission class

Full-stack CanSat for ESERO / national rulebooks. Adds GNSS, a
small camera, and a payload-sensor channel on top of the minimal
profile. Baseline for teams targeting the European CanSat
Competition and similar events.

## 2. Physical envelope

| Parameter              | Value                               |
|------------------------|-------------------------------------|
| Mass (with 20 % margin)| ≤ 500 g                             |
| Outer diameter         | 68 mm  (ESERO standard)             |
| Inner (usable) dia.    | 64 mm                               |
| Height                 | 80 mm                               |
| Internal volume        | 257 cm³ (cylinder interior)         |
| Nominal consumption    | 1.0 W                               |
| Battery                | 2× 14500 Li-ion, ~2.5 Wh            |

## 3. Regulatory context

* **ESERO CanSat 2024 rulebook** §2 — mass, dimensions, descent rate 6–11 m/s, parachute deployment at ≥ 300 m AGL.
* **Radio**: UHF 433 MHz with ≤ 250 mW transmit power. Verify regional allocation before picking a frequency (e.g. EU licence-exempt 433.05–434.79 MHz / 10 mW ERP).
* **Airspace**: launch vehicle registered with the national aviation authority; CanSat itself has no separate licensing.

## 4. Subsystem matrix

| Subsystem             | Required | Allowed | Forbidden |
|-----------------------|----------|---------|-----------|
| OBC                   | ✅       |         |           |
| EPS                   | ✅       |         |           |
| IMU (ICM-20948)       | ✅       |         |           |
| Barometer (BMP388)    | ✅       |         |           |
| GNSS (u-blox MAX-M10S)| ✅       |         |           |
| UHF telemetry         | ✅       |         |           |
| Descent controller    | ✅       | parachute eject + altimeter | |
| Camera (low-res)      |          | ✅ (5 MP) |         |
| Payload sensors       |          | ✅      |           |
| ADCS                  |          |         | ❌        |
| S-band                |          |         | ❌        |

## 5. Build

```bash
make target-cansat-standard
```

Compile-time macro: `MISSION_PROFILE_CANSAT_STANDARD=1`.

## 6. Mission config

```bash
cp mission_templates/cansat_standard.json mission_config.json
```

Fields to review:

* `mission.competition.descent_rate_range_m_s` — adjust to match your event's rulebook (ESERO: `[6.0, 11.0]`).
* `mission.competition.min_telemetry_samples` — ESERO requires ≥ 100 usable samples during the flight.
* `subsystems.descent_controller.mode` — `single_deploy` or `dual_deploy` depending on rulebook.
* `subsystems.camera` — set `enabled: false` if disqualification rules forbid imagery.
* `ground_station.antenna` — configure a yagi / moxon orientation for the launch site.

## 7. Mass & volume validation

With the default subsystem set:

| Metric        | Value   | Status |
|---------------|---------|--------|
| Total mass    | 0.408 kg| ≤ 0.50 kg ✅ |
| 20 % margin   | 0.068 kg| included |
| Total volume  | 155 cm³ | ≤ 290 cm³ ✅ |
| Utilization   | 53 %    | healthy |

Adding a 12 MP camera will push mass to ~460 g — still valid with
7 % margin. Adding reaction wheels will be refused by the form-
factor gate (`AdcsTier.NONE` only).

## 8. Typical mission phases

```
pre_launch → launch_detect → ascent → apogee → descent → landed
```

Phase transitions match the minimal profile. Additional duties
per phase:

| Phase       | Extra module activity                               |
|-------------|-----------------------------------------------------|
| `pre_launch`| GNSS fix acquired & logged                          |
| `ascent`    | Camera begins recording at 5 fps                    |
| `apogee`    | Parachute eject + log peak altitude                 |
| `descent`   | Verify descent rate inside 6–11 m/s window          |
| `landed`    | GNSS position downlinked for recovery               |

## 9. Testing checklist (bench)

- [ ] Green `./scripts/verify.sh`.
- [ ] Telemetry link closes at worst-case launch-site distance (≥ 2 km with yagi).
- [ ] GNSS cold-start ≤ 45 s indoors with an active antenna, ≤ 90 s outdoors on battery.
- [ ] Parachute eject mechanism fires within 50 ms of apogee detection (SITL).
- [ ] Descent rate stays inside [6, 11] m/s in a 1 : 10 drop test from a tower or UAV.
- [ ] Camera records ≥ 1 minute of 5 fps video without frame drops.
- [ ] On-board CSV logger writes at 10 Hz for 15 minutes without loss.
- [ ] HMAC key rotation check: `KeyRotationPolicy.check_before_send()` returns `ok`.

## 10. Flight-day checklist

- [ ] Battery > 95 % charged.
- [ ] `mission_config.json` flashed and verified over UART.
- [ ] Launch-pad UHF channel clear of interference (scan with SDR).
- [ ] Camera SD card formatted, ≥ 2 GB free.
- [ ] GNSS antenna patch cable seated.
- [ ] Parachute folded per procedure; restraint wire intact.
- [ ] Team confirms redundancy on key generation tracking (see §11 of the security guide).

## 11. Known limitations

* **No attitude control**: descent orientation is gravity-and-chute only. Expect spin at 0.5–2 Hz.
* **GNSS outage during ascent**: antenna is shadowed by the ejection mechanism while the chute is folded. Fix typically re-acquired within 10 s of deployment.
* **Single UHF radio**: any RF failure ends telemetry. Ground team must record local sensor logs as a secondary data source.

## 12. Post-flight debrief

Capture:

1. Ground capture (AX.25 PCAP format).
2. On-board CSV log + camera SD card.
3. Descent-rate plot derived from barometer + IMU.
4. GNSS ground track.

Analyse against rulebook thresholds:

* ≥ 100 usable samples (ESERO);
* descent rate inside 6–11 m/s window;
* landing GNSS coordinate within 500 m of predicted drift drop zone.

File a flight report under `docs/operations/flight_reports/`.

---

**Previous profile**: [cansat_minimal.md](cansat_minimal.md) · **Next profile**: [cansat_advanced.md](cansat_advanced.md)
