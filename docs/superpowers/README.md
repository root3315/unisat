# docs/superpowers/ — Historical design + implementation plans

> **ℹ️ STATUS: ARCHIVED**
>
> The plans and specs under this directory were written during
> **Track 1 / Track 1b** (AX.25 link layer + HMAC dispatcher,
> March–April 2026). They describe the *original* design intent and
> the step-by-step implementation sequence that landed the first
> version of the AX.25 + CCSDS + HMAC stack.
>
> **These documents are preserved for historical reference only.**
> The current behaviour of the code diverges from these plans in
> several places because Phase 2–8 TRL-5 hardening refined the APIs:
>
> * Replay protection (ADR-004) — the dispatcher wire format now
>   prepends a 4-byte counter; the plans reference a single
>   body+HMAC layout.
> * Persistent key store (ADR-003) — the plans assume a key is
>   set by boot code; the production firmware reads it from A/B
>   flash via `key_store.c`.
> * FDIR advisor/commander split (ADR-005) — the plans don't
>   anticipate `mode_manager.c`; FDIR was originally drafted as
>   a single module.

## If you're here because you followed a link from…

* **SRS or traceability CSV** → use `docs/requirements/SRS.md`
  and `docs/requirements/traceability.csv` for current state.
* **Architecture page** → current layout is in
  `docs/architecture.md` + the eight ADRs under `docs/adr/`.
* **Threat model** → `docs/security/ax25_threat_model.md` is
  up-to-date with T1 and T2 both mitigated.
* **FDIR policy** → `docs/reliability/fdir.md` is the current
  authoritative doc.

## Documents preserved here

| File | Content |
|---|---|
| [specs/2026-04-17-track1-ax25-design.md](specs/2026-04-17-track1-ax25-design.md) | Original 775-line AX.25 design spec (Track 1) |
| [plans/2026-04-17-track1-ax25-implementation.md](plans/2026-04-17-track1-ax25-implementation.md) | 4022-line implementation plan that landed the AX.25 library |

## What replaced this directory

The `docs/` tree now uses lightweight ADRs (300-400 lines each)
plus a living SRS for design communication. The "superpowers"
prefix was a naming quirk of the initial planning phase and is
no longer in active use — newer design decisions go directly into
`docs/adr/ADR-NNN-<topic>.md`.
