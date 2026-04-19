# Mission templates

Ready-to-copy mission configurations. Each JSON is a self-contained `mission_config.json` for a specific form factor or competition. Pick one, copy it to the repository root as `mission_config.json`, and the whole stack (firmware, flight-software, ground-station) reconfigures itself automatically.

```bash
cp mission_templates/<choice>.json mission_config.json
```

## Generic form-factor templates

One per registered form factor — the starting point for any new mission.

| File | Form factor | Max mass | Typical radio | Notes |
|---|---|---:|---|---|
| `cansat_minimal.json` | `cansat_minimal` | 350 g | LoRa 433 MHz | Telemetry-only, first CanSat |
| `cansat_standard.json` | `cansat_standard` | 500 g | LoRa 433 MHz | Ø68×80 mm CDS, generic 10 Hz telemetry |
| `cansat_advanced.json` | `cansat_advanced` | 500 g | LoRa + UHF | Pyro deploy + camera + guided descent |
| `cubesat_1u.json` | `cubesat_1u` | 2 kg | UHF amateur | First CubeSat |
| `cubesat_1_5u.json` | `cubesat_1_5u` | 3 kg | UHF amateur | Intermediate when 1U is tight |
| `cubesat_2u.json` | `cubesat_2u` | 4 kg | UHF + S-band | Tech demo |
| `cubesat_3u.json` | `cubesat_3u` | 6 kg | UHF + S + X | **TRL-5 reference** |
| `cubesat_6u.json` | `cubesat_6u` | 12 kg | UHF + S + X + Ka | Fine pointing |
| `cubesat_12u.json` | `cubesat_12u` | 24 kg | S + X + Ka + optical | Research-class + propulsion |
| `cubesat_sso.json` | `cubesat_3u` | 6 kg | — | 3U in sun-synchronous orbit |
| `hab_standard.json` | `hab_payload` | 4 kg | ISM / APRS | High-altitude balloon |
| `drone_survey.json` | `drone_small` | 5 kg | ISM 2.4 GHz | UAV survey / inspection |
| `rocket_competition.json` | `rocket_payload` | 10 kg | UHF | IREC / SA Cup |

## Competition-specific presets

Inherit a generic form-factor profile, then override the handful of settings a specific competition's rulebook pins. The generic profile stays clean — competitions are overlays, not forks.

| File | Regulation | What it pins | Source |
|---|---|---|---|
| `cansat_uzcansat.json` | **🇺🇿 UzCanSat 2026** (Uzcosmos / ICESCO / cmspace.uz) | `telemetry_hz=1.0`, buzzer locator on, camera 640×480 @ 30 fps horizontal + SD, bonus tasks (real-time altitude + instantaneous velocity) enabled | [cmspace.uz/youth-projects/16](https://training.cmspace.uz/youth-projects/16) · [full compliance doc](../docs/missions/cansat_radiation/UZCANSAT_COMPLIANCE.md) · [original files](../docs/missions/cansat_radiation/references/official/) |

## Adding a new competition

If a new competition arrives with different rulebook requirements (ESERO, NASA-CanSat, national olympiad …):

1. Find the generic profile that matches the form factor (`cansat_standard`, `cubesat_3u`, …).
2. Copy that generic template and name it after the competition: `cp cansat_standard.json cansat_<competition>.json`.
3. Override only the fields the rulebook pins — leave everything else inherited.
4. Add a compliance document under `docs/missions/<competition>/` that traces every rulebook clause to the repo artefact satisfying it.
5. Add a row to the table above.

**Don't modify the generic profile.** The whole point of the universal platform is that new competitions arrive as JSON overlays, not as branches of core code. Generic `cansat_standard` must stay useful to the next team with a different rulebook.

## Validation

Every template here is covered by `configurator/tests/test_validators.py::test_every_template_references_a_known_form_factor` — the cross-consistency test makes sure every `satellite.form_factor` resolves to an entry in `flight-software/core/form_factors.py`.

Run the full regression with `pytest configurator/tests/ -q` before committing any new template.
