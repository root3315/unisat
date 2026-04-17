# ADR-002: AX.25 Library Style Adapter

**Status:** Accepted — 2026-04-17
**Track:** 1 (AX.25 Link Layer)

## Context

The pure AX.25 library in `firmware/stm32/Drivers/AX25/` is written in
Google C++ Style (snake_case functions, `xxx_t` types). Existing firmware
code in `firmware/stm32/Core/Src/` uses the embedded-HAL convention
(`COMM_SendXxx()`, `COMM_Status_t`). A naive mix of both styles inside the
same translation unit hurts readability and signals "this code was glued
together" rather than designed.

## Decision

A thin facade header (`ax25_api.h`) exposes `static inline AX25_Xxx()`
wrappers and `AX25_Xxx_t` typedef aliases over the snake_case core
library. Integration callers include **only** `ax25_api.h`; the core
library stays project-neutral and portable.

```c
/* Core (ax25.h) — Google C++ style, reusable in any project. */
ax25_status_t ax25_encode_ui_frame(
    const ax25_address_t *dst, const ax25_address_t *src,
    uint8_t pid, const uint8_t *info, size_t info_len,
    uint8_t *out, size_t out_cap, size_t *out_len);

/* Facade (ax25_api.h) — project-style wrapper. */
static inline bool AX25_EncodeUiFrame(
    const AX25_Address_t *dst, const AX25_Address_t *src,
    uint8_t pid, const uint8_t *info, uint16_t info_len,
    uint8_t *out_buf, uint16_t out_cap, uint16_t *out_len) {
  size_t n = 0;
  ax25_status_t s = ax25_encode_ui_frame(dst, src, pid, info, info_len,
                                          out_buf, out_cap, &n);
  if (out_len) *out_len = (uint16_t)n;
  return s == AX25_OK;
}
```

## Consequences

- Two names for every public API. Inside a single translation unit, only
  one set is used — no mixing.
- Core library can be lifted into any other C project unchanged.
- One extra header per caller (`#include "ax25_api.h"` replaces
  `#include "ax25.h"` + `#include "ax25_decoder.h"`).
- Static-inline wrappers compile to zero overhead with `-O1` or higher.

## Alternatives considered

- **Choose one style everywhere**: rejected. Rewriting the library in
  PascalCase makes it un-portable; rewriting existing firmware in
  snake_case is a massive diff outside Track 1 scope.
- **#define aliases (`#define AX25_EncodeUiFrame ax25_encode_ui_frame`)**:
  rejected because macro aliases don't translate argument types
  (`size_t` vs `uint16_t`) and produce worse compile errors.
