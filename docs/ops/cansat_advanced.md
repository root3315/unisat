# CanSat Advanced — Operations Guide

Profile key: `cansat_advanced` · Mass cap: **700 g** · Volume: **700 cm³**
Template: [`mission_templates/cansat_advanced.json`](../../mission_templates/cansat_advanced.json) ·
BOM: [`hardware/bom/by_form_factor/cansat_advanced.csv`](../../hardware/bom/by_form_factor/cansat_advanced.csv)

---

## 1. Mission class

NASA CanSat-style build: taller envelope, dual-deploy parachute,
deployable science payload (airbrake / tethered sensor / bonus
glider). Ideal for experienced teams that want a meaningful payload
experiment rather than a bare descent telemetry pipe.

## 2. Physical envelope

| Parameter              | Value                               |
|------------------------|-------------------------------------|
| Mass (with 20 % margin)| ≤ 700 g                             |
| Outer dimensions       | 80 × 80 × 150 mm (square envelope)  |
| Internal volume        | 700 cm³                             |
| Nominal consumption    | 1.4 W                               |
| Battery                | 2× 18650 Li-ion, ~6 Wh              |

## 3. Regulatory context

* **NASA CanSat 2024** rulebook (or equivalent advanced-category event).
* Radio: UHF 433 MHz, ≤ 250 mW ERP (same as standard).
* Deployable payload must satisfy competition's soft-landing rules if it separates from the main body.

## 4. Subsystem matrix

| Subsystem              | Required | Allowed |
|------------------------|----------|---------|
| OBC                    | ✅       |         |
| Dual IMU (primary+redundant)| ✅ |         |
| GNSS                   | ✅       |         |
| Barometer              | ✅       |         |
| UHF telemetry (high-gain patch) | ✅ |     |
| Descent ctrl (dual-deploy)| ✅    |         |
| Wide-angle camera (5 MP)| ✅      |         |
| Deployable payload     | ✅       | airbrake / tethered / glider |

## 5. Build

```bash
make target-cansat-advanced
```

Compile-time macro: `MISSION_PROFILE_CANSAT_ADVANCED=1`. Enables
`PROFILE_FEATURE_IMAGERY=1` for on-board camera processing.

## 6. Mission config

Start from `mission_templates/cansat_advanced.json`. Key fields:

* `subsystems.descent_controller.mode`: `dual_deploy` (drogue at apogee, main at ~300 m AGL).
* `subsystems.payload.type`: match your experiment (`airbrake`, `tethered_probe`, `glider`).
* `mission.competition.max_cansat_mass_g`: should be `700`.
* `mission.competition.name`: "NASA CanSat Advanced" (or your event).

## 7. Mass & volume validation

Reference run from `validate_mass("cansat_advanced", ALL_ENABLED)`:

| Metric       | Value   | Status |
|--------------|---------|--------|
| Total mass   | 0.612 kg| ≤ 0.70 kg ✅ |
| Margin left  | 88 g    | 13 % slack for payload experiment growth |
| Volume used  | 310 cm³ | 44 % of 700 cm³ |

## 8. Typical mission phases

```
pre_launch → launch_detect → ascent → apogee → descent → landed
```

Augmented by payload deployment inside `descent`:

```
          descent (drogue)
               ↓ altitude < deploy_altitude_m (default 300 m)
          descent (main)
               ↓ altitude < payload_deploy_alt (optional)
          descent (+ deployed payload)
               ↓ ground contact
          landed
```

## 9. Testing checklist (bench)

- [ ] Dual-deploy sequence verified in vacuum chamber or barometric simulator.
- [ ] Camera + IMU write to SD without contention (stress test 10 min).
- [ ] Redundant IMU takes over within 500 ms when primary is disabled via SITL.
- [ ] `make target-cansat-advanced` produces a firmware that sets `PROFILE_FEATURE_IMAGERY=1`.
- [ ] Telemetry link tested at 3 km with high-gain patch (expected RX SNR ≥ 10 dB).
- [ ] Deployable payload mechanism triggers correctly and cleanly separates.

## 10. Flight-day checklist

Everything from `cansat_standard` plus:

- [ ] Both IMU channels armed; ground console shows both fix streams.
- [ ] Payload deployment altitude set to the approved value for your airspace.
- [ ] Camera SD card has ≥ 8 GB free for 720p video.
- [ ] Backup ground station running at a second location for spatial diversity.

## 11. Known limitations

* **Spin mitigation is passive** — no active attitude control.
* **Ground-recovery time sensitivity**: if the tethered payload separates, recovery needs dual GNSS units (one in the main body, one in the payload) — not covered by the default BOM.
* **Power budget is tight** under full camera + dual IMU load; a mission longer than 30 minutes will likely need a 3-cell pack.

## 12. Post-flight debrief

Capture everything from `cansat_standard` plus:

* Both IMU streams (cross-correlate for drift).
* Camera video (check frame-drop log).
* Payload telemetry (if separate downlink).
* Post-separation attitude of the deployable (photo / video from chase drone, if available).

File under `docs/operations/flight_reports/<event>_<YYYY-MM-DD>.md`.

---

**Previous profile**: [cansat_standard.md](cansat_standard.md) · **Next profile**: [cubesat_1u.md](cubesat_1u.md)
