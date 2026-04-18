# Bill of Materials — per form factor

Each CSV below is a *reference* BOM sized to the physical envelope of its
form factor and aligned with the matching `mission_templates/<name>.json`
file. Use them as the starting point for a specific mission; substitute
components for what you can actually procure.

| File | Vehicle | Nominal mass | Max mass |
|---|---|---:|---:|
| [`cansat_minimal.csv`](cansat_minimal.csv) | CanSat telemetry-only | ~130 g | 350 g |
| [`cansat_standard.csv`](cansat_standard.csv) | CanSat competition | ~170 g | 500 g |
| [`cansat_advanced.csv`](cansat_advanced.csv) | CanSat guided descent | ~250 g | 500 g |
| [`cubesat_1u.csv`](cubesat_1u.csv) | 1U CubeSat | ~420 g | 2 kg |
| [`cubesat_3u.csv`](cubesat_3u.csv) | 3U CubeSat | ~1.28 kg | 6 kg |
| [`cubesat_6u.csv`](cubesat_6u.csv) | 6U CubeSat | ~7.1 kg | 12 kg |
| [`cubesat_12u.csv`](cubesat_12u.csv) | 12U CubeSat | ~16 kg | 24 kg |

The legacy `../components.csv` file remains for backwards compatibility
and now points to `cubesat_3u.csv` as its canonical successor.

Columns are identical across files: `Category, Component, Part Number,
Qty, Unit Price (USD), Mass (g), Supplier, Notes`.
