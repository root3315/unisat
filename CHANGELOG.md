# Changelog

All notable changes to UniSat will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.4.1] - 2026-04-19 — Docs tree reorganised + BOM corrections + bench-test verification

Zero behavioural changes. Reorganises the flat `docs/` root into
thematic subdirectories, rebuilds the README Documentation section,
verifies every testing-checklist item in the 12 per-profile ops
guides, and corrects two wrong component masses in the CanSat BOM.

### Changed — docs/ tree reorganised

The 21 markdown files in `docs/` root are now grouped by purpose:

- **`docs/guides/`** — `USAGE_GUIDE.md`, `OPERATIONS_GUIDE.md`, `TROUBLESHOOTING.md`
- **`docs/design/`** — `architecture.md`, `universal_platform.md`, `mission_design.md`, `communication_protocol.md`, `assembly_guide.md`
- **`docs/budgets/`** — `mass_budget.md`, `power_budget.md`, `link_budget.md`, `orbit_analysis.md`, `thermal_analysis.md`
- **`docs/reference/`** — `API_REFERENCE.md`, `TECHNICAL_DOCUMENTATION.md`, `STYLE_GUIDE.md`, `REQUIREMENTS_TRACEABILITY.md`
- **`docs/project/`** — `GAPS_AND_ROADMAP.md`, `REGULATORY.md`, `POSTER_TEMPLATE.md`
- `testing_plan.md` moved next to `hil_test_plan.md` under `docs/testing/`

100 file references across 25 consumer files updated in one sweep.
Every markdown link re-verified by an automated resolver — zero
broken links remaining.

### Added

- **`docs/README.md`** — single documentation index. Every file in
  the tree is grouped by purpose (guides / ops / design / budgets /
  reference / adr / hardware / testing / reliability / quality /
  security / characterization / verification / requirements /
  operations / project / sbom / tutorials / diagrams / superpowers).
  "Quick paths" table up top answers the most common "where do I
  find …?" questions.
- **README.md "Documentation" section** rewritten from a 30-line
  reference into a structured catalogue covering every directory,
  every ADR by name, and every per-profile ops guide. Points at
  `docs/README.md` as the single entry for the full index.

### Fixed — BOM component masses

`cansat_advanced.csv` had two visibly-wrong numbers:

- **LiPo 2S 1500 mAh**: 45 g → **80 g** (a real dual-cell 1500 mAh
  pouch pack is 75–80 g; 45 g was approximately the mass of a
  single-cell pack).
- **HS-35HD servo**: 9 g → **4 g** (Hitec datasheet lists 4.4 g; the
  part description already said "4.3 g").

BOM total corrected 246 → 277 g. `hardware/bom/by_form_factor/README.md`
updated: bare-kit mass ≈ 280 g, payload headroom ≈ 220 g under the
500 g regulation limit.

### Verified — per-profile testing checklists

All 12 `docs/ops/*.md` "Testing checklist (bench)" sections audited.
Each item classified:

- `[x]` = backed by passing tests / CI / SITL in the current release
- `[ ]` = requires bench hardware, RF range test, or flight-day
  field activity (team must sign off manually)

17 items flipped from `[ ]` to `[x]` across 8 profiles, grounded in
the current 435-test Python pass + 28 ctest C pass + 12
`KeyRotationPolicy` regression tests. Remaining `[ ]` items are
genuinely physical (drop tests, RF range at ≥ 2 km, GNSS cold-start
outdoors, battery SoC, parachute fold, SD-card preparation, camera
video capture) — these cannot be signed off from the repository
alone. A legend at the top of every checklist explains the
distinction.

### Test pass

Same 435 Python tests still green. Markdown-link resolver: 0 broken
links across the whole tree. `ruff` clean, `mypy --strict` clean.

## [1.4.0] - 2026-04-19 — Reliability hardening + per-profile ops + key rotation

Cherry-picks the seven genuinely new changes from the
`root3315/code-review-fixes` branch. The branch also contained a
parallel re-implementation of v1.3.0 universal-platform; that half
was skipped since master already has it. Net effect: real bug
fix + three new firmware/ground-station capabilities + richer
per-profile docs, with zero rework of existing subsystems.

### Fixed

- **`flight-software/core/event_bus.py`** — `EventBus.subscribe`
  blindly appended handlers; a caller that subscribed the same
  handler twice would see each publish fire the handler twice, and
  one unsubscribe only removed the first entry — leaking a live
  duplicate that silently kept reacting. Now dedupes on registration
  and logs repeated subscribes at debug level. Regression test
  `test_subscribe_is_idempotent` in `test_event_bus.py` drives the
  three-subscribe / one-unsubscribe sequence.

### Added — Firmware reliability

- **Reboot-loop guard** (`firmware/stm32/Core/Src/main.c`,
  `fdir_persistent.c`). If the `.noinit` `reboot_count` shows more
  than `FDIR_REBOOT_LOOP_THRESHOLD` (5) consecutive warm resets, boot
  engages a reboot-suppression flag in the mode manager: FDIR
  recommendations of `RECOVERY_REBOOT` are diverted to `SAFE` mode
  instead. Ground has to clear the flag (and typically the .noinit
  ring via a diag command) once the faulty subsystem is isolated —
  otherwise a board-level intermittent takes the vehicle down in a
  tight reset loop with no chance for operator intervention.
- **Grayscale FDIR** (`firmware/stm32/Core/Src/fdir.c`). Sensor
  degradation used to be binary — either nominal or faulted. Now
  `fdir_report_grayscale(fault_id, severity_0_to_255)` accumulates
  a per-sensor health score; DEGRADED mode kicks in at score ≥ 128
  while the sensor is still usable, full REBOOT only at ≥ 224. Lets
  the vehicle keep flying with partially-working instruments instead
  of hard-failing at the first glitch.

### Added — Ground station

- **HMAC key-rotation policy** (`ground-station/utils/key_rotation.py`).
  Firmware already supported A/B key rotation via `key_store`; this
  module adds the operator-facing *policy*: when to actually press
  the button. Knobs: `WARN_THRESHOLD_PCT` (50 %, orange chip in UI),
  `ROTATE_THRESHOLD_PCT` (80 %, hard-refuses further signatures),
  `MAX_LIFETIME_DAYS` (365, calendar-based ceiling). 12 pytest cases
  cover threshold math, calendar rollover, and rotate-while-signing
  interleave.

### Added — Documentation

- **Per-profile ops guides** (`docs/ops/` — 11 files + a README):
  `cansat_minimal.md`, `cansat_standard.md`, `cansat_advanced.md`,
  `cubesat_1u.md` through `cubesat_12u.md`, `rocket_avionics.md`,
  `hab_payload.md`, `drone.md`. Each covers setup → build → flight
  → post-flight for that specific form factor. More granular than
  the previous single-file `docs/guides/OPERATIONS_GUIDE.md` (kept alongside
  as a platform-agnostic overview).
- **Radiation budget** (`docs/hardware/radiation_budget.md`) —
  design-level TID / SEE budget for STM32F446RE + sensor stack +
  CC1125 / RFM radios, per orbital class (LEO equatorial → SSO 600
  km → HEO). Input spec for board-level accelerated testing, not a
  substitute for it.

### Added — Hardware

- **`cubesat_1_5u.csv` + `cubesat_2u.csv` reference BOMs** fill the
  two remaining gaps in `hardware/bom/by_form_factor/`. Every
  CubeSat size registered in `form_factors.py` now has a BOM. README
  updated with bare-kit mass and payload headroom for both.

### Changed

- **`README.md`** "Supported Form Factors" section merged: every row
  now has both the reference BOM and the per-profile ops guide link.
  Competition Adaptation table gains an "Ops guide" column pointing
  into `docs/ops/*.md`.
- **`configurator/tests/test_validators.py`** — two new mission-
  template cross-consistency tests catch orphan `form_factor` keys
  that would silently fall back to the 3U default.
- **Drone / HAB mission templates** (`mission_templates/`) point at
  the canonical `form_factor` keys (`drone_small` / `hab_payload`)
  instead of historical aliases.

### Test pass

- 435 Python tests green: 263 flight-software + 94 ground-station
  + 57 simulation + 21 configurator (was 420 before this release).
- `ruff` clean across all four Python packages.
- `mypy --strict` clean on all 23 `flight-software` source files.
- Firmware host ctest + ARM cross-compile footprint unchanged from
  1.3.0 (31.6 KB flash / 36.3 KB RAM).

### Skipped (intentionally)

- The 10 parallel-implementation commits on `root3315/code-review-fixes`
  that re-did v1.3.0 universal-platform work already on master were
  left behind. Merging them would have wiped `CLAUDE.md`,
  `docs/design/universal_platform.md`, `docs/guides/OPERATIONS_GUIDE.md`, the five
  configurator templates added in 1.3.1, and the v1.3.1/v1.3.2
  CHANGELOG entries.

## [1.3.2] - 2026-04-18 — Full audit: docs sync + lint clean

Full repository audit after the 1.3.1 polish. Zero behavioural changes;
this release fixes stale numbers in every documentation file,
brings the whole Python tree to `ruff` / `mypy --strict` clean, and
cross-links form-factor-specific budgets to the 3U reference docs.

### Fixed — stale documentation

- **README.md** — test-count badges and project-status table brought
  in line with the real 420 Python / 28 ctest numbers (were 329 / 27).
  Banner subtitle changed from "Universal Modular CubeSat Platform"
  to "Universal Modular Satellite Platform" since the scope is no
  longer CubeSat-only. Project tree gained accurate test counts per
  package and references to `utils/profile_gate.py` and the
  `by_form_factor/` BOM directory.
- **docs/project/GAPS_AND_ROADMAP.md** — verification table reflects 28/28
  ctest and 420 pytest (was 27 / 329).
- **docs/guides/USAGE_GUIDE.md** — "ctest 16/16 → pytest 34/34" updated to
  "28/28 → 420/420" with per-package breakdown.
- **docs/quality/static_analysis.md** — soft-pass numbers updated.
- **docs/reference/TECHNICAL_DOCUMENTATION.md** — version bumped from 1.2.0 to
  1.3.1, with a two-line "What's new since 1.2" block.
- **COMPETITION_GUIDE.md** — CanSat section completely rewritten.
  Previous guidance ("set form_factor to 1U or custom, add parachute
  module") predated the first-class CanSat profiles and was actively
  misleading. Now shows the three built-in variants, the three-line
  setup, and an explicit competition-scoring table.
- **CLAUDE.md** — "parallel-truth debt" warning rewritten into a
  "single source of truth" note (the debt was closed in 1.3.1).
- **docs/budgets/mass_budget.md** and **docs/budgets/power_budget.md** now call out
  their 3U scope and point at `core.form_factors` for other profiles.

### Fixed — code quality

- **`flight-software/modules/__init__.py`** — removed unused `asyncio`
  import.
- **`flight-software/modules/health_monitor.py`** — type-ignore
  comment on `ctypes.windll.kernel32` widened to include
  `unused-ignore` so mypy is happy whether the attribute is present
  (Windows) or not (Linux/Mac).
- **19 automatic `ruff --fix`** cleanups across `core/`, `modules/`,
  `ground-station/`, `simulation/` (unused imports, unused local
  variables).
- **`ground-station/tests/test_ax25.py`** — two two-statement-on-one-
  line cases split.
- **`noqa: E402` hints** added to the three legitimate sys.path + late
  import sites (`configurator/validators/*`, `configurator_app.py`,
  `ground-station/utils/ax25.py`). Ruff is now clean across every
  package.

### Verified

- `ruff check` clean across `flight-software/core`, `flight-software/modules`,
  `ground-station`, `simulation`, `configurator`.
- `mypy --strict` clean across the 23 `flight-software` source files.
- All 420 Python tests still green across all 4 packages.

## [1.3.1] - 2026-04-18 — Universal-platform polish

Post-merge follow-up that closes the parallel-truth gap between the
form-factor registry and the Streamlit configurator, fixes a flaky
soak test, and ships a full end-to-end operations guide.

### Changed

- **Configurator validators now read from `core.form_factors`.** Both
  `configurator/validators/mass_validator.py` and `volume_validator.py`
  stop carrying their own hardcoded dicts and instead source mass /
  volume envelopes from the registry. Every profile registered in
  `form_factors.py` is automatically recognised by the validator, and
  legacy keys (`"1U"`, `"3U"`, `"cansat_custom"` …) keep working via
  an explicit alias table.
- **`configurator_app.py`** form-factor dropdown updated to expose the
  full set: `cubesat_1u` through `cubesat_12u` (adds 1.5U), all three
  CanSat variants, plus `rover_small`. Legacy `1U` / `cansat_custom`
  labels retired from the UI but still accepted if you paste an older
  config.
- **CanSat-scale component masses.** The mass validator previously
  defaulted to CubeSat-sized components (150 g OBC stack, 500 g battery)
  which produced 1.4 kg totals for a 500 g CanSat. A second
  `CANSAT_COMPONENT_MASSES` table now supplies realistic hobby-part
  weights (5–15 g range) so CanSat profiles validate against the actual
  competition envelope. Reference BOMs already reflected these — now
  the validator matches.
- **`hardware/bom/by_form_factor/README.md`** adds a "payload headroom"
  column so teams stop confusing kit mass with the regulation limit.
  For `cansat_standard`: 170 g kit + 330 g headroom = 500 g cutoff.

### Added

- **`docs/guides/OPERATIONS_GUIDE.md`** — 12-section start-to-finish playbook
  covering profile selection, tooling setup, simulation, firmware
  build per profile, BOM fill, ground-station bring-up, HIL bench
  tests, pre-launch checklist, flight-day roles, post-flight analysis,
  and competition submission.
- **Five new configurator templates**: `cansat_minimal_default.json`,
  `cansat_standard_default.json`, `cansat_advanced_default.json`,
  `1_5u_default.json`, `12u_default.json`. Closes the template gap
  so every registered form factor has a starter config.
- **Six new validator tests** covering CanSat envelopes, scale-aware
  component masses, legacy-alias back-compat, cylindrical-volume
  handling, and a sweep that every registered form factor validates
  without raising.

### Fixed

- **Flaky `test_long_soak.py::test_mission_soak`.** Windows + Python
  3.14 occasionally saw the "first" cycle complete in < 0.1 ms, which
  made the `mean ≤ 1.5 × first` drift check trip on the full suite.
  Replaced the first-cycle anchor with a median-of-first-5 baseline
  and loosened the factor to 3× — still catches genuine degradation
  (memory leak, unbounded list growth), stops flaking on scheduler
  jitter.
- **Root `mission_config.json` mass/form-factor mismatch** — example
  declared `cansat_standard` but carried `mass_kg: 1.272` (2.5× over
  the 500 g limit). Restored to 0.45 kg with explicit dimensions.

## [1.3.0] - 2026-04-18 — Universal Platform (branch `feature/universal-platform`)

Expands the platform coverage from "3U CubeSat LEO + a handful of
templates" to a single codebase that configures itself for every
supported vehicle class — CanSat (minimal/standard/advanced), CubeSat
1U-12U, sounding rocket, HAB, drone, and rover.

### Added — Form-factor registry (`flight-software/core/form_factors.py`)

- Authoritative mass / volume / power envelopes for 14 form factors
  aligned with CDS Rev. 14 (CubeSats) and ESA CanSat regulations.
- Helpers `check_mass()`, `is_adcs_tier_supported()`,
  `is_comm_band_supported()` used by the configurator and runtime
  guards.
- Per-class allowed ADCS tiers and radio bands so invalid
  configurations fail fast instead of silently misbehaving in flight.

### Added — Feature-flag resolver (`flight-software/core/feature_flags.py`)

- Declarative registry of 17 optional features with platform /
  form-factor / ADCS / radio-band gates.
- Deterministic resolution pipeline: explicit override → platform →
  form factor → ADCS tier → radio band → default.
- `ResolvedFlags.as_dict()` exposes the full decision trail for UI
  rendering and CI logs.

### Added — New mission profiles (`flight-software/core/mission_types.py`)

- CubeSat 1U, 1.5U, 2U, 3U, 6U, 12U profiles reusing the LEO phase
  graph with size-appropriate telemetry rates and module lists.
- CanSat minimal (≤350 g) and CanSat advanced (≤500 g guided descent)
  variants alongside the existing CanSat standard.

### Added — Mission templates (`mission_templates/`)

- Eight new ready-to-copy JSON templates: `cansat_minimal`,
  `cansat_advanced`, `cubesat_1u`, `cubesat_1_5u`, `cubesat_2u`,
  `cubesat_3u`, `cubesat_6u`, `cubesat_12u`.
- Each carries explicit `features` block and form-factor key for
  deterministic downstream resolution.

### Added — Reference BOMs (`hardware/bom/by_form_factor/`)

- Seven per-class BOMs sized to stay inside the regulatory mass limit
  of each form factor, each with part number, price, mass, and
  supplier.

### Added — Compile-time firmware profile selector

- `firmware/stm32/Core/Inc/mission_profile.h` — single header that
  turns `-DMISSION_PROFILE_<NAME>=1` into `PROFILE_FEATURE_*` and
  `PROFILE_TELEMETRY_HZ` macros mirroring the Python resolver.
- Nine new Makefile targets (`target-cansat-minimal` …
  `target-cubesat-12u`) producing isolated `build-arm-<profile>/`
  trees; `target-all-profiles` builds every image in one shot.

### Added — Ground-station page gating

- `ground-station/utils/profile_gate.py` — declarative `page_applies()`
  helper that reads `mission_config.json` and hides pages irrelevant
  to the active mission.
- `03_orbit_tracker`, `04_image_viewer`, `05_adcs_monitor` now
  auto-hide with a short notice when the mission does not need them.

### Added — Tests (56 new tests, all passing)

- `test_form_factors.py` — envelope checks against the reference
  regulations.
- `test_feature_flags.py` — resolver pipeline, explicit-override
  precedence, unknown-flag warnings.
- `test_new_profiles.py` — every CubeSat size and CanSat variant,
  including round-trip of the JSON template through
  `build_profile_from_config()`.
- `test_profile_gate.py` — ground-station page visibility for CanSat
  vs CubeSat 3U configurations.

### Added — Documentation

- `docs/design/universal_platform.md` — architectural reference for the three
  registries and end-to-end flow.
- README "Supported Form Factors" rewritten with the full 9-profile
  matrix, BOM links, and quickstart commands.
- README "Competition Adaptation" table expanded to cover all three
  CanSat classes and the 6U/12U research use cases.

## [1.2.0] - 2026-04-18 — TRL-5 hardening (branch `feat/trl5-hardening`)

Eight-phase hardening sweep covering security, reliability,
build infrastructure, quality gates, and documentation. Ships a
verified ARM target build, doubled test count, full FDIR stack,
persistent key store, and a relicense to Apache-2.0 for the
patent-grant clause.

### Added — Phase 1: STM32 target build

- `firmware/stm32/Target/STM32F446RETx_FLASH.ld` — linker script
  (512 KB FLASH + 128 KB RAM layout, stack + heap guard regions).
- `firmware/stm32/Target/startup_stm32f446retx.s` — Cortex-M4
  vector table + full IRQ handler stubs + `Reset_Handler`.
- `firmware/stm32/Target/system_stm32f4xx.c` — SystemInit + PLL
  config driving the core to 168 MHz from an 8 MHz HSE.
- `firmware/stm32/Target/system_init.c` — `SystemClock_Config()`
  + weak `MX_*_Init` placeholders for peripheral bring-up.
- `firmware/stm32/Target/stm32f4xx_it.c` — IT handlers (SysTick,
  HardFault with register dump, NMI, PendSV, SVC).
- `firmware/stm32/Target/hal_shim.c` — weak HAL_* stubs so the
  firmware links out of the box without the STMicro HAL tree
  being fetched yet.
- `firmware/stm32/Target/stm32f4xx_hal_conf.h` — project HAL
  configuration (168 MHz, enabled modules, no assert).
- `firmware/stm32/Target/FreeRTOSConfig.h` — kernel configuration
  for CMSIS-RTOSv2 (max 56 priorities, heap_4, generic task
  selector for wrapper compat).
- `firmware/stm32/Target/stm32_assert.h` — no-op for LL drivers.
- `firmware/stm32/Target/peripherals.c` — huart1/2, hi2c1, hspi1,
  hadc1, htim2, hiwdg handle definitions.
- `scripts/setup_stm32_hal.sh` — one-command fetch of STM32CubeF4
  HAL + CMSIS + CMSIS-RTOSv2 wrapper.
- `scripts/setup_freertos.sh` — one-command fetch of FreeRTOS
  V10.6.1 kernel + Cortex-M4F port.
- `scripts/flash_stm32.sh` — `st-flash` wrapper with 90 %
  flash/RAM budget gate.
- `Makefile` targets: `make target / size / flash / setup-hal /
  setup-freertos / setup-all`.

**Verified:** ARM build produces `firmware/build-arm/unisat_firmware.elf`
= 31.6 KB flash (6 % of 512 KB) + 36.3 KB RAM (28 % of 128 KB).

### Added — Phase 2: Security (T2 replay + persistent key store)

- 32-bit monotonic counter prefix + 64-bit sliding-window bitmap
  in `command_dispatcher.c`; counter = 0 reserved as sentinel.
  Closes **Threat T2 (replay)** from
  `docs/security/ax25_threat_model.md`.
- `firmware/stm32/Core/Src/key_store.c` — A/B flash slots with
  CRC-32 + magic-byte validation + strictly monotonic generation.
  Torn-write safe during rotation.
- `ground-station/utils/hmac_auth.py` — `CounterSender` class
  (thread-safe, monotonic, overflow-guard) + `build_auth_frame`
  / `parse_auth_frame` / `verify_auth_frame`.
- Integration in `main.c`: `key_store_init()` →
  `CommandDispatcher_SetKey()` boot wiring (fail-closed when
  neither slot carries a valid record).
- Tests: `test_command_dispatcher.c` (11 sub-tests),
  `test_key_store.c` (10), `test_boot_security.c` (4),
  `test_hmac_auth.py` (22).

### Added — Phase 3: FDIR (Fault Detection, Isolation, Recovery)

- `firmware/stm32/Core/Src/fdir.c` — 12-fault advisor with
  60-second escalation window and 6-level severity ladder
  (LOG_ONLY → RETRY → RESET_BUS → DISABLE_SUBSYS → SAFE_MODE
  → REBOOT).
- `firmware/stm32/Core/Src/mode_manager.c` — commander layer
  that polls FDIR at 1 Hz and enacts actual transitions
  (ADR-005 split).
- `firmware/stm32/Core/Src/fdir_persistent.c` — warm-reboot-
  survivable fault ring in `.noinit` SRAM + CRC-32 validation
  (ADR-006).
- `firmware/stm32/Core/Src/watchdog.c` integrated with
  `FDIR_Report` on task-feed miss.
- Tests: `test_fdir.c` (9), `test_mode_manager.c` (9),
  `test_fdir_persistent.c` (6).

### Added — Phase 4: Tboard driver + E2E + soak

- `firmware/stm32/Drivers/BoardTemp/board_temp.c` — TMP117
  facade wiring beacon bytes 14-15 to live temperature reading
  (previously hardcoded zeros).
- `flight-software/tests/test_mission_e2e.py` — full mission
  lifecycle test (init → nominal → imaging → safe mode →
  recovery).
- `flight-software/tests/test_long_soak.py` — 48-hour soak
  harness gated via `UNISAT_SOAK_SECONDS` environment variable;
  default smoke run is 30-cycle, ~1 second.
- Tests: `test_board_temp.c` (6), e2e (3), soak (1).

### Added — Phase 5: Quality gates

- `cmake -DCOVERAGE=ON` → lcov HTML reports under
  `firmware/build/coverage_html/`.
- `cmake -DSANITIZERS=ON` → ASAN + UBSAN linked into ctest.
- `cmake -DSTRICT=ON` → `-Werror -Wshadow -Wconversion` on host
  builds (all 27 tests green under STRICT).
- `scripts/run_cppcheck.sh` + `.cppcheck-suppressions` →
  two-mode static analyzer (CI-blocking gate + MISRA advisory).
- Makefile: `make cppcheck / cppcheck-strict / coverage /
  sanitizers`.

### Added — Phase 6: Documentation

- `docs/requirements/SRS.md` — Software Requirements Spec, 44
  REQ each with priority + verification method + source file +
  test file.
- `docs/requirements/traceability.csv` — machine-readable
  REQ → source → test matrix.
- `docs/characterization/` — WCET / stack / heap / power
  measurement templates (data is TBD until HIL bench runs).
- `docs/testing/hil_test_plan.md` — HIL bench BOM ($155) + 10
  test IDs mapped to specific REQ IDs.
- `docs/reliability/fdir.md` — FDIR policy + fault table.
- `docs/quality/static_analysis.md` — quality-gate policy.
- ADRs 3-8 under `docs/adr/` (A/B keystore, counter=0 sentinel,
  FDIR split, .noinit log, HAL shim, dispatcher wire format).

### Added — Phase 7: Python & release plumbing

- `scripts/gen_sbom.sh` → SPDX bill-of-materials under
  `docs/sbom/sbom-summary.md`.
- `pytest-cov` gate in `flight-software/pyproject.toml` with
  `fail_under = 80` (currently at 85.15 %).
- `mypy --strict` clean across 21 source files after six
  targeted type-annotation fixes.
- `scripts/pin_docker.sh` + `make pin-docker / pin-docker-unpin`
  — release-engineering toggle for Docker base-image pinning.

### Added — Phase 8: Final polish + ARM verification

- ARM target build actually verified (previously just linked):
  6.04 % flash + 27.69 % RAM on STM32F446RE, both under the
  90 % budget gate.
- `__attribute__((unused))` annotations on every SIM-only
  helper function across BME280, MPU9250, TMP117, UBLOX,
  SunSensor drivers → zero `-Wunused-*` warnings on host and
  target builds.
- `uhf_tx_buffer` in `comm.c` likewise annotated for host.
- 87 new Python tests covering gnss_receiver, health_monitor,
  scheduler, orbit_predictor, image_processor, camera_handler,
  communication, data_logger, module_registry (+ coverage from
  51 % → 85.15 %).
- LICENSE migrated MIT → Apache-2.0; `NOTICE` added with
  third-party attribution.

### Security model (summary)

- T1 (command injection) — mitigated by HMAC-SHA256 with
  constant-time verify (closed since 1.1.0).
- T2 (replay) — **closed** by 32-bit counter + 64-bit sliding
  window, counter=0 sentinel.
- Key management — A/B flash rotation with monotonic
  generation (downgrade replay rejected).

### Test totals

- C ctest: 16 → **27** test executables (+ 100+ sub-tests).
- Python pytest: 34 → **329** tests (hypothesis + fuzz + e2e +
  soak + Streamlit smoke + mocked-serial).
- C line coverage: not measured → **85.3 %**.
- Python line coverage: not measured → **85.15 %**.

### Changed

- LICENSE: MIT (2026-02-15 — 2026-04-18) → **Apache-2.0**
  (2026-04-18 onward). See `NOTICE` for third-party attribution.
- TECHNICAL_DOCUMENTATION.md bumped to v1.2.0 with new §0
  Phase 1–8 summary.
- `docs/superpowers/` legacy plans + specs marked archival
  with banners pointing to the SRS and ADRs.

### Infrastructure

- 75 atomic commits on `feat/trl5-hardening` with detailed
  commit messages (≥ 100 lines each).
- 9 quality gates all green simultaneously: ctest + pytest +
  cppcheck + coverage (C+Py) + STRICT + ASAN + UBSAN + mypy +
  ARM build.
- Supply-chain: pinned STM32CubeF4 v1.27.1 + FreeRTOS V10.6.1;
  Docker digest-pin automation via `make pin-docker`.

## [1.1.0] - 2026-04-17

### Added — AX.25 Link Layer (Track 1)

- Pure C11 AX.25 v2.2 library at `firmware/stm32/Drivers/AX25/` —
  FCS (CRC-16/X.25 with RFC oracle `"123456789" → 0x906E`),
  bit-level stuffing across byte boundaries, address encode/decode
  per §3.12, UI-frame encode + pure decoder, first-class streaming
  decoder (`ax25_decoder_t`) with HUNT/FRAME state machine.
- Python mirror at `ground-station/utils/ax25.py` — same algorithm,
  same exception hierarchy, shared test fixtures.
- 28 golden test vectors (`tests/golden/ax25_vectors.json` + `.inc`)
  consumed by both C and Python runners — bit-identical results
  required (REQ-AX25-015).
- Project-style facade `ax25_api.h` (ADR-002) so firmware callers
  use `AX25_Xxx()` naming while the core library stays reusable.
- SITL TCP virtual UART (`firmware/stm32/Drivers/VirtualUART/`)
  replacing HAL UART under `SIMULATION_MODE`; one end-to-end demo
  binary `scripts/sitl_fw.c`.
- Ground-station CLIs (`ground-station/cli/ax25_listen.py`,
  `ax25_send.py`) — TCP listener/sender that speak the same AX.25
  wire format as the firmware.
- `scripts/demo.py` + `Makefile` targets — `make demo` runs the
  full C-encoder → TCP → Python-decoder path, asserts 2 beacons.
- Comprehensive docs: design spec (775 lines), implementation plan
  (4022 lines), ADR-001 (no CSP), ADR-002 (style adapter), threat
  model, byte-by-byte walkthrough tutorial, auto-generated
  verification trace matrix.
- `scripts/verify.sh` + `./scripts/verify.sh` — single-command
  reproducibility inside a pre-built Docker image.
  (GitHub Actions workflows removed for now — the repo account is
  locked on billing, see [removal note](#removed).)

### Removed

- `.github/workflows/` directory dropped to avoid red-X indicators
  from billing-blocked runs. Reviewers should use
  `./scripts/verify.sh` which runs the same pipeline locally.

### Added — Track 1b (command authentication — now wired end-to-end)

- HMAC-SHA256 library at `firmware/stm32/Drivers/Crypto/` — portable
  C11, zero platform dependencies, suitable for flight-software
  task context. RFC 4231 test vectors (§4.2, §4.3) asserted.
- Constant-time tag comparison (`hmac_sha256_verify`).
- Python mirror at `ground-station/utils/hmac_auth.py` (stdlib
  `hmac` + `hashlib`), same RFC vectors asserted to guarantee
  cross-implementation agreement.
- Beacon TX path now properly layered:
  48 B raw (`Telemetry_PackBeacon`) → CCSDS Space Packet
  (`CCSDS_BuildPacket` + `CCSDS_Serialize`) → AX.25 UI frame
  (`COMM_SendAX25`).
- **Command dispatcher with HMAC verification**
  (`firmware/stm32/Core/Src/command_dispatcher.c`). Provides the
  strong `CCSDS_Dispatcher_Submit` that overrides the weak no-op
  in `comm.c`. Splits incoming frames into CCSDS body + 32-byte
  tag, verifies the tag in constant time, drops unauthenticated
  frames silently, forwards authenticated frames to a registered
  handler. Counters (`accepted`, `rejected_bad_tag`,
  `rejected_too_short`) exposed for telemetry. Unit tests cover
  valid / tampered / truncated / no-key cases.
- **Threat T1 (command injection) — MITIGATED.** Threat model
  updated accordingly (`docs/security/ax25_threat_model.md`).

### Fixed

- `gnss.c`, `payload.c`, `sensors.c`, `obc.c` updated to the
  handle-based driver APIs (previously invoked legacy handle-less
  calls that broke the host build). Full `unisat_core` library
  now compiles cleanly on host.
- `CMakeLists.txt`: removed `EXCLUDE_FROM_ALL` workaround —
  `unisat_core` is a first-class build target so any future
  regression in any subsystem fails CI before a test target
  touches it.
- Orphan tests (`test_ccsds`, `test_adcs_algorithms`, `test_eps`,
  `test_telemetry`) wired into `ctest`. All green.
- `Telemetry_PackBeacon` now emits the 48-byte raw beacon layout
  per `communication_protocol.md` §7.2; the legacy CCSDS-wrapped
  variant preserved as `Telemetry_PackBeaconCcsds`.

### Infrastructure

- `docker/Dockerfile.ci` — locally-built image with `cmake` +
  `pytest` + `hypothesis` pre-installed. Cuts each verification
  run from ~60 s to ~5 s.
- `docs/verification/driver_audit.md` — full audit of the 8
  sensor drivers (MPU9250, LIS3MDL, BME280, TMP117, MCP3008,
  UBLOX, SBM20, SunSensor): every one confirmed a real
  vendor-datasheet-compliant protocol (no stubs).

### Test counts

- C (`ctest`): 15 targets, all pass (up from 4 broken-wired).
- Python (`pytest`): 34 tests, all pass (incl. 200 hypothesis
  property-based + 500 fuzz + RFC 4231 HMAC).

## [1.0.0] - 2026-02-18

### Added

#### Firmware (STM32F4 + FreeRTOS)
- OBC main controller with 6 FreeRTOS tasks
- CCSDS-based telemetry packet formatting
- ADCS algorithms: B-dot detumbling, sun pointing, nadir/target pointing
- Full quaternion math library (multiply, inverse, normalize, Euler/DCM conversion)
- EPS subsystem: MPPT (Perturb & Observe), battery manager, power distribution
- HAL drivers for 8 sensors: LIS3MDL, BME280, TMP117, MPU9250, SBM20, u-blox, MCP3008, Sun Sensor
- Watchdog with per-task monitoring and 10-second timeout
- Error handler with EEPROM logging and safe mode transition
- Communication module for UHF (AX.25) and S-band

#### Flight Software (Python + asyncio)
- Asynchronous flight controller with state machine
- Dynamic module loading from mission_config.json
- Camera handler with scheduled and on-demand capture
- SVD image compression with configurable rank
- Telemetry manager with CCSDS packing
- SQLite data logger with 1GB rotation
- SGP4-based orbit predictor
- Orbit-based task scheduler
- Health monitor (CPU, RAM, temperature, storage)
- Safe mode with automatic activation on 24h communication loss
- Power manager with priority-based load shedding
- Abstract payload interface for plugin modules

#### Ground Station (Streamlit + Plotly)
- Mission dashboard with subsystem health indicators
- Real-time telemetry charts (temperature, pressure, voltage, radiation)
- 3D orbit visualization on interactive globe
- Image gallery with geolocation overlay
- 3D satellite attitude visualization
- Power generation/consumption monitoring
- HMAC-SHA256 authenticated command center
- Communication pass prediction and imaging planner
- Data export (CSV, JSON, CCSDS)
- Automated health report with anomaly detection

#### Simulation
- Keplerian orbit propagator with J2 perturbation
- Power budget simulator (eclipse/sunlight cycles)
- Six-face thermal model (solar, albedo, Earth IR, cosmic background)
- Link budget calculator (SNR, BER, range)
- Comprehensive mission analyzer

#### Configurator
- Web-based mission configurator (Streamlit)
- Form factor templates: 1U, 2U, 3U, 6U
- Mass, power, and volume validators
- mission_config.json generator
- PDF mission report generator
- Bill of Materials (BOM) generator

#### Payloads
- Abstract payload interface
- Radiation monitor (SBM-20 Geiger counter)
- Earth observation camera
- IoT relay module
- Magnetometer survey
- Spectrometer module

#### Documentation
- CDR-level system architecture
- CCSDS communication protocol specification
- Power budget analysis (Nominal / Peak / Safe Mode)
- Mass budget with 20% margin
- UHF and S-band link budget
- Thermal analysis (hot/cold case)
- Orbit analysis (ground track, eclipse, revisit time)
- Test plan with pass/fail matrix
- Assembly guide
- Competition adaptation guide (CanSat, CubeSat, NASA Space Apps, Olympiad, Hackathon)

#### Infrastructure
- GitHub Actions CI/CD (Python tests, firmware build, linting)
- Documentation auto-generation workflow
- Setup, test, build, flash, and simulation scripts
