# Universal Platform — design reference

UniSat is built so the **same** firmware, flight-software stack, and
ground station can fly any of the following vehicles with nothing more
than a template swap and a build-target choice:

| Family | Variants |
|---|---|
| CanSat | `cansat_minimal`, `cansat_standard`, `cansat_advanced` |
| CubeSat | 1U, 1.5U, 2U, 3U, 6U, 12U |
| Other | suborbital rocket payload, HAB, small drone, small rover |

This document describes the three collaborating registries that make
that possible and the end-to-end flow from template to firmware.

## Three collaborating registries

### 1. Form-factor registry — `flight-software/core/form_factors.py`

Authoritative source for **physical envelopes**:

- mass (`min_kg`, `max_kg`, `nominal_kg`)
- mechanical volume (`shape`, `dimensions_mm`, `volume_cm3`)
- power (`peak_w`, `average_w`, `battery_capacity_wh_typical`, `solar_capable`)
- allowed ADCS tiers and radio bands
- regulation notes (CDS Rev. 14, ESA CanSat regulations, FAA Part 101…)

Each entry is a frozen dataclass with helpers such as `check_mass()` and
`is_adcs_tier_supported()`.

### 2. Feature-flag resolver — `flight-software/core/feature_flags.py`

Registry of optional capabilities (`orbit_predictor`, `reaction_wheels`,
`descent_controller`, `parachute_pyro`, `s_band_radio`, `camera`, …).
Each `FeatureDescriptor` declares:

- default value when unset
- platforms / form factors it applies to
- required ADCS tier or radio band

At runtime `resolve_flags(profile, form_factor, config)` returns a
`ResolvedFlags` object that records, for every flag, whether it is
**enabled / disabled** and a human-readable **reason**. The decision
pipeline is deterministic:

```
explicit override  →  platform match  →  form-factor match
                                       →  ADCS tier match
                                       →  radio band match  →  default
```

An explicit `features.<flag> = false` in `mission_config.json` always
wins; an explicit `true` wins against the gates (the configurator
surfaces envelope conflicts separately so the operator is never
silently overruled).

### 3. Mission-type registry — `flight-software/core/mission_types.py`

Built-in `MissionProfile` objects for every supported mission type,
including a full phase graph (`pre_launch → ascent → apogee → descent →
landed` for CanSat; `startup → deployment → detumbling → nominal →
science → comm_window → safe_mode → low_power` for CubeSat LEO).

The size-specific CubeSat profiles (`CUBESAT_1U` … `CUBESAT_12U`) reuse
the LEO phase graph and differ only in telemetry rate, module list, and
the `competition.form_factor` key consumed by the form-factor
registry.

## End-to-end flow

1. **Pick a template** from `mission_templates/` (e.g. `cubesat_3u.json`)
   and copy it to `mission_config.json` at the repository root.
2. **Launch the flight controller** — `flight-software/flight_controller.py`
   parses the config, resolves the profile, and dynamically loads only
   the modules declared in `profile.core_modules` + enabled optional
   modules.
3. **Build the firmware** with the matching profile target:

   ```bash
   make target-cubesat-3u       # → firmware/build-arm-cubesat-3u/
   ```

   Each target defines `-DMISSION_PROFILE_<NAME>=1` so
   `firmware/stm32/Core/Inc/mission_profile.h` brings in exactly the
   `PROFILE_FEATURE_*` macros for that vehicle.
4. **Start the ground station** — `ground-station/app.py` also reads
   `mission_config.json`; every page calls `utils.profile_gate.page_applies()`
   and the irrelevant ones (orbit tracker for CanSat, image viewer
   without a camera, ADCS monitor without an ADCS subsystem) auto-hide
   with a short notice.

## Mapping template ↔ profile ↔ firmware build

| Template | MissionType | Form factor | Firmware target | Nominal mass |
|---|---|---|---|---:|
| `cansat_minimal.json` | `CANSAT_MINIMAL` | `cansat_minimal` | `target-cansat-minimal` | ~130 g |
| `cansat_standard.json` | `CANSAT_STANDARD` | `cansat_standard` | `target-cansat-standard` | ~170 g |
| `cansat_advanced.json` | `CANSAT_ADVANCED` | `cansat_advanced` | `target-cansat-advanced` | ~250 g |
| `cubesat_1u.json` | `CUBESAT_1U` | `cubesat_1u` | `target-cubesat-1u` | ~0.42 kg |
| `cubesat_1_5u.json` | `CUBESAT_1_5U` | `cubesat_1_5u` | `target-cubesat-1-5u` | ~0.7 kg |
| `cubesat_2u.json` | `CUBESAT_2U` | `cubesat_2u` | `target-cubesat-2u` | ~1.2 kg |
| `cubesat_3u.json` | `CUBESAT_3U` | `cubesat_3u` | `target-cubesat-3u` | ~1.28 kg |
| `cubesat_6u.json` | `CUBESAT_6U` | `cubesat_6u` | `target-cubesat-6u` | ~7.1 kg |
| `cubesat_12u.json` | `CUBESAT_12U` | `cubesat_12u` | `target-cubesat-12u` | ~16 kg |

## Adding a new form factor

1. Call `_register(FormFactor(...))` in `flight-software/core/form_factors.py`.
2. Add a matching `MissionType` entry and factory in
   `flight-software/core/mission_types.py`.
3. Drop a template JSON file into `mission_templates/`.
4. Add a reference BOM in `hardware/bom/by_form_factor/`.
5. Add a per-profile Makefile target (follow the pattern in the
   existing `target-cubesat-*` rules).
6. (Optional) Extend `firmware/stm32/Core/Inc/mission_profile.h` with a
   new `MISSION_PROFILE_<NAME>` block.

Tests under `flight-software/tests/test_form_factors.py`,
`test_feature_flags.py`, and `test_new_profiles.py` should be extended
to cover the new entry.
