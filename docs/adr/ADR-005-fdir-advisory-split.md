# ADR-005: FDIR as advisor; mode manager as commander

**Status:** Accepted — 2026-04-17
**Phases:** 3 (FDIR advisor) + 7.3 (mode manager)
**Commits:** 454422c, 619d980

## Context

The UniSat firmware needs both fault tracking and fault response.
The naive design puts them in the same module: a single
`fdir_tick()` that detects, counts, decides, and enacts the
recovery (safe-mode entry, subsystem disable, NVIC reset). This
couples three independent concerns:

1. **Detection / tracking.** "Has FAULT_X fired and how often?"
   Pure bookkeeping — reusable, testable in isolation.
2. **Recovery policy.** "Given the counters, what should happen?"
   Configuration-driven — the fault-action table belongs in a
   single source of truth.
3. **Mode transition.** "Actually enter safe mode / reset the
   core." Runtime side effect with platform dependencies
   (NVIC_SystemReset, subsystem disable hooks).

Mixing all three in one file forces unit tests to pull in NVIC
headers just to verify escalation arithmetic, and hides actual
transitions behind mock layers that drift out of sync with
production code.

## Decision

Split into two modules with a clean hand-off:

* **`fdir.c` — advisor only.** Tracks fault counters, maintains
  the fault table + escalation thresholds, exposes
  `FDIR_GetRecommendedAction(id)` — but never invokes a
  transition itself.
* **`mode_manager.c` — commander.** Runs from `WatchdogTask` at
  1 Hz, polls every fault id via `FDIR_GetRecommendedAction`,
  selects the worst-severity recommendation, and enacts the
  corresponding `EnterSafe` / `EnterDegraded` /
  `RequestReboot`. Platform hook `ModeManager_PlatformReboot()`
  is weak so tests provide their own.

Schema:

```
  driver detects fault
         │
         ▼
   FDIR_Report(FAULT_X)            <- advisory, just counts
         │
         ▼
   FDIR_GetRecommendedAction(X)    <- looks up the table
         │
         ▼
   ModeManager_Tick(): worst-case  <- commanding
         │
         ▼
   EnterSafe / Degraded / Reboot   <- state change + telemetry
         │
         ▼
   NVIC_SystemReset (on target)    <- platform hook
```

## Rationale

* **Unit-testability.** `test_fdir.c` needs zero HAL includes;
  `test_mode_manager.c` runs the full supervisor by overriding
  a single weak symbol.
* **Observability.** Downlink telemetry can report the delta:
  "FDIR recommended SAFE_MODE at tick X, supervisor was
  already in SAFE_MODE, no transition" — a distinction that
  matters to ops but would be lost if FDIR both decided and
  enacted.
* **Graceful future change.** A ground command can override the
  supervisor's decision without touching FDIR; FDIR stays the
  stable contract, mode_manager is the swappable policy engine.
* **No hidden side effects.** A test or a developer reading
  `fdir.c` never wonders "will calling Report reset the MCU?"
  — the module explicitly cannot.

## Consequences

Positive:
* Two small, focused modules (165 + 175 LoC)
* Per-module unit tests (9/9 each) without cross-contamination
* Ground operator has visibility into "advised vs enacted"
* Weak platform hook makes the reboot path testable

Negative:
* Two sources of truth about fault severity (FDIR table
  + mode_manager action mapping) — kept in sync by documented
  severity-ladder ordering in `fdir.h`
* One extra function call per fault event (`GetRecommendedAction`)
  — negligible at 1 Hz supervisor cadence

## Alternatives considered

* **Monolithic fdir.c.** Rejected — couples tracking, policy,
  and enaction; tests force HAL includes.
* **Full event bus.** Overkill for 12 fault IDs; introduces
  message-order dependencies and a dispatcher layer that add
  latency to a time-sensitive safety path.

## Implementation

See:
* `firmware/stm32/Core/Src/fdir.c` + `fdir.h`
* `firmware/stm32/Core/Src/mode_manager.c` + `mode_manager.h`
* `docs/reliability/fdir.md` for the table + severity ladder

Tests:
* `firmware/tests/test_fdir.c` — 9/9
* `firmware/tests/test_mode_manager.c` — 9/9

## Follow-up fix

While implementing mode_manager the test suite exposed a latent
bug in `FDIR_GetRecommendedAction`: it returned the primary
action even for faults that had never been reported
(recent_count == 0). That's semantically wrong — a fault with no
active report should not drive a recovery. The fix — adding a
`recent_count == 0 -> LOG_ONLY` fast-path at the top — is part
of the 619d980 commit; two pre-existing test_fdir tests were
updated to match the corrected semantics.
