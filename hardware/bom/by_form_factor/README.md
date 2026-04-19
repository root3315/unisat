# Bill of Materials — per form factor

Each CSV below is a *reference* BOM sized to the physical envelope of its
form factor and aligned with the matching `mission_templates/<name>.json`
file. Use them as the starting point for a specific mission; substitute
components for what you can actually procure.

| File | Vehicle | Bare-kit mass¹ | Payload headroom² | Regulation limit |
|---|---|---:|---:|---:|
| [`cansat_minimal.csv`](cansat_minimal.csv) | CanSat telemetry-only | ~130 g | ~220 g | **350 g** |
| [`cansat_standard.csv`](cansat_standard.csv) | CanSat competition | ~170 g | **~330 g** | **500 g** |
| [`cansat_advanced.csv`](cansat_advanced.csv) | CanSat guided descent | ~280 g | ~220 g | **500 g** |
| [`cubesat_1u.csv`](cubesat_1u.csv) | 1U CubeSat | ~420 g | ~910 g | **1.33 kg** (CDS) / 2.0 kg |
| [`cubesat_1_5u.csv`](cubesat_1_5u.csv) | 1.5U CubeSat | ~680 g | ~2.32 kg | **3.0 kg** |
| [`cubesat_2u.csv`](cubesat_2u.csv) | 2U CubeSat | ~990 g | ~3.01 kg | **4.0 kg** |
| [`cubesat_3u.csv`](cubesat_3u.csv) | 3U CubeSat | ~1.28 kg | ~2.72 kg | **4.0 kg** (CDS) / 6.0 kg |
| [`cubesat_6u.csv`](cubesat_6u.csv) | 6U CubeSat | ~7.1 kg | ~4.9 kg | **12 kg** |
| [`cubesat_12u.csv`](cubesat_12u.csv) | 12U CubeSat | ~16 kg | ~8 kg | **24 kg** |

¹ *Bare-kit mass* is the sum of UniSat reference components from this CSV
— structure, OBC, sensors, battery, comms. **It is not the total launch
mass**, just the empty-platform weight.

² *Payload headroom* is the mass you still have for science payloads,
custom sensors, or mechanical accessories before hitting the regulation
limit. For `cansat_standard` that headroom is ≈330 g — that's room for
a Geiger tube, NIR camera, cubesat-class IMU, or a thin-film chemistry
experiment, and still stay inside the 500 g ceiling.

**Read the "Max mass" column as the regulation, not the kit.** Teams
sometimes confuse the two during design reviews; the kit total is a
starting point, and the regulation is the hard cutoff judges enforce
at pre-launch mass check.

The legacy `../components.csv` file remains for backwards compatibility
and now points to `cubesat_3u.csv` as its canonical successor.

Columns are identical across files: `Category, Component, Part Number,
Qty, Unit Price (USD), Mass (g), Supplier, Notes`.
