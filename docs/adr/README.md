# Architecture Decision Records (ADRs)

Short records of architecturally-significant decisions taken
during UniSat development. One decision per file; each explains
the context, the choice made, the rationale, and the trade-offs
taken.

## Index

| ID | Title | Phase | Status |
|----|-------|------:|--------|
| [ADR-001](ADR-001-no-csp.md) | No CSP — use CCSDS directly | Track 1 | ✅ Accepted |
| [ADR-002](ADR-002-style-adapter.md) | AX.25 library style adapter | Track 1 | ✅ Accepted |
| [ADR-003](ADR-003-ab-keystore.md) | Dual-slot HMAC key store with CRC + monotonic generation | 2 | ✅ Accepted |
| [ADR-004](ADR-004-replay-counter-zero-sentinel.md) | Reserve counter = 0 as uninitialised sentinel | 2 | ✅ Accepted |
| [ADR-005](ADR-005-fdir-advisory-split.md) | FDIR as advisor; mode manager as commander | 3 + 7.3 | ✅ Accepted |
| [ADR-006](ADR-006-noinit-persistent-log.md) | Warm-reboot-survivable fault log via `.noinit` SRAM | 7.4 | ✅ Accepted |
| [ADR-007](ADR-007-hal-shim-strategy.md) | Weak HAL shim + optional autodetect | 1 | ✅ Accepted |
| [ADR-008](ADR-008-command-dispatcher-wire-format.md) | CCSDS-agnostic command-dispatcher wire format | 1b + 2 | ✅ Accepted |

## Format

Each ADR follows the lightweight Michael Nygard template:

* **Context** — the problem and the constraints
* **Decision** — what we chose
* **Rationale** — why
* **Consequences** — positive and negative trade-offs
* **Alternatives considered** — rejected options with reasons
* **Implementation** — pointer to the code / tests that realise it

## When to add an ADR

Add an ADR when a design decision:
* changes a cross-module contract,
* picks between two or more plausible alternatives with real
  trade-offs,
* will be hard to explain later from the code alone,
* was made under a constraint (time / scope / compatibility) that
  a future reader cannot see.

Conversely: do NOT add an ADR for routine style choices, bug
fixes, or implementation details that belong in a code comment.
