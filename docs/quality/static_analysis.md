# Static analysis, coverage, sanitizers (Phase 5)

**Scope:** host-side firmware and test sources under
`firmware/stm32/Core`, `firmware/stm32/Drivers`,
`firmware/stm32/ADCS`, `firmware/stm32/EPS`.

This document describes the four quality gates introduced in the
Phase 5 TRL-5 hardening work and how to run them locally or in CI.

## Gates overview

| Gate | Blocking | Runs in `verify.sh` | Command |
|------|----------|---------------------|---------|
| `cppcheck` (error/warning/portability) | ✅ yes | ✅ yes | `make cppcheck` |
| `cppcheck --strict` (+ MISRA advisory) | ❌ advisory | manual | `make cppcheck-strict` |
| `lcov` coverage | ⚠ opt-in | ✅ best-effort | `make coverage` |
| ASAN + UBSAN | ⚠ opt-in | manual | `make sanitizers` |

All four are exposed as top-level `make` targets and as CMake
options (`-DCOVERAGE=ON`, `-DSANITIZERS=ON`, `-DSTRICT=ON`).

## cppcheck

**Tool:** `cppcheck ≥ 2.9` with the MISRA-C:2012 addon.
**Wrapper:** `scripts/run_cppcheck.sh`.
**Suppressions:** `.cppcheck-suppressions` in repo root.

Two modes:

* **Default (CI-blocking).** Severity filter =
  `warning,portability` + all `error` rules. Catches the bugs
  that actually matter: null-deref, uninit read, buffer overflow,
  shift-too-many-bits, format-string mismatch, `badBitmaskCheck`
  (which found a real issue in `ccsds.c` during development and
  one false-positive in `comm.c` documented inline). Exit code
  is the pass/fail gate — any unsuppressed finding fails CI.

* **Strict (`--strict` flag).** Adds `style` + `performance` +
  the full MISRA-C:2012 addon. Does NOT fail the script — the
  existing codebase has hundreds of MISRA deviations (mostly
  Rule 8.7 "external linkage when used in one TU" and Rule 10.x
  implicit conversions) that are scheduled for cleanup as a
  separate roadmap item, not part of Phase 5. The strict run
  prints a deviation summary to stdout and writes the full log
  to `firmware/build/.cppcheck-cache/strict.log` so the backlog
  is trackable without blocking PRs.

Suppressions list is curated — every entry has a short rationale
in `.cppcheck-suppressions` (e.g. Rule 11.5 is routinely deviated
because STM32 HAL's `void *handle` convention requires the cast).

### Real issues found and fixed during development

1. **`comm.c:125` — arrayIndexOutOfBounds** on `dst_call[n]`.
   Cppcheck inferred that callers like `COMM_SendAX25(..., "CQ", ...)`
   pass a 3-byte string and the loop body could read up to
   `dst_call[5]`. The code is in fact safe because of the
   `!= '\0'` short-circuit, but cppcheck cannot prove the
   NUL-termination invariant. Suppressed inline with rationale.
2. **`ccsds.c:68` — badBitmaskCheck** on `(0 << 13) | ...`.
   The version-field OR with 0 is a no-op; the `(0 << 13)`
   spelling documented the CCSDS primary-header layout but
   generated a spurious warning. ✅ Fixed: removed the
   `0 << 13` and moved the field-layout documentation into a
   code comment that survives future version-field changes.
3. **ccsds.c / comm.c / payload.c / telemetry.c / error_handler.c /
   sbm20.c / virtual_uart.c — `-Wconversion` narrowings.** 12
   locations where an `int`-promoted arithmetic result was
   stored into a `uint8_t` / `uint16_t` without an explicit
   cast. ✅ Fixed: added `(uint8_t)` / `(uint16_t)` casts with
   explicit unsigned literals (`0xFFU`, `1U`, etc.) so the
   narrowing is visible in the diff and there is no surprise
   on a target where `int` is 32-bit.

## Coverage (lcov + genhtml)

Configure with `-DCOVERAGE=ON`, then build + `coverage` target.
Output: `firmware/build/coverage.info` + HTML under
`firmware/build/coverage_html/`.

```
make coverage
# ...
# Overall coverage rate:
#   lines......: 73.6% (866 of 1176 lines)
#   functions..: 69.9% (93 of 133 functions)
```

**Current numbers (Phase 5 baseline):**

| Metric | Value | Target |
|--------|------:|-------:|
| Line coverage (overall) | 73.6 % | ≥ 80 % for Phase 6 |
| Function coverage (overall) | 69.9 % | ≥ 85 % for Phase 6 |

The 6.4 % gap is concentrated in the EPS module (mppt.c,
battery_manager.c), AX.25 error paths (frame-corruption edge
cases), and the CCSDS secondary-header fields that the current
tests don't exercise. Closing the gap is the explicit Phase 6
work-item "expand test coverage".

## Sanitizers

Configure with `-DSANITIZERS=ON`. The host build links
`-fsanitize=address,undefined` and every `ctest` invocation runs
under ASAN + UBSAN. Catches:

* use-after-free, out-of-bounds heap / stack access (ASAN);
* shift of negative value, signed overflow, invalid enum
  value, alignment violations, misaligned loads (UBSAN).

Current repo state: 19 / 19 tests pass clean under sanitizers
(run `make sanitizers` to reproduce). A regression that adds a
memory bug is loud — the sanitizer report stops the test with
a full stack trace.

## STRICT build

`cmake -DSTRICT=ON` enables `-Werror -Wshadow -Wconversion` on
the host build. Primarily useful during refactoring — drives a
zero-warning policy for new code and catches narrowing bugs
before they reach the 32-bit MCU.

**Current status:** ✅ **STRICT passes — 19/19 ctest green.**
The post-Phase-5 cleanup commit made every narrowing explicit
(`(uint8_t)((x >> 8) & 0xFFU)` pattern) across `ccsds.c`,
`comm.c`, `error_handler.c`, `payload.c`, `telemetry.c`,
`sbm20.c`, and `virtual_uart.c`. The few legitimate exemptions
(unused static helpers gated behind `#ifndef SIMULATION_MODE`
in sensor drivers, Unity test framework's comma-expression) are
demoted to warnings with `-Wno-error=unused-function` /
`-Wno-error=unused-const-variable`.

Reproduction:
```
cmake -B firmware/build-strict -S firmware -DSTRICT=ON
cmake --build firmware/build-strict
ctest --test-dir firmware/build-strict --output-on-failure
# -> 100% tests passed, 0 tests failed out of 19
```

## Running everything

```
# fast green-path
make cppcheck && make test

# full local CI equivalent
make cppcheck && make sanitizers && make coverage && make ci

# deep MISRA audit
make cppcheck-strict
```

`scripts/verify.sh` exercises the whole pipeline end-to-end
inside the `unisat-ci` Docker image — cppcheck and lcov steps
are best-effort, they print a note and skip when the tool is
missing from the image so the existing green-path (16/16 ctest +
34/34 pytest + SITL) keeps working on stripped-down CI images.
