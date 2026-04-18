# Security Policy

## Supported versions

| Version | Support |
|---|---|
| 1.2.x (current) | ✅ security fixes, active development |
| 1.1.x | ⚠ critical fixes only, deprecated after 2026-10 |
| < 1.1  | ❌ unsupported |

## Reporting a vulnerability

**Do not** file a public GitHub issue for a security problem.
Instead:

1. Email the maintainer at the address in the `root3315` GitHub
   profile, subject line `[unisat-security]`.
2. Include:
   - A clear description of the issue.
   - Reproduction steps (smallest failing input preferred).
   - Affected versions.
   - Impact assessment you have already done, if any.
3. Expect an acknowledgement within **48 hours**.
4. We publish a coordinated disclosure once a fix ships — your
   contribution is credited in the release notes unless you ask
   otherwise.

## In-scope

- UniSat firmware code under `firmware/`.
- Ground-station Python code under `ground-station/`.
- Simulation tooling under `simulation/`.
- The shared AX.25 and HMAC primitives.

## Out of scope

- Third-party dependencies (report upstream). The SBOM
  at `docs/sbom/sbom-summary.md` lists each dependency and its
  upstream URL.
- Physical attacks on the host running the ground station.
- Denial-of-service that requires jamming the RF band — the
  threat model at `docs/security/ax25_threat_model.md` already
  acknowledges this is unmitigable at the software layer.

## Known-safe configurations

The wire format today:

- **T1 (command injection):** closed by HMAC-SHA256 with
  constant-time verification (`firmware/stm32/Drivers/Crypto/hmac_sha256.c`).
- **T2 (replay):** closed by 32-bit monotonic counter + 64-bit
  sliding-window bitmap (`firmware/stm32/Core/Src/command_dispatcher.c`).
- **T3 (bit-stuff DoS):** closed by hard-rejecting frames above
  `AX25_MAX_FRAME_BYTES` at every decoder stage.
- **T4 (RF garbage flood):** the decoder is proven crash-free by
  10 000+ hypothesis fuzz iterations per release.

See [`docs/security/ax25_threat_model.md`](docs/security/ax25_threat_model.md)
for the full model and residual-risk discussion.

## Cryptographic primitives

UniSat relies on three primitives, all backed by well-tested
reference implementations:

| Primitive | Source | Validation |
|---|---|---|
| SHA-256 | FIPS 180-4 reference | test vectors `"abc"` + `""` asserted at every build |
| HMAC-SHA256 | RFC 2104 + RFC 4231 | §4.2 and §4.3 vectors asserted |
| CRC-16/X.25 | RFC 4506 / AX.25 v2.2 §3.7 | `"123456789" → 0x906E` oracle |

Do not replace these implementations without re-running the shared
golden-vector test (`firmware/tests/test_ax25_golden.c`) and the
RFC-4231 sweep — if either starts to fail, do not ship.

## Responsible disclosure timeline

- **Day 0:** report received, acknowledgement sent.
- **Day ≤ 7:** initial triage + severity assessment.
- **Day ≤ 30:** fix in hand, patch release prepared.
- **Day ≤ 90:** public disclosure with CVE if one has been
  assigned.

We may extend the window if the fix requires a coordinated
upstream change (e.g. an STM32 HAL bug). You will be kept in the
loop.
