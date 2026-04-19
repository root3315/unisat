# UniSat documentation

One file per concern, organised by purpose. Start here if you are new.

## Quick paths

| I want to… | Read this |
|---|---|
| Clone, build, and fly a reference mission | [`guides/USAGE_GUIDE.md`](guides/USAGE_GUIDE.md) → [`guides/OPERATIONS_GUIDE.md`](guides/OPERATIONS_GUIDE.md) |
| Pick the right mission profile | [`ops/README.md`](ops/README.md) |
| Understand how the system fits together | [`design/architecture.md`](design/architecture.md) |
| Know what works and what is still TODO | [`project/GAPS_AND_ROADMAP.md`](project/GAPS_AND_ROADMAP.md) |
| Look up an API | [`reference/API_REFERENCE.md`](reference/API_REFERENCE.md) |
| Submit to a competition | [`../COMPETITION_GUIDE.md`](../COMPETITION_GUIDE.md) + `ops/<profile>.md` |

## `guides/` — user-facing walkthroughs

- [`USAGE_GUIDE.md`](guides/USAGE_GUIDE.md) — end-to-end step-by-step for someone who just cloned the repo. Covers every supported competition.
- [`OPERATIONS_GUIDE.md`](guides/OPERATIONS_GUIDE.md) — 12-section playbook from profile selection to flight-day roles.
- [`TROUBLESHOOTING.md`](guides/TROUBLESHOOTING.md) — common build / run / integration issues and their fixes.

## `ops/` — per-profile operations guides (one per form factor)

Granular ops for a specific vehicle class: setup → build → flight → post-flight.

- CanSat: [`cansat_minimal`](ops/cansat_minimal.md), [`cansat_standard`](ops/cansat_standard.md), [`cansat_advanced`](ops/cansat_advanced.md)
- CubeSat: [`cubesat_1u`](ops/cubesat_1u.md), [`cubesat_1_5u`](ops/cubesat_1_5u.md), [`cubesat_2u`](ops/cubesat_2u.md), [`cubesat_3u`](ops/cubesat_3u.md), [`cubesat_6u`](ops/cubesat_6u.md), [`cubesat_12u`](ops/cubesat_12u.md)
- Other platforms: [`rocket_avionics`](ops/rocket_avionics.md), [`hab_payload`](ops/hab_payload.md), [`drone`](ops/drone.md)
- Index + selection flowchart: [`ops/README.md`](ops/README.md)

## `design/` — architecture and design decisions

- [`architecture.md`](design/architecture.md) — layered architecture, bus map, form-factor registry
- [`universal_platform.md`](design/universal_platform.md) — how one code base serves 14 form factors
- [`mission_design.md`](design/mission_design.md) — mission concept of operations
- [`communication_protocol.md`](design/communication_protocol.md) — AX.25 + CCSDS wire format
- [`assembly_guide.md`](design/assembly_guide.md) — physical assembly steps

## `budgets/` — quantitative analyses (CubeSat 3U reference)

- [`mass_budget.md`](budgets/mass_budget.md) — 3U component mass breakdown with margins. Per-profile BOMs live in [`../hardware/bom/by_form_factor/`](../hardware/bom/by_form_factor/README.md).
- [`power_budget.md`](budgets/power_budget.md) — solar generation, consumption, storage
- [`link_budget.md`](budgets/link_budget.md) — UHF / S-band link calculations
- [`orbit_analysis.md`](budgets/orbit_analysis.md) — ground track, eclipse cycles, J2 perturbations
- [`thermal_analysis.md`](budgets/thermal_analysis.md) — orbital thermal environment

## `reference/` — API / standards / conventions

- [`API_REFERENCE.md`](reference/API_REFERENCE.md) — programmatic API surface
- [`TECHNICAL_DOCUMENTATION.md`](reference/TECHNICAL_DOCUMENTATION.md) — full technical deep-dive (~1200 lines)
- [`STYLE_GUIDE.md`](reference/STYLE_GUIDE.md) — code + prose conventions (Google-derived)
- [`REQUIREMENTS_TRACEABILITY.md`](reference/REQUIREMENTS_TRACEABILITY.md) — REQ → source → test mapping

## `project/` — project state and regulatory

- [`GAPS_AND_ROADMAP.md`](project/GAPS_AND_ROADMAP.md) — honest status, open work, out-of-scope items
- [`REGULATORY.md`](project/REGULATORY.md) — licensing, export, radio regulation compliance
- [`POSTER_TEMPLATE.md`](project/POSTER_TEMPLATE.md) — competition poster starter

## `adr/` — architecture decision records (8 ADRs)

Indexed in [`adr/README.md`](adr/README.md). Includes:

- ADR-001 — no CSP
- ADR-002 — style adapter
- ADR-003 — A/B key store
- ADR-004 — replay counter zero-sentinel
- ADR-005 — FDIR advisory split
- ADR-006 — .noinit persistent log
- ADR-007 — HAL shim strategy
- ADR-008 — command dispatcher wire format

## `hardware/` — hardware references

- [`CC1125_configuration.md`](hardware/CC1125_configuration.md) — UHF transceiver register map
- [`radiation_budget.md`](hardware/radiation_budget.md) — TID / SEE design budget per orbital class (STM32 + sensors + radios)

## `testing/` — verification and test plans

- [`testing_plan.md`](testing/testing_plan.md) — overall V&V strategy
- [`hil_test_plan.md`](testing/hil_test_plan.md) — hardware-in-the-loop bench procedure (bench BOM + 10 tests)

## `characterization/` — measured baselines

- [`power_profile.md`](characterization/power_profile.md) — measured power consumption by task
- [`stack_usage.md`](characterization/stack_usage.md) — per-task stack high-water marks
- [`wcet.md`](characterization/wcet.md) — worst-case execution time per subsystem
- Index: [`characterization/README.md`](characterization/README.md)

## `verification/` — auto-generated verification artefacts

- [`ax25_trace_matrix.md`](verification/ax25_trace_matrix.md) — REQ → test mapping (auto-generated via `make trace`)
- [`driver_audit.md`](verification/driver_audit.md) — proof every driver is real, not a mock

## `security/` — threat model + mitigations

- [`ax25_threat_model.md`](security/ax25_threat_model.md) — T1 (injection) + T2 (replay) + mitigations

## `quality/` — CI-enforced quality gates

- [`static_analysis.md`](quality/static_analysis.md) — cppcheck policy, coverage floors, sanitizers

## `reliability/` — FDIR and fault tolerance

- [`fdir.md`](reliability/fdir.md) — 12 fault IDs, severity ladder, advisor/commander split

## `requirements/` — Software Requirements Specification

- [`SRS.md`](requirements/SRS.md) — numbered REQs across 10 subsystems
- [`traceability.csv`](requirements/traceability.csv) — REQ → source file → test (machine-readable)

## `operations/` — on-orbit operations runbooks

- [`commissioning_runbook.md`](operations/commissioning_runbook.md) — post-deploy activation checklist

## `sbom/` — software bill of materials (SPDX)

- [`sbom-summary.md`](sbom/sbom-summary.md) — auto-generated by `make sbom`

## `tutorials/` — learning-oriented walkthroughs

- [`ax25_walkthrough.md`](tutorials/ax25_walkthrough.md) — byte-by-byte beacon decode

## `diagrams/` — SVG block diagrams

Referenced from `../README.md` and other docs.

## `superpowers/` — design specs + long-form implementation plans

Archived Track 1 (AX.25) design and implementation material under `superpowers/specs/` and `superpowers/plans/`.
