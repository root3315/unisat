# Per-Profile Operations Guides

UniSat ships one codebase that targets 17 canonical hardware form
factors.  Each one has a different mass / volume / power budget,
different regulatory context, and different flight ops.  This folder
collects a **step-by-step runbook per profile** so a new team can go
from "cloned the repo" to "integrated & ready to fly" without
cross-referencing the whole documentation set.

Every guide follows the same twelve-section template:

1. **Mission class** — what this profile is for (competition / science / education).
2. **Physical envelope** — mass, volume, dimensions, power.
3. **Regulatory context** — which rulebook the flight must comply with.
4. **Subsystem matrix** — what the form factor allows / requires / forbids.
5. **Build** — exact `make target-<profile>` invocation.
6. **Mission config** — which `mission_templates/*.json` to copy and what to edit.
7. **Mass & volume validation** — what the configurator should show.
8. **Typical mission phases** — operational sequence at a glance.
9. **Testing checklist** — what to prove on the bench before flight.
10. **Flight-day checklist** — final pre-launch verification.
11. **Known limitations** — hard stops you cannot work around on this profile.
12. **Post-flight debrief** — what data to capture and where.

## Index

### CanSat family

| Profile                          | Best for                            | Mass cap | Guide |
|----------------------------------|-------------------------------------|----------|-------|
| `cansat_minimal`                 | First-time teams, schools           | 350 g    | [cansat_minimal.md](cansat_minimal.md) |
| `cansat_standard`                | ESERO / national CanSat competitions| 500 g    | [cansat_standard.md](cansat_standard.md) |
| `cansat_advanced`                | NASA CanSat / deployable payload    | 700 g    | [cansat_advanced.md](cansat_advanced.md) |

### CubeSat family

| Profile                          | Best for                            | Mass cap | Guide |
|----------------------------------|-------------------------------------|----------|-------|
| `cubesat_1u`                     | Educational LEO tech demo           | 1.33 kg  | [cubesat_1u.md](cubesat_1u.md) |
| `cubesat_1_5u`                   | Compact tech demo                   | 2.0 kg   | [cubesat_1_5u.md](cubesat_1_5u.md) |
| `cubesat_2u`                     | Small science / imaging             | 2.66 kg  | [cubesat_2u.md](cubesat_2u.md) |
| `cubesat_3u`                     | **UniSat TRL-5 reference**          | 4.0 kg   | [cubesat_3u.md](cubesat_3u.md) |
| `cubesat_6u`                     | Earth observation / deployable      | 12.0 kg  | [cubesat_6u.md](cubesat_6u.md) |
| `cubesat_12u`                    | Long-duration / deep-space tech     | 24.0 kg  | [cubesat_12u.md](cubesat_12u.md) |

### Suborbital & atmospheric

| Profile                          | Best for                            | Mass cap | Guide |
|----------------------------------|-------------------------------------|----------|-------|
| `rocket_avionics`                | IREC / SA Cup / Team America        | 0.5 kg   | [rocket_avionics.md](rocket_avionics.md) |
| `hab_payload_medium`             | Standard HAB flights                | 2.0 kg   | [hab_payload.md](hab_payload.md) |
| `drone_small` / `drone_medium`   | UAV survey / inspection             | 2.5 / 5.0 kg | [drone.md](drone.md) |

## Shared prerequisites

Before diving into a profile-specific guide, confirm the following:

```
git clone https://github.com/root3315/unisat
cd unisat
./scripts/verify.sh             # "✓ UniSat green" — builds + passes every test
```

On a bare checkout the verify step will:

* build the firmware host image (no ARM toolchain required);
* run 28 ctest targets + 386 pytest cases + the SITL AX.25 demo;
* confirm the `mission_templates/*.json` ↔ `form_factors.py` ↔ `hardware/bom/by_form_factor/*.csv` cross-consistency.

If any stage is red, **do not start the profile setup**. Open the
failing log and fix (or file an issue) before continuing — the per-
profile guides assume a green baseline.

## Form-factor selection flowchart

```
                  ┌────────────────────────────┐
                  │   Does it leave the        │
                  │   atmosphere (≥ 100 km)?   │
                  └──────────┬─────────────────┘
                  Yes        │          No
            ┌────────────────┘          └────────────┐
            ▼                                        ▼
  ┌──────────────────┐                     ┌──────────────────┐
  │  Orbital class → │                     │  Is it a balloon │
  │  CubeSat 1U–12U  │                     │  (float-capable)?│
  └────┬─────────────┘                     └────────┬─────────┘
       │                               Yes          │   No
       ▼                           ┌────────────────┘   │
┌──────────────────┐               ▼                    ▼
│ 1U / 1.5U for    │     ┌──────────────────┐  ┌──────────────────┐
│ first mission;   │     │  HAB profile     │  │  Is it deployed  │
│ 3U is the TRL-5  │     │  hab_payload_*   │  │  from a rocket?  │
│ flagship;        │     └──────────────────┘  └─────────┬────────┘
│ 6U/12U for       │                        Yes          │   No
│ imaging / tech.  │                 ┌──────────────────┘   │
└──────────────────┘                 ▼                      ▼
                           ┌──────────────────┐   ┌──────────────────┐
                           │  CanSat profile  │   │  Is it airborne  │
                           │  cansat_*        │   │  under power?    │
                           └──────────────────┘   └─────────┬────────┘
                                                       Yes  │
                                                            ▼
                                                   ┌──────────────────┐
                                                   │  Drone profile   │
                                                   │  drone_small/med │
                                                   └──────────────────┘
```

## Tooling the guides refer to

| Command                               | What it does                                         |
|---------------------------------------|------------------------------------------------------|
| `make target-<profile>`               | Cross-compile firmware with the profile's macro      |
| `make configurator`                   | Launch the Streamlit mission-config wizard           |
| `scripts/verify.sh`                   | Full green pipeline (CI-equivalent, no Docker needed)|
| `scripts/simulate_mission.sh`         | SITL run of the loaded mission_config.json           |
| `python3 scripts/gen_golden_vectors.py` | Regenerate AX.25 golden vectors                    |
| `make lint-py` / `make coverage-py`   | Python type + coverage gates                         |
| `make cppcheck` / `make coverage`     | C static analysis + line-coverage gates              |

## Cross-references

* Architecture overview — [`docs/architecture.md`](../architecture.md)
* SRS + trace matrix    — [`docs/REQUIREMENTS_TRACEABILITY.md`](../REQUIREMENTS_TRACEABILITY.md)
* Commissioning runbook — [`docs/operations/commissioning_runbook.md`](../operations/commissioning_runbook.md)
* Radiation budget      — [`docs/hardware/radiation_budget.md`](../hardware/radiation_budget.md)
* Threat model          — [`docs/security/ax25_threat_model.md`](../security/ax25_threat_model.md)
