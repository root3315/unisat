# CubeSat 6U — Operations Guide

Profile key: `cubesat_6u` · Mass cap: **12.0 kg** · Volume: **7704 cm³**
Template: [`mission_templates/cubesat_6u.json`](../../mission_templates/cubesat_6u.json) ·
BOM: [`hardware/bom/by_form_factor/cubesat_6u.csv`](../../hardware/bom/by_form_factor/cubesat_6u.csv)

---

## 1. Mission class

Imaging / Earth-observation workhorse. 6U unlocks deployable solar
arrays (20+ W), larger optics (up to 80 mm aperture), and full
3-axis pointing with star-tracker + reaction wheels. Typical
customers: commercial EO constellations, science missions with
modest deployable antennas.

## 2. Physical envelope

| Parameter              | Value                               |
|------------------------|-------------------------------------|
| Mass cap               | 12.0 kg                             |
| Dimensions             | 100 × 226.3 × 340.5 mm              |
| Volume                 | 7704 cm³                            |
| Power generation       | ~25 W with deployable arrays        |
| Nominal consumption    | 18 W                                |
| Battery                | 8S4P Li-ion, ~120 Wh                |

## 3. Regulatory context

* **CDS rev 14 §3.2** — 6U tuna-can standard (226.3 mm).
* **ITU**: UHF, S-band, potentially X-band for high-rate downlink.
* **Launch**: P-POD 6U, ISIPOD 6U, EXOpod. Additional ICD: deployable
  antenna + panel retention.
* **End-of-life**: active de-orbit strategy recommended (drag brake,
  propulsion, or < 600 km orbit for 25-year natural decay).

## 4. Subsystem matrix

| Subsystem                  | Status |
|----------------------------|--------|
| Reaction wheels ADCS       | ✅ (3 mid-size) |
| Magnetorquer detumble      | ✅    |
| Star tracker               | ✅    |
| Sun sensor + magnetometer  | ✅    |
| UHF telemetry              | ✅    |
| S-band downlink (5 W)      | ✅    |
| X-band downlink (optional) | ⚠ (fits, needs extra power budget) |
| GNSS                       | ✅    |
| Camera (48 MP + telescope) | ✅    |
| Deployable solar panels    | ✅    |
| Cold-gas propulsion        | ⚠ (fits in 1U volume) |
| Electric propulsion        | ❌ (needs 12U power) |

## 5. Build

```bash
make target-cubesat-6u
```

Compile-time macro: `MISSION_PROFILE_CUBESAT_6U=1`.

## 6. Mission config

```bash
cp mission_templates/cubesat_6u.json mission_config.json
```

Key fields:

* `subsystems.eps.deployable_panels` — `true` for the full 25 W generation.
* `subsystems.adcs.star_tracker` — `true` (unlocks arcsec pointing).
* `subsystems.camera.optics` — `telescope` (refractor / Cassegrain).
* `orbit.type` — `SSO` for imaging, `LEO` for tech demo.

## 7. Mass & volume validation

| Metric       | Value   | Status |
|--------------|---------|--------|
| Total mass   | 8.20 kg | ≤ 12.0 kg ✅ (32 % margin) |
| Volume used  | 2875 cm³| 37 % of 7704 cm³ ✅       |

Ample room for a large payload. If adding X-band, budget an extra
0.5 kg and 5 W peak draw.

## 8. Typical mission phases

Same `cubesat_sso` phases. Imaging cadence is the big change from
3U: `science` phase becomes 30–60 minutes at a time for whole-strip
collection, not 10-minute bursts.

## 9. Testing checklist (ground qualification)

Everything from 3U plus:

- [ ] Deployable panel release tested at -40 °C and +60 °C.
- [ ] Momentum-wheel desaturation path exercised through magnetorquer commanding (closed loop in air-bearing table).
- [ ] Star-tracker sky-field test in dark chamber.
- [ ] TVac cycles extended to 6 (launch-provider requirement for deployable bodies).
- [ ] Plume-impingement analysis for any cold-gas thruster.

## 10. Flight-day checklist

Same as 3U plus:

- [ ] Solar-panel deployment safety tag removed.
- [ ] Retention cable checked; pyro-cutter armed.
- [ ] Launch-provider ICD signed off on 226 mm tuna-can envelope.

## 11. Known limitations

* **Deployment risk**: any stuck panel halves the power budget. Mission must survive in `low_power` phase indefinitely.
* **Thermal peak** under full imaging burst (camera + S-band + wheel desat) can exceed +70 °C. Passive thermal design must include a dedicated radiator.
* **No autonomous orbit-insertion** — rely on the launch-provider drop-off; no delta-V capability beyond reaction wheel + magnetorquer desaturation.

## 12. Post-flight debrief

Same as 3U, plus:

* Deployment success (record panel articulation telemetry from first 30 min).
* Star-tracker lost-in-space acquisition time.
* Image-pipeline production: frames collected / frames downlinked / frames usable.

---

**Previous profile**: [cubesat_3u.md](cubesat_3u.md) · **Next profile**: [cubesat_12u.md](cubesat_12u.md)
