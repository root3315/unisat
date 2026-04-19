# CubeSat 2U — Operations Guide

Profile key: `cubesat_2u` · Mass cap: **2.66 kg** · Volume: **2270 cm³**
Template: [`mission_templates/cubesat_2u.json`](../../mission_templates/cubesat_2u.json) ·
BOM: [`hardware/bom/by_form_factor/cubesat_2u.csv`](../../hardware/bom/by_form_factor/cubesat_2u.csv)

---

## 1. Mission class

First CubeSat size that fits an 8 MP imaging payload, an S-band
downlink, and a 3-channel magnetorquer stack comfortably. Sweet spot
for universities that want to upgrade from educational 1U missions
to a meaningful science / Earth-obs demonstration.

## 2. Physical envelope

| Parameter              | Value                               |
|------------------------|-------------------------------------|
| Mass cap               | 2.66 kg                             |
| Dimensions             | 100 × 100 × 227.0 mm                |
| Volume                 | 2270 cm³                            |
| Power generation       | ~5.0 W orbit-average                |
| Nominal consumption    | 4.0 W                               |
| Battery                | 4× 18650 Li-ion, ~40 Wh             |

## 3. Regulatory context

* CDS rev 14 §3.1 — same dimension/mass contract as 1U/1.5U.
* **ITU coordination**: UHF amateur band and S-band 2.4 GHz (licence required, NOT amateur-only).
* **US FCC Part 25** (commercial) or Part 97 (amateur), depending on payload.

## 4. Subsystem matrix

| Subsystem           | Status on 2U         |
|---------------------|----------------------|
| Magnetorquer ADCS   | ✅ (3 axes)           |
| Reaction wheels     | ❌ (gate: needs 3U)  |
| UHF telemetry       | ✅                   |
| S-band downlink     | ✅ (first allowed)   |
| GNSS                | ✅                   |
| Camera (8 MP)       | ✅                   |
| Payload module      | ✅                   |
| Propulsion          | ❌                   |

## 5. Build

```bash
make target-cubesat-2u
```

Compile-time macro: `MISSION_PROFILE_CUBESAT_2U=1`. S-band gate is
enabled (`PROFILE_FEATURE_SBAND=1`).

## 6. Mission config

```bash
cp mission_templates/cubesat_2u.json mission_config.json
```

Edit as for 1.5U, plus:

* `subsystems.comm_sband.frequency_mhz` — your coordinated channel (typical 2400 MHz).
* `subsystems.camera.resolution_mp` — match your optical chain.
* `mission.telemetry_hz` — 1.0 Hz is reasonable; 2 Hz requires S-band.

## 7. Mass & volume validation

| Metric       | Value   | Status |
|--------------|---------|--------|
| Total mass   | 2.30 kg | ≤ 2.66 kg ✅  (14 % margin) |
| Volume used  | 735 cm³ | 32 % of 2270 cm³ ✅         |

## 8. Typical mission phases

Same `cubesat_leo` / `cubesat_sso` profile as 1U/1.5U. With S-band
enabled, the `comm_window` phase becomes more interesting: image
downlink happens in discrete windows when ground tracks the pass.

## 9. Testing checklist (ground qualification)

Same as 1.5U plus:

- [ ] S-band end-to-end link budget verified on a 2 m range with a 1.2 m parabolic dish (expected SNR ≥ 10 dB).
- [ ] Image pipeline (`imagery_pipeline` feature flag) processes 100 frames at 10 fps without drop.
- [ ] Camera temperature stays within 5 °C of the OBC temperature during capture burst.

## 10. Flight-day checklist

Same as 1.5U plus:

- [ ] S-band ground antenna pointed within 3° of first expected pass.
- [ ] TLE < 72 hours old.

## 11. Known limitations

* **Still no reaction wheels** — attitude pointing from magnetorquers alone is typically ≥ 2° jitter. Not suitable for narrow-field science imaging.
* **Battery charge during full S-band transmit** can go negative under worst-case eclipse — budget a duty cycle of ≤ 15 % per orbit.
* **No propulsion** — orbit decay is unavoidable; plan for a 2-year natural decay from 550 km SSO.

## 12. Post-flight debrief

Same as 1.5U plus image-downlink analytics: measured BER on S-band,
frames received per pass, average pass duration.

---

**Previous profile**: [cubesat_1_5u.md](cubesat_1_5u.md) · **Next profile**: [cubesat_3u.md](cubesat_3u.md)
