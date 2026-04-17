#!/usr/bin/env bash
# ==============================================================================
#  UniSat — fetch STM32Cube HAL (F4 family) into the firmware source tree.
#
#  The target build in firmware/CMakeLists.txt links one of two HAL layers:
#
#    (a) firmware/stm32/Drivers/STM32F4xx_HAL_Driver/   — the upstream ST HAL
#    (b) firmware/stm32/Target/hal_shim.c               — weak no-op fallback
#
#  (b) is always present so the repo produces an .elf even on a fresh clone;
#  this script downloads (a) so that the resulting firmware actually reads
#  sensors, transmits over UART, etc. on real hardware.
#
#  Source
#  ------
#  STMicroelectronics publishes the HAL under the 3-Clause BSD "SLA0044"
#  licence at github.com/STMicroelectronics/STM32CubeF4. We fetch exactly
#  the two directories the firmware depends on:
#
#    Drivers/STM32F4xx_HAL_Driver/Inc/
#    Drivers/STM32F4xx_HAL_Driver/Src/
#    Drivers/CMSIS/Device/ST/STM32F4xx/Include/
#    Drivers/CMSIS/Include/
#
#  and discard the rest (BSP, Middleware, demos — ~500 MB that UniSat does
#  not need). Resulting on-disk footprint: ~15 MB.
#
#  The HAL is fetched into firmware/stm32/Drivers/STM32F4xx_HAL_Driver/ and
#  firmware/stm32/Drivers/CMSIS/ — paths that CMakeLists.txt searches with
#  find_path(); if they exist, the CubeMX sources are compiled, if not,
#  hal_shim.c is linked instead.
#
#  Usage
#  -----
#    scripts/setup_stm32_hal.sh           # default tag = v1.27.1
#    scripts/setup_stm32_hal.sh v1.28.0   # pin a specific release tag
#    scripts/setup_stm32_hal.sh --clean   # remove fetched HAL (re-stub)
#
#  .gitignore already excludes Drivers/STM32F4xx_HAL_Driver/ and
#  Drivers/CMSIS/ so this script's output is never committed — the HAL
#  stays a build-time dependency, not part of the UniSat history.
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DRIVERS_DIR="$PROJECT_ROOT/firmware/stm32/Drivers"
HAL_TAG="${1:-v1.27.1}"
TMP_DIR="$(mktemp -d)"

cleanup() { rm -rf "$TMP_DIR"; }
trap cleanup EXIT

if [[ "${1:-}" == "--clean" ]]; then
    echo "==> removing fetched HAL / CMSIS trees"
    rm -rf "$DRIVERS_DIR/STM32F4xx_HAL_Driver" "$DRIVERS_DIR/CMSIS"
    echo "==> hal_shim.c will be linked on the next build"
    exit 0
fi

if [[ -d "$DRIVERS_DIR/STM32F4xx_HAL_Driver" ]]; then
    echo "==> HAL already present at $DRIVERS_DIR/STM32F4xx_HAL_Driver"
    echo "    use '--clean' to remove, or pass a tag to re-fetch"
    exit 0
fi

echo "==> fetching STM32CubeF4 $HAL_TAG"
if ! command -v git >/dev/null; then
    echo "ERROR: git not found — install git or unzip the release tarball manually" >&2
    exit 1
fi

git clone --depth 1 --branch "$HAL_TAG" \
    https://github.com/STMicroelectronics/STM32CubeF4.git \
    "$TMP_DIR/cube" >/dev/null 2>&1 || {
    echo "ERROR: git clone failed. Check network, or download the release zip" >&2
    echo "       manually from https://github.com/STMicroelectronics/STM32CubeF4" >&2
    exit 1
}

echo "==> installing HAL + CMSIS into $DRIVERS_DIR"
mkdir -p "$DRIVERS_DIR/STM32F4xx_HAL_Driver"
mkdir -p "$DRIVERS_DIR/CMSIS"

cp -r "$TMP_DIR/cube/Drivers/STM32F4xx_HAL_Driver/Inc" \
      "$DRIVERS_DIR/STM32F4xx_HAL_Driver/"
cp -r "$TMP_DIR/cube/Drivers/STM32F4xx_HAL_Driver/Src" \
      "$DRIVERS_DIR/STM32F4xx_HAL_Driver/"
cp -r "$TMP_DIR/cube/Drivers/CMSIS/Device/ST/STM32F4xx/Include" \
      "$DRIVERS_DIR/CMSIS/"
cp -r "$TMP_DIR/cube/Drivers/CMSIS/Include" \
      "$DRIVERS_DIR/CMSIS/CMSIS_Include"

echo "==> done."
echo "    HAL:   $DRIVERS_DIR/STM32F4xx_HAL_Driver   (~$(du -sh "$DRIVERS_DIR/STM32F4xx_HAL_Driver" | cut -f1))"
echo "    CMSIS: $DRIVERS_DIR/CMSIS                  (~$(du -sh "$DRIVERS_DIR/CMSIS" | cut -f1))"
echo
echo "    re-run cmake to pick up the new include path, then 'make flash'."
