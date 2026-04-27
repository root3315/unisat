# Critical Design Review — <Mission name>

**Mission:** one-sentence statement of the science / engineering objective.

**Form factor:** `<cansat_standard | cubesat_1u | …>` — physical envelope, mass
budget, applicable platform standard.

**Team:** *[team name]* · Contact: *[email]* · Code: [github.com/root3315/unisat](https://github.com/root3315/unisat)

---

## 1. Concept of Operations (ConOps)

```
t=0s    Ground checkout       → describe what is verified before launch
t=Ns    Launch                → describe trigger and detection
t+30s   Ascent (~h m)         → describe ascent envelope
t+35s   Apogee / ejection     → describe deployment
t+36s   Descent ~v m/s        → describe data collection schedule
t+95s   Landed                → describe landing artefacts and beacon
```

State the total flight duration and which subsystems are active at each phase.

---

## 2. Science / engineering objective

Reference [`SCIENCE_MISSION.md`](SCIENCE_MISSION.md) and summarise here in three
to five bullets. State what makes this mission non-trivial relative to a
generic telemetry-only baseline.

---

## 3. Requirements (REQ traceability)

| ID | Requirement | Verification | Section |
| --- | --- | --- | --- |
| REQ-001 | … | test / inspection / analysis | §x |
| REQ-002 | … | … | … |

Every requirement listed here must be traceable to a verification activity in
§7 and to the corresponding line in `<COMPETITION>_COMPLIANCE.md`.

---

## 4. Subsystems

For each subsystem (power, comms, ADCS, payload, GNSS, …) describe:

- Components and part numbers.
- Interfaces (electrical, mechanical, data) — link to ICDs.
- Failure modes and mitigations.
- Mass / power / data-rate budget contribution.

---

## 5. Mass / power / data budgets

Reference [`docs/budgets/`](../../budgets/) and summarise the values for this
mission. Highlight any line item over 80 % of its allocation.

---

## 6. Risk register

| Risk | Likelihood | Severity | Mitigation |
| --- | --- | --- | --- |
| … | L / M / H | L / M / H | … |

---

## 7. Verification plan

Enumerate the tests that close every requirement from §3. Each row should
reference a script, fixture, or procedure that can be re-run.

| Test | Closes | Method | Artefact |
| --- | --- | --- | --- |
| TEST-001 | REQ-001 | SITL run on `baseline_sitl_dataset.csv` | log path |
| … | … | … | … |

---

## 8. Open issues

A short list of decisions still pending. Each item should have an owner and a
target review date.
