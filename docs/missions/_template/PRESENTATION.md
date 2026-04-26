---
marp: true
theme: default
paginate: true
---

<!--
PRESENTATION.md is a Marp slide deck. Render with `marp PRESENTATION.md` or
preview in VS Code's Marp extension. Talking points live in HTML comments
under each slide so they do not appear in the rendered deck but are still
version-controlled with the slide.

Target: 10 slides, 10 minutes including Q&A.
-->

# <Mission name>

<!-- Talking points: introduce the team, the mission name, and the platform. -->

---

## Mission objective

- One bullet: the science / engineering question.
- One bullet: why it is non-trivial.
- One bullet: why it fits the chosen form factor.

<!-- Talking points: state H₀ / H₁ in plain language. -->

---

## Concept of operations

```
launch → ascent → apogee → descent → landed
```

<!-- Talking points: walk through the flight phases and call out the
science-collection window. -->

---

## Subsystems

| Subsystem | Choice | Why |
| --- | --- | --- |
| Power | … | … |
| Comms | … | … |
| Payload | … | … |

<!-- Talking points: highlight the one subsystem that drove the design. -->

---

## Science measurement

- Quantity, units, resolution.
- Expected magnitude and uncertainty.
- Sample count over the mission.

<!-- Talking points: contrast the expected H₁ result with H₀. -->

---

## Verification

- SITL coverage: which scripts run against `baseline_sitl_dataset.csv`.
- Hardware-in-the-loop: which subsystems are exercised on bench.
- Field test: what was demonstrated end-to-end before flight.

<!-- Talking points: name the one test that closes the highest-risk REQ. -->

---

## Risk register highlights

- Top three risks and their mitigations.

<!-- Talking points: be honest about residual risk. Juries reward this. -->

---

## Compliance summary

- One line per regulation: how this mission meets it.

<!-- Talking points: reference `<COMPETITION>_COMPLIANCE.md` for the full list. -->

---

## Schedule and team

- Major milestones with dates.
- Team roles.

<!-- Talking points: end with the next dated deliverable. -->

---

## Questions

- Contact email.
- Repository URL.
- Where the data will be published after the flight.

<!-- Talking points: leave 2 minutes for Q&A. -->
