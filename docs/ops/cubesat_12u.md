# CubeSat 12U — Operations Guide

Profile key: `cubesat_12u` · Mass cap: **24.0 kg** · Volume: **17438 cm³**
Template: [`mission_templates/cubesat_12u.json`](../../mission_templates/cubesat_12u.json) ·
BOM: [`hardware/bom/by_form_factor/cubesat_12u.csv`](../../hardware/bom/by_form_factor/cubesat_12u.csv)

---

## 1. Mission class

The largest standard CubeSat: 226.3 × 226.3 × 340.5 mm, 24 kg, up
to 60 W with deployable arrays. Used for long-duration tech demos,
deep-space precursors (lunar orbit, cislunar), interferometric
Earth observation, and multi-payload science missions.

> **Radiation caveat**. The STM32F446RE has published TID heritage
> of ~10 krad (see `docs/hardware/radiation_budget.md`).  A 12U
> on a 5-year polar orbit at 700 km burns through 10 krad — right
> at the margin. For deep-space, an additional rad-hard secondary
> OBC is recommended but **not in scope** for UniSat 1.3.x.

## 2. Physical envelope

| Parameter              | Value                               |
|------------------------|-------------------------------------|
| Mass cap               | 24.0 kg                             |
| Dimensions             | 226.3 × 226.3 × 340.5 mm            |
| Volume                 | 17438 cm³                           |
| Power generation       | ~50 W with full deployable arrays   |
| Nominal consumption    | 35 W                                |
| Battery                | 16S4P Li-ion, ~200 Wh               |

## 3. Regulatory context

* **CDS rev 14 §3.2** — 12U dispenser spec.
* **ITU**: UHF + S-band + X-band; for deep-space, DSN (NASA) or
  ESTRACK (ESA) frequency coordination.
* **Launch**: ESPA-class rideshare, Firefly, Electron, Falcon-9 rideshare.
* **Planetary protection** (for lunar / deep-space): COSPAR
  Category II or III depending on target body.

## 4. Subsystem matrix

| Subsystem                  | Status |
|----------------------------|--------|
| 3-axis ADCS (wheels+star)  | ✅    |
| Redundant star tracker     | ✅    |
| UHF telemetry              | ✅    |
| S-band downlink (10 W)     | ✅    |
| X-band downlink (20 W dish)| ✅    |
| GNSS (LEO only)            | ✅    |
| Deep-space radio           | ⚠ (requires X-band TX 20 W + 0.5 m dish) |
| Camera (64 MP telescope)   | ✅    |
| Deployable solar arrays    | ✅    |
| Cold-gas propulsion        | ✅    |
| Electric propulsion        | ⚠ (BIT-3, PPT — budget-permitting) |
| Rad-hard secondary OBC     | ❌ (out of scope for UniSat 1.3.x) |

## 5. Build

```bash
make target-cubesat-12u
```

Compile-time macro: `MISSION_PROFILE_CUBESAT_12U=1`.

## 6. Mission config

```bash
cp mission_templates/cubesat_12u.json mission_config.json
```

Fields specific to 12U:

* `subsystems.comm_xband.frequency_mhz` — default 8400 MHz.
* `subsystems.adcs.star_tracker` — typically two for redundancy.
* `subsystems.payload.type` — match your experiment (interferometer, lunar comms relay, etc.).
* `orbit.type` — LEO, SSO, GEO insertion (via rideshare + kick stage), or cislunar.
* `orbit.expected_lifetime_years` — default 5, adjust per propulsion budget.

## 7. Mass & volume validation

| Metric       | Value   | Status |
|--------------|---------|--------|
| Total mass   | 16.0 kg | ≤ 24.0 kg ✅ (33 % margin) |
| Volume used  | 5425 cm³| 31 % of 17438 cm³ ✅       |

Very comfortable margin for a complex payload stack. Typical 12U
missions budget 4–6 kg for the payload alone.

## 8. Typical mission phases

Same as 6U in LEO mode. Cislunar / deep-space missions add:

```
initial_orbit → transfer_burn → cruise → science_arrival → science → eol
```

Where `transfer_burn` is an external propulsion event (rideshare
upper stage or on-board electric propulsion) and `cruise` can be
weeks or months.

## 9. Testing checklist (ground qualification)

> **Legend:** `[x]` = verified in software / CI / SITL (passes in the current release); `[ ]` = requires bench hardware, RF range test, or flight-day field activity — team must sign off manually.


Everything from 6U plus:

- [ ] Extended TVac: 10 cycles, -30 °C to +65 °C, 8 h dwell.
- [ ] Radiation test to 5 krad TID (deep-space) or 2 krad (LEO).
- [ ] SEU cross-section characterisation at proton energies ≥ 65 MeV.
- [ ] Propulsion firing verification on air-bearing table (cold-gas) or vacuum chamber (electric).
- [ ] Star-tracker sky-field + stray-light tests in dark chamber.
- [x] End-to-end SITL with full phase sequence including `transfer_burn`.

## 10. Flight-day checklist

Same as 6U plus:

- [ ] Planetary-protection certificate (for lunar / deep-space).
- [ ] DSN / ESTRACK tracking time scheduled.
- [ ] Redundant OBC path tested during the final pre-ship review.
- [ ] Propellant loaded per cold-gas / electric manifest; leak-test signed off.

## 11. Known limitations

* **No rad-hard OBC in UniSat 1.3.x** — long-duration deep-space
  missions accept TID risk on the STM32F446RE. Plan for a soft
  failure mode (fallback to safe-mode + survival beacon) at end of
  life.
* **DSN/ESTRACK scheduling** can limit science duty cycle for
  cislunar and beyond; budget accordingly.
* **Thermal gradient** across the 226 × 226 mm footprint under
  asymmetric illumination can exceed 30 °C; design the thermal
  strap network carefully.
* **Deployable retention mass** scales quickly with array size;
  budget 0.5 kg per panel articulation mechanism.

## 12. Post-flight debrief

Same as 6U plus:

* Deep-space radio link-budget verification per pass.
* Star-tracker cross-check over thermal swings.
* Propulsion consumption vs. plan (delta-V delivered).
* TID dose estimate from on-board radiation sensor (`FAULT_RADIATION_*` grayscale reports — see `docs/hardware/radiation_budget.md`).

---

**Previous profile**: [cubesat_6u.md](cubesat_6u.md) · **Next profile**: [rocket_avionics.md](rocket_avionics.md)
