# <Mission name> — full mission documentation pack

Brief mission statement: what science / engineering objective this pack covers,
on which UniSat form factor (`cansat_standard`, `cubesat_3u`, …) and against
which competition or operational target.

## Document map

```
docs/missions/<mission_dir>/
├── README.md              ← this file
├── CDR.md                 ← Critical Design Review
├── SCIENCE_MISSION.md     ← H₀/H₁, sensor justification, analysis method
├── KEY_DATA_PACKET.md     ← key-data on-the-wire format and fallback plan
├── PRESENTATION.md        ← Marp slide deck (10 slides) with talking points
├── POSTER.md              ← A0 poster layout in ASCII plus typesetting notes
├── <COMPETITION>_COMPLIANCE.md ← regulation checklist (rename per competition)
└── baseline_sitl_dataset.csv   ← optional but strongly recommended
```

The mission's template preset lives outside this directory at
`mission_templates/<mission_name>.json` so it stays in the canonical templates
location; reference it from this README.

## Related tools

- `scripts/<analysis_script>.py` — post-flight CSV processor for this mission's
  key data (delete this section if no mission-specific analysis exists).

## How to use this template

1. Copy `docs/missions/_template/` to `docs/missions/<your_mission>/`.
2. Fill in each canonical document. Keep section headings stable so that
   reviewers can navigate across packs by structure.
3. Append a row to [`docs/missions/README.md`](../README.md) under **Index**.
