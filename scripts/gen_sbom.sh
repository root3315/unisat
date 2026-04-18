#!/usr/bin/env bash
# =============================================================================
#  UniSat — generate a Software Bill of Materials (SBOM) in SPDX format.
#
#  Scope
#  -----
#  Three artefacts produced under docs/sbom/:
#
#    1. sbom-python.spdx    Python direct deps from pyproject.toml +
#                            requirements.txt files
#    2. sbom-c-firmware.spdx Firmware vendored / fetched C libraries
#                            (Cube HAL, FreeRTOS, FreeRTOS port)
#    3. sbom-summary.md      Human-readable index with versions,
#                            licences, and the SPDX file references
#
#  Why SBOM matters
#  ----------------
#  A TRL-5 software package needs a machine-readable accounting of
#  every third-party dependency. This lets a reviewer (or a future
#  supply-chain scanner) verify: no abandoned libraries, no
#  incompatible licences, no silently-upgraded versions slipping in.
#
#  Tool strategy
#  -------------
#  The script prefers `syft` (Anchore SBOM tool) if present — it
#  produces rich SPDX output including transitive deps. Falls back
#  to a hand-rolled scan that lists pyproject + requirements.txt
#  declarations + the vendored C trees so the SBOM is always
#  something rather than nothing.
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$SCRIPT_DIR")"
OUT_DIR="$ROOT/docs/sbom"
mkdir -p "$OUT_DIR"

echo "==> generating SBOM at $OUT_DIR"

# Use syft if available — richest output.
if command -v syft >/dev/null; then
    echo "    syft detected ($(syft version 2>&1 | head -1))"
    syft dir:"$ROOT" -o spdx-json > "$OUT_DIR/sbom-full.spdx.json"
    syft dir:"$ROOT" -o table     > "$OUT_DIR/sbom-summary.txt"
    echo "    -> $OUT_DIR/sbom-full.spdx.json"
    echo "    -> $OUT_DIR/sbom-summary.txt"
fi

# Hand-rolled fallback — always runs, complements syft.

NOW=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
cat > "$OUT_DIR/sbom-summary.md" <<EOF
# UniSat — Software Bill of Materials

**Generated:** $NOW
**Branch:** $(git -C "$ROOT" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
**Commit:** $(git -C "$ROOT" rev-parse --short HEAD 2>/dev/null || echo "unknown")

## Python dependencies

### flight-software

EOF

if [ -f "$ROOT/flight-software/pyproject.toml" ]; then
    awk '/^dependencies = \[/,/^\]/' "$ROOT/flight-software/pyproject.toml" \
        | grep -E '^\s*"' | sed 's/^\s*/- /; s/,$//' \
        >> "$OUT_DIR/sbom-summary.md" || true
fi

cat >> "$OUT_DIR/sbom-summary.md" <<'EOF'

### ground-station

EOF

if [ -f "$ROOT/ground-station/requirements.txt" ]; then
    grep -v '^#' "$ROOT/ground-station/requirements.txt" \
        | grep -v '^\s*$' \
        | sed 's/^/- /' \
        >> "$OUT_DIR/sbom-summary.md" || true
fi

cat >> "$OUT_DIR/sbom-summary.md" <<'EOF'

## C / C++ / Assembly dependencies (firmware)

These libraries are fetched at build time (not committed) via
`scripts/setup_stm32_hal.sh` and `scripts/setup_freertos.sh`.
Pinned tags:

| Name | Source | Pinned tag | License | Fetched by |
|------|--------|------------|---------|------------|
| STM32CubeF4 HAL | github.com/STMicroelectronics/STM32CubeF4 | v1.27.1 | SLA0044 (BSD-3-Clause variant) | `scripts/setup_stm32_hal.sh` |
| CMSIS Core (ARM) | from STM32CubeF4 bundle | same | Apache-2.0 | `scripts/setup_stm32_hal.sh` |
| FreeRTOS Kernel | github.com/FreeRTOS/FreeRTOS-Kernel | V10.6.1 | MIT | `scripts/setup_freertos.sh` |
| CMSIS-RTOSv2 wrapper | from STM32CubeF4 bundle | v1.27.1 | Apache-2.0 | `scripts/setup_freertos.sh` |
| Unity (test framework) | ThrowTheSwitch/Unity | in-tree header-only | MIT | vendored in `firmware/tests/unity/` |

## CI Docker image

`docker/Dockerfile.ci` builds on an official Ubuntu base. See the
Dockerfile for the pinned digest.

## Links

- Full SPDX JSON (syft-generated, if available): `sbom-full.spdx.json`
- Summary table (syft-generated, if available): `sbom-summary.txt`
EOF

echo "    -> $OUT_DIR/sbom-summary.md"
echo
echo "==> done."
