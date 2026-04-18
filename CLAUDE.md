# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

**UniSat** — universal modular satellite software platform. **v1.3.0** extended support from CubeSat-only to a multi-class registry: CanSat (minimal/standard/advanced), CubeSat (1U/1.5U/2U/3U/6U/12U), suborbital rocket, HAB, drone, rover, custom. TRL-5-hardened on the CubeSat-3U reference profile. Three cooperating codebases share one repo and one on-air protocol stack:

- **`firmware/`** — STM32F446RE OBC firmware in C11 + FreeRTOS (host-buildable for tests; cross-compiles to `.elf/.bin/.hex` when `arm-none-eabi-gcc` is on PATH).
- **`flight-software/`** — Python 3.11 asyncio mission controller meant to run on a Raspberry Pi Zero 2 W, talking to the OBC over UART.
- **`ground-station/`** — Streamlit dashboard + AX.25 CLI tooling (`cli/ax25_listen`, `cli/ax25_send`).

Plus: `simulation/` (orbit/power/thermal/link Python sims), `configurator/` (Streamlit mission builder), `payloads/` (plugin templates), `hardware/` (KiCad + BOM), `docs/` (SRS, ADRs, threat model, trace matrix).

License: Apache-2.0 (migrated from MIT on 2026-04-18). Patent-grant clause is load-bearing — don't suggest license changes.

## Common commands

The `Makefile` at the repo root is the canonical entry point. `make` with no arg prints the target list.

```bash
make all              # host build + ctest + pytest
make ci               # same, inside the unisat-ci Docker image (no local toolchain needed)
./scripts/verify.sh   # one-shot reproducibility check; prints "✓ UniSat green" when everything passes
make demo             # end-to-end SITL AX.25 beacon demo (C encoder → TCP → Python decoder)

make test-c           # ctest only (firmware/build, Unity targets)
make test-py          # pytest only (ground-station/tests/test_ax25.py)

# Firmware quality gates (all must stay green for merges)
make cppcheck         # cppcheck error/warning/portability gate
make coverage         # lcov html report; target ≥ 85 % C lines
make sanitizers       # ASAN + UBSAN ctest pass
cmake -B firmware/build -S firmware -DSTRICT=ON && cmake --build firmware/build
                      # -Werror -Wshadow -Wconversion gate

# Python gates
make coverage-py      # pytest + coverage on ground-station/ and flight-software/
make lint-py          # mypy --strict on flight-software/core + modules

# STM32F446RE cross-compile (one-time HAL fetch then build)
make setup-all        # fetch STM32Cube HAL + FreeRTOS kernel + CMSIS-RTOSv2
make target           # produces firmware/build-arm/unisat_firmware.{elf,bin,hex}
make size             # per-section flash/RAM (must stay under 90 % budget)
make flash            # st-flash to Nucleo-F446RE

# Generated artifacts (regenerate after touching sources)
make goldens          # tests/golden/ax25_vectors.{json,inc}
make trace            # docs/verification/ax25_trace_matrix.md
make sbom             # docs/sbom/sbom-summary.md (SPDX)
```

### Running a single test

- **C (Unity/ctest):** after `make build`, a single test executable is `firmware/build/test_<name>`. Run it directly, or `ctest --test-dir firmware/build -R <name> --output-on-failure`.
- **Python:** `cd ground-station && python3 -m pytest tests/test_ax25.py::TestClass::test_name -v`. Same pattern under `flight-software/tests/` and `simulation/tests/`.

## Architecture — what requires multi-file reading to understand

### 0. Universal platform: form-factor registry is the source of truth (v1.3.0)

`flight-software/core/form_factors.py` is the single source of truth for every supported vehicle class. Each `FormFactor` bundles mass/volume/power envelopes, allowed ADCS tiers, allowed comm bands, regulation notes. Consumers:

- **`flight-software/core/feature_flags.py`** — 3-tier resolver (`explicit override → form-factor gate → platform gate → default`) that selectively enables Python modules per profile.
- **`firmware/stm32/Core/Inc/mission_profile.h`** — compile-time mirror of the Python resolver. One firmware source → 9 build targets via `-DMISSION_PROFILE_<NAME>=1`. Default is `CUBESAT_3U` for backwards compat. `make target-<profile>` per profile.
- **`ground-station/utils/profile_gate.py`** — hides orbit/imagery/ADCS pages for non-orbital profiles (CanSat, HAB, drone).
- **`mission_templates/*.json`** — 8 ready-to-use presets (cansat_minimal/standard/advanced + cubesat_1u through 12u).
- **`hardware/bom/by_form_factor/*.csv`** — per-class BOM with real masses.

**Known parallel-truth debt (do not replicate):** `configurator/validators/mass_validator.py` and `volume_validator.py` still hold hardcoded dicts that predate `form_factors.py`. They know only a subset of profiles (no `cansat_minimal`, `cansat_advanced`, `cubesat_1_5u`). When touching validators, switch them to read from `form_factors.get_form_factor(key)` instead of extending the dicts. Same for `configurator/configurator_app.py` (lines ~18–44 hardcode form-factor lists).

When adding a new form factor: register it in `form_factors.py` **first**, then add template, BOM, feature-flag mapping in `feature_flags.py`, and a firmware profile macro in `mission_profile.h`. Don't forget `tests/test_form_factors.py`.

### 1. Two-processor split with a strict bus between them

Ground ↔ OBC over **UHF 437 MHz** using **AX.25 v2.2** framing wrapping **CCSDS** Space Packets, authenticated with **HMAC-SHA256 + 32-bit counter + 64-bit sliding-window replay filter** (threats T1 and T2 in `docs/security/ax25_threat_model.md`). OBC ↔ flight-software over **UART @ 115 200 baud** using plain CCSDS.

The **Application layer (Python on RPi) never reaches past Subsystem (STM32)** — it speaks CCSDS only. Enforced by the layer table in `docs/architecture.md` §3.2. Don't introduce direct sensor access from Python; go through OBC telemetry/commands.

### 2. AX.25 and HMAC have parallel C + Python implementations kept byte-identical

- C: `firmware/stm32/Drivers/AX25/`, `firmware/stm32/Drivers/Crypto/`
- Python: `ground-station/utils/ax25.py`, `ground-station/utils/hmac_auth.py`, `CounterSender` class
- Cross-validation: **28 shared golden vectors** in `tests/golden/ax25_vectors.{json,inc}`, consumed by both `test_ax25_golden.c` (Unity) and pytest. Regenerate with `make goldens` after protocol changes — *both* implementations must round-trip the new vectors.

### 3. Firmware has a host-mode build for testability

The whole OBC tree compiles on a workstation as `unisat_core` (a static lib + 27 Unity test targets) when `arm-none-eabi-gcc` is absent or when any of `-DSTRICT=ON / -DCOVERAGE=ON / -DSANITIZERS=ON / -DFORCE_HOST=ON` is passed. Hardware-touching paths are guarded by `#ifdef SIMULATION_MODE`. The `VirtualUART` driver is the SITL TCP shim used by `make demo`. When adding HAL-dependent code, always gate it and provide a host stub — otherwise `make test-c` breaks.

### 4. FDIR: three-tier fault handling with a split advisor/commander

`fdir.c` (advisor — classifies and logs) and `mode_manager.c` (commander — escalates to SAFE/DEGRADED/REBOOT) are deliberately separate per **ADR-005**. 12 fault IDs, 60 s escalation window, 6-level severity ladder. Persistent fault log lives in `.noinit` SRAM so it survives warm reboot. Don't collapse the two — the split is what lets the mode supervisor be unit-tested without hardware.

### 5. Layered driver architecture

Layer 4 (Application, Python) → Layer 3 (Subsystem, C) → Layer 2 (Driver, C) → Layer 1 (HAL) → Layer 0 (HW). **No layer may call more than one level down.** The 9 drivers under `firmware/stm32/Drivers/` are all in the "reality audit" (`docs/verification/driver_audit.md`) — they are real, not mocks.

### 6. Requirements traceability is a hard review gate

`docs/requirements/SRS.md` defines numbered REQs; `docs/requirements/traceability.csv` maps each to its source file and test. When you add a module, updating `docs/API_REFERENCE.md` and `docs/REQUIREMENTS_TRACEABILITY.md` is part of the change — see `docs/STYLE_GUIDE.md` §"Documentation roadmap for new modules" for the 6-item checklist.

## Code conventions (project-specific deltas from Google style)

See `docs/STYLE_GUIDE.md` for the full table. Key rules that bite:

- **C:** 4-space indent, 80-col hard limit, `module_snake_case()` for functions, `module_name_t` for types, `MODULE_UPPER_SNAKE` for public macros, every non-API function `static`, `#ifndef FILE_H` guards (never `#pragma once`), Doxygen `@file`/`@brief` at top of every `.c`/`.h`, return-status enums (never `errno`).
- **Python:** `black` line length 79, `mypy --strict` must be clean, Google-style docstrings, custom exception hierarchy rooted at `AX25Error` — never raise bare `Exception`.
- **Shell:** `#!/usr/bin/env bash` + `set -euo pipefail`, scripts land under `scripts/`.
- **Max 200 lines per file** (CONTRIBUTING.md §Code Style) — split before growing past this.

## Commit conventions

Conventional Commits: `<type>(<scope>): <imperative, ≤50 chars>`. Types: `feat fix docs test build ci perf refactor chore`. Scopes used in-tree: `ax25 comm dispatcher crypto gs-ax25 gs-cli firmware config docs build ci`. Body wraps at 72, explains **why**, not what. Reference REQ-IDs when touching requirements-traced code. See `docs/STYLE_GUIDE.md` §"Writing commit messages" for the good-vs-bad example.

## Things to know before editing

- `docs/adr/` holds 8 Architecture Decision Records. If a change contradicts an ADR, write a new ADR superseding it — don't silently diverge.
- The 48-hour soak harness (`flight-software/tests/test_long_soak.py`) is gated by `UNISAT_SOAK_SECONDS` env var; don't run it by default.
- `cmake -DSTRICT=ON` is the merge gate — a warning is a build failure. Host build must stay clean under `-Werror -Wshadow -Wconversion`.
- Coverage floors: **C ≥ 85 %**, **Python ≥ 80 % MUST / 85 % SHOULD** (`flight-software/pyproject.toml` `[tool.coverage.report]`).
- ARM footprint budget: flash ≤ 90 %, RAM ≤ 90 % of STM32F446RE. Current baseline 31.6 KB flash (6 %) / 36.3 KB RAM (28 %) — if `make size` shows a jump, investigate before merging.
