#!/usr/bin/env bash
# =============================================================================
#  UniSat — cppcheck static-analysis gate (Phase 5).
#
#  Two-mode operation:
#
#    default (CI-blocking):   severity = error,warning,portability.
#                              Catches real bugs: null deref, uninit,
#                              buffer overflow, leak, format mismatch,
#                              badBitmaskCheck, shiftTooManyBits, etc.
#                              Exit code is the pass/fail gate.
#
#    --strict (advisory):     default + style, performance, and the
#                              MISRA-C:2012 addon. Produces a report
#                              at firmware/build/.cppcheck-cache/
#                              misra_report.log.  Does NOT fail the
#                              script — MISRA compliance on the
#                              existing codebase is a scheduled cleanup
#                              (tracked in docs/project/GAPS_AND_ROADMAP.md).
#
#  Flags are assembled from .cppcheck-suppressions in the repo root.
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$SCRIPT_DIR")"
cd "$ROOT"

STRICT=0
for arg in "$@"; do
    case "$arg" in
        --strict) STRICT=1 ;;
        -h|--help)
            sed -n '3,22p' "$0"
            exit 0
            ;;
    esac
done

if ! command -v cppcheck >/dev/null; then
    echo "ERROR: cppcheck not installed." >&2
    echo "       Ubuntu: apt-get install cppcheck" >&2
    echo "       macOS:  brew install cppcheck" >&2
    exit 2
fi

VERSION=$(cppcheck --version | awk '{print $2}')
BUILD_DIR="$ROOT/firmware/build/.cppcheck-cache"
mkdir -p "$BUILD_DIR"
SUPPRESSIONS="$ROOT/.cppcheck-suppressions"

echo "==> cppcheck ${VERSION} — UniSat firmware scan"

BASE_FLAGS=(
    --inline-suppr
    --language=c
    --std=c11
    --platform=unix32
    --suppressions-list="$SUPPRESSIONS"
    --cppcheck-build-dir="$BUILD_DIR"
    -I firmware/stm32/Core/Inc
    -I firmware/stm32/Drivers/AX25
    -I firmware/stm32/Drivers/Crypto
    -I firmware/stm32/Drivers/VirtualUART
    -I firmware/stm32/Drivers/LIS3MDL
    -I firmware/stm32/Drivers/BME280
    -I firmware/stm32/Drivers/TMP117
    -I firmware/stm32/Drivers/MPU9250
    -I firmware/stm32/Drivers/SBM20
    -I firmware/stm32/Drivers/UBLOX
    -I firmware/stm32/Drivers/MCP3008
    -I firmware/stm32/Drivers/SunSensor
    -I firmware/stm32/Drivers/BoardTemp
    -I firmware/stm32/ADCS
    -I firmware/stm32/EPS
    -DSIMULATION_MODE
)

TARGETS=(
    firmware/stm32/Core/Src
    firmware/stm32/Drivers/AX25
    firmware/stm32/Drivers/Crypto
    firmware/stm32/Drivers/BoardTemp
    firmware/stm32/Drivers/LIS3MDL
    firmware/stm32/Drivers/BME280
    firmware/stm32/Drivers/TMP117
    firmware/stm32/Drivers/MPU9250
    firmware/stm32/Drivers/SBM20
    firmware/stm32/Drivers/UBLOX
    firmware/stm32/Drivers/MCP3008
    firmware/stm32/Drivers/SunSensor
    firmware/stm32/ADCS
    firmware/stm32/EPS
)

# --- mode 1: default gate (CI-blocking) --------------------------------
echo "==> gate pass — severity = error,warning,portability"
cppcheck "${BASE_FLAGS[@]}" \
    --enable=warning,portability \
    --error-exitcode=1 \
    "${TARGETS[@]}" 2>&1 | tee "$BUILD_DIR/gate.log"
GATE_STATUS=${PIPESTATUS[0]}

if [ "$GATE_STATUS" -ne 0 ]; then
    echo "==> cppcheck gate FAILED — see $BUILD_DIR/gate.log" >&2
    exit 1
fi
echo "==> gate clean."

# --- mode 2: MISRA advisory report (informative) -----------------------
if [ "$STRICT" -eq 1 ]; then
    echo ""
    echo "==> strict pass — style + performance + MISRA-C:2012 (advisory)"

    ADV_FLAGS=("${BASE_FLAGS[@]}"
        --enable=warning,style,performance,portability)

    # Probe the MISRA addon.
    if cppcheck --addon=misra --version >/dev/null 2>&1; then
        ADV_FLAGS+=(--addon=misra)
        echo "    MISRA addon enabled"
    fi

    # Deliberately does NOT set --error-exitcode: advisory only.
    cppcheck "${ADV_FLAGS[@]}" "${TARGETS[@]}" 2>&1 \
        | tee "$BUILD_DIR/strict.log" || true

    # Summarise so the reviewer can see the MISRA deviation count at
    # a glance instead of scrolling the full log.
    TOTAL=$(grep -c "misra violation" "$BUILD_DIR/strict.log" || echo 0)
    STYLE=$(grep -c "^.*:.*style:" "$BUILD_DIR/strict.log" || echo 0)
    echo ""
    echo "    MISRA deviations : $TOTAL  (tracked in roadmap, not blocking)"
    echo "    style findings   : $STYLE  (cleanup backlog)"
    echo "    full log         : $BUILD_DIR/strict.log"
fi

echo ""
echo "==> cppcheck clean (gate pass, exit 0)"
