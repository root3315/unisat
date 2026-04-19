# Style Guide

UniSat follows Google's public style guides, lightly adapted for
aerospace firmware:

- **C code:** [Google C++ Style Guide][gcpp] (we are C11, but the
  naming, commenting, and layout rules port cleanly).
- **Python code:** [Google Python Style Guide][gpy].
- **Prose:** [Google developer documentation style guide][gdoc].
- **Shell scripts:** [Google Shell Style Guide][gsh].

[gcpp]: https://google.github.io/styleguide/cppguide.html
[gpy]: https://google.github.io/styleguide/pyguide.html
[gdoc]: https://developers.google.com/style
[gsh]: https://google.github.io/styleguide/shellguide.html

This document records the **project-specific** deviations and
conventions. If a point is not covered here, assume the linked
Google guide wins.

---

## Code conventions

### C (firmware)

| Aspect | Rule | Rationale |
|---|---|---|
| Indentation | 4 spaces, never tabs | Google C++ — adapted for C |
| Line length | 80 columns | Diff-friendly, side-by-side review |
| Naming (functions) | `module_snake_case(...)` | Consistent across AX.25, Crypto, etc. |
| Naming (types) | `module_name_t` | Same |
| Naming (public macros) | `MODULE_UPPER_SNAKE` | e.g. `AX25_MAX_FRAME_BYTES` |
| Static vs extern | Every non-API function is `static` | Keep link graph tight |
| Header guards | `#ifndef FILE_H / #define / #endif` | Standard, never `#pragma once` |
| Includes | System `<>`, then project `""` | Alphabetical within each group |
| Doxygen | `@file`, `@brief` at top of every `.c`/`.h` | Discoverable via grep |
| Error handling | Return status enum, never `errno` | Deterministic on embedded |

**Project-specific:** `SIMULATION_MODE` `#ifdef`s guard every
hardware-touching code path so host tests compile without a HAL.

Lint gate: `cmake -DSTRICT=ON` enables `-Werror -Wshadow
-Wconversion`. Every merge to `master` must pass it.

### Python (ground station, flight software, tooling)

| Aspect | Rule |
|---|---|
| Formatter | `black` (line length 79 — matches PEP 8) |
| Imports | `isort`, sectioned: stdlib → third-party → local |
| Docstrings | Google-style (`Args:`, `Returns:`, `Raises:`) |
| Type hints | Everywhere a public function is declared; `mypy --strict` clean |
| Naming | `snake_case` for funcs/vars, `CamelCase` for classes |
| Exceptions | Custom hierarchy rooted at `AX25Error`, never bare `Exception` |

Lint gates: `mypy --strict`, `pytest --cov --cov-fail-under=80`.

### Shell

| Aspect | Rule |
|---|---|
| Shebang | `#!/usr/bin/env bash` |
| Safety pragma | `set -euo pipefail` in every script |
| Quoting | `"${var}"` for scalars, `"${arr[@]}"` for arrays |
| Portability | Plain POSIX unless otherwise noted |

Lint gate: `shellcheck` clean (advisory in CI).

---

## Documentation conventions

The **Google developer documentation style guide** is the source
of truth. The project-specific reinforcements below are the ones
that matter most for aerospace reviewers:

### Voice and mood

- **Active voice, not passive.**
  ✅ *The decoder rejects frames longer than 400 bytes.*
  ❌ *Frames longer than 400 bytes are rejected by the decoder.*

- **Imperative mood for instructions.**
  ✅ *Run `./scripts/verify.sh`.*
  ❌ *You should run `./scripts/verify.sh`.*

- **Present tense, not future.**
  ✅ *The dispatcher drops replayed frames silently.*
  ❌ *The dispatcher will drop replayed frames silently.*

### Structure

Every task-oriented doc uses this skeleton:

```
# Title — what this helps you do

Before you begin
----------------
Prerequisites, mental model, assumptions.

Steps
-----
1. First action (imperative mood, one verb).
2. Next action.
3. …

Verify
------
How to tell it worked.

Troubleshooting
---------------
Common failure modes + fixes.

Next steps
----------
Pointer forward.
```

Reference docs (SRS, ADRs, spec files) use their own conventions
but still stay in active voice.

### Formatting

- **Code samples** go in fenced blocks with an explicit language
  hint (```` ```bash ````, ```` ```c ````, etc.) so syntax
  highlighting works on every renderer.
- **Commands** get a leading `$` only when the prompt itself is
  relevant to the lesson. Most of the time we omit it.
- **Paths** are always relative to the repository root
  (`ground-station/utils/ax25.py`, not `~/unisat/ground-station/…`).
- **Emphasis** uses bold for key terms, italics for variable
  placeholders (e.g. *callsign*-*ssid* becomes `UN8SAT-1`).
- **Cross-links** point at real files or anchors — broken links
  fail review.
- **Headings** use sentence case, not title case
  (*Supported form factors*, not *Supported Form Factors*).

### Terminology

Consistent terminology across all docs:

| Preferred | Deprecated | Reason |
|---|---|---|
| ground station | ground control / mission control | common in amateur-radio world |
| uplink / downlink | upload / download | matches ITU and CCSDS usage |
| frame | packet (when on-air) | AX.25 talks about frames |
| packet | frame (when in CCSDS context) | CCSDS talks about packets |
| flash / RAM | ROM / memory | precise on MCU |
| commission | activate / turn on | matches NASA ops vocabulary |

When in doubt, run `grep -n preferred_word docs/ -r` before
introducing a synonym.

### Acronyms

Expand on first use within each document, keep the short form
everywhere after:

> The Hash-based Message Authentication Code (HMAC) is computed
> over … HMAC tags are verified in constant time.

Common acronyms assumed known in embedded / aerospace context:
`MCU`, `CPU`, `RAM`, `HAL`, `I2C`, `SPI`, `UART`, `LEO`, `SSO`,
`UHF`, `RF`.

---

## Writing commit messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <imperative summary, 50 chars max>

<body wrapped at 72 chars, explaining *why*, not *what*>

<footers: Closes #N, Co-Authored-By, etc.>
```

Types we use regularly: `feat`, `fix`, `docs`, `test`, `build`,
`ci`, `perf`, `refactor`, `chore`.

Scopes we use: `ax25`, `comm`, `dispatcher`, `crypto`, `gs-ax25`,
`gs-cli`, `firmware`, `config`, `docs`, `build`, `ci`.

### Good example

```
feat(dispatcher): add 64-bit sliding-window replay filter

Closes threat T2 from docs/security/ax25_threat_model.md. Every
authenticated frame now carries a 32-bit monotonic counter; the
dispatcher maintains a 64-bit bitmap of recently-accepted counters
and rejects duplicates or out-of-window values silently.

Adds 11 sub-tests in test_command_dispatcher.c covering the full
acceptance table from the threat model.
```

### Bad example

```
updated dispatcher
```

---

## Pull-request conventions

- **One concern per PR.** Split mixed changes.
- **Title:** same format as a commit message summary.
- **Description:** what, why, how-to-test. Include the output of
  `./scripts/verify.sh` or the relevant subset.
- **Traceability:** reference the REQ-IDs from `docs/requirements/SRS.md`
  your change touches.
- **Reviewers:** tag at least one module owner. When unsure, tag
  the most recent committer of the files you changed
  (`git log -5 --format='%an' <file>`).

---

## Documentation roadmap for new modules

When adding a new module (`firmware/stm32/Drivers/NewDriver/` or
similar), the PR is not complete without:

1. Module header (`new_driver.h`) with doxygen `@file`, `@brief`,
   public API comments following the `AX25_`/`SBM20_` patterns.
2. Module source with module-level comment explaining lifecycle
   (init → use → shutdown).
3. At least one Unity test file registered in `firmware/CMakeLists.txt`.
4. Entry in `docs/reference/API_REFERENCE.md` pointing at the header.
5. Update to `docs/reference/REQUIREMENTS_TRACEABILITY.md` linking the REQ
   IDs this module satisfies.
6. If behaviour is user-visible: mention in `CHANGELOG.md` under
   the `Unreleased` or next version heading.

---

## Enforcement

- `cmake -DSTRICT=ON make` — C style + warnings.
- `make lint-py` — `mypy --strict` + `ruff`.
- `make cppcheck` — static analysis.
- `./scripts/verify.sh` — the aggregate gate; green = mergeable.

Cosmetic deviations that a formatter can fix (whitespace, import
order) are auto-corrected; structural violations (naming,
architectural decisions) block merge until resolved.

---

*Last synced to Google style guides: 2026-04-18.*
