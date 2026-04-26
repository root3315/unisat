# Mission packs

Each subdirectory under `docs/missions/` is a complete **mission pack**: the full
documentation set for one specific science mission on a UniSat platform. A mission
pack ships every artefact a competition jury or internal CDR review needs in one
place — design review, science justification, key-data format, presentation,
poster, compliance checklist, and a baseline SITL dataset.

If you are starting a new mission, copy [`_template/`](_template/) and fill in
the seven canonical documents.

## Index

| Mission | Science objective | Form factor | Template preset | Pack |
| --- | --- | --- | --- | --- |
| `cansat_radiation` | Vertical gamma dose-rate profile 0–500 m at ≤ 10 m resolution (SBM-20 Geiger tube) | `cansat_standard` (Ø 68 × 80 mm, ≤ 500 g) | [`cansat_uzcansat.json`](../../mission_templates/cansat_uzcansat.json), [`cansat_standard.json`](../../mission_templates/cansat_standard.json) | [pack](cansat_radiation/) |

> Future mission packs (hyperspectral 6U Earth observation, 3U SSO technology
> demonstrator, HAB telemetry) will be added here as they ship. See
> [`docs/budgets/mass_budget.md`](../budgets/mass_budget.md) for the upcoming
> form-factor budgets that pack authors should target.

## What a complete mission pack contains

The seven canonical documents come from the `cansat_radiation` precedent — the
first pack that closed all four UzCanSat 2026 regulatory weaknesses. Each pack
should include:

| Document | Purpose |
| --- | --- |
| `README.md` | One-page overview: mission, form factor, document map, related tools. |
| `CDR.md` | Critical Design Review — ConOps, requirements, subsystems, tests, REQ-traceability. |
| `SCIENCE_MISSION.md` | Hypotheses (H₀/H₁), sensor justification, expected data, analysis method. |
| `KEY_DATA_PACKET.md` | On-the-wire format for the key-data beacon plus a fallback plan. |
| `PRESENTATION.md` | Marp slide deck (10 slides) with talking points in HTML comments. |
| `POSTER.md` | A0 poster layout in ASCII plus typesetting notes. |
| `*_COMPLIANCE.md` | Regulation-specific checklist (UzCanSat, CanSat Russia, ESA, …). |

A baseline SITL dataset (`baseline_sitl_dataset.csv`) is strongly recommended so
post-flight analysis scripts can be regression-tested against a known-good
trajectory.

The mission template preset (the `mission_templates/*.json` file) lives **outside**
the mission pack so it stays in the canonical templates location; the pack
references it from `README.md`.

## Authoring a new pack

1. `cp -r docs/missions/_template/ docs/missions/<your_mission>/`
2. Fill in each of the seven documents. Keep the section structure — readers
   navigate by it across packs.
3. Add the corresponding `mission_templates/<your_mission>.json` preset (see
   existing presets for shape).
4. Append a row to the **Index** table above.
5. If your mission targets a specific competition, add a `<competition>_COMPLIANCE.md`
   modelled on [`cansat_radiation/UZCANSAT_COMPLIANCE.md`](cansat_radiation/UZCANSAT_COMPLIANCE.md).
