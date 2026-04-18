# CubeSat 1.5U — Operations Guide

Profile key: `cubesat_1_5u` · Mass cap: **2.0 kg** · Volume: **1702 cm³**
Template: [`mission_templates/cubesat_1_5u.json`](../../mission_templates/cubesat_1_5u.json) ·
BOM: [`hardware/bom/by_form_factor/cubesat_1_5u.csv`](../../hardware/bom/by_form_factor/cubesat_1_5u.csv)

---

## 1. Mission class

Non-standard intermediate form factor between 1U and 2U.  Useful
when a payload needs ~30 % more volume than a 1U can offer but
the launch provider's slot billing is per-U. Same mechanical
footprint as 1U, 170 mm tall instead of 113.5 mm.

Typical users: imaging teams where the camera + baffle chain is
exactly 130 mm; tech-demo missions that need a deployable antenna
longer than a 1U can hide.

## 2. Physical envelope

| Parameter              | Value                               |
|------------------------|-------------------------------------|
| Mass cap               | 2.0 kg                              |
| Dimensions             | 100 × 100 × 170.2 mm                |
| Volume                 | 1702 cm³                            |
| Power generation       | ~3.5 W orbit-average                |
| Nominal consumption    | 2.8 W                               |
| Battery                | 3× 18650 Li-ion, ~30 Wh             |

## 3. Regulatory context

Same as 1U — CDS rev 14, ITU coordination, launch-provider ICD.
Most launch-provider slots are 1U × N, so a 1.5U must be billed as
two 1U slots unless the provider supports 0.5U increments (a few do,
notably ISIS and D-Orbit).

## 4. Subsystem matrix

| Subsystem            | 1U | 1.5U |
|----------------------|----|------|
| S-band               | ❌ | ❌   |
| Reaction wheels      | ❌ | ❌   |
| Magnetorquer ADCS    | ✅ | ✅   |
| GNSS                 | ✅ | ✅   |
| Camera (8 MP)        | ⚠  | ✅   |
| Deployable antenna   | ⚠  | ✅   |
| Dual OBC redundancy  | ❌ | ⚠ (tight) |

## 5. Build

```bash
make target-cubesat-1_5u
```

Compile-time macro: `MISSION_PROFILE_CUBESAT_1_5U=1`.

## 6. Mission config

```bash
cp mission_templates/cubesat_1_5u.json mission_config.json
```

Same adjustment list as 1U plus:

* Verify launch provider bills in 0.5U increments; otherwise stick with 2U.
* If using a deployable antenna, add the mass estimate to `satellite.mass_kg`.

## 7. Mass & volume validation

| Metric       | Value   | Status |
|--------------|---------|--------|
| Total mass   | 1.68 kg | ≤ 2.0 kg ✅ (16 % margin) |
| Volume used  | 500 cm³ | 29 % of 1702 cm³ ✅       |

A 1.5U has a comfortable margin for a moderate camera + deployable
antenna. Still no room for reaction wheels — the AdcsTier gate
stays at `magnetorquer`.

## 8. Typical mission phases

Same as 1U (cubesat_leo profile).

## 9. Testing checklist (ground qualification)

Same as 1U plus:

- [ ] Verify deployable antenna fully extends in thermal-vacuum at -20 °C.
- [ ] Check centre-of-mass offset from geometric centre < 2 mm (CDS §3.1 requirement).
- [ ] Confirm moment of inertia along each principal axis within ICD tolerance.

## 10. Flight-day checklist

Same as 1U.

## 11. Known limitations

Same as 1U. The extra 55 mm of height mostly buys you volume, not
power — body-mounted panels on a 1.5U add only two extra cells
compared to 1U, so the orbit-average generation gain is ~30 %.

## 12. Post-flight debrief

Same as 1U.

---

**Previous profile**: [cubesat_1u.md](cubesat_1u.md) · **Next profile**: [cubesat_2u.md](cubesat_2u.md)
