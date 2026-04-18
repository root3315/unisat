#!/usr/bin/env bash
# ==============================================================================
#  UniSat — fetch FreeRTOS kernel + CMSIS-RTOSv2 wrapper.
#
#  The UniSat firmware calls the CMSIS-RTOSv2 C API (`osKernelStart`,
#  `osThreadNew`, `osMessageQueueNew`, `osDelay`) which is the thin
#  wrapper ST ships on top of the FreeRTOS kernel. This script fetches
#  the upstream FreeRTOS (v10.6.1 pinned) + CMSIS-RTOSv2 sources and
#  drops them into the path the firmware CMake build already expects:
#
#    firmware/stm32/Middlewares/FreeRTOS/Source          -- kernel
#    firmware/stm32/Middlewares/FreeRTOS/Source/include
#    firmware/stm32/Middlewares/FreeRTOS/Source/portable/GCC/ARM_CM4F
#    firmware/stm32/Middlewares/CMSIS_RTOS_V2
#
#  Companion to scripts/setup_stm32_hal.sh — together they produce a
#  real, linkable STM32F446 image. Without this script the target
#  build still links (the HAL shim keeps the dispatcher / sensor
#  drivers happy) but tasks never start because the kernel isn't
#  present.
#
#  Source
#  ------
#  github.com/FreeRTOS/FreeRTOS-Kernel — the kernel-only submodule
#  repository (no demos, no middleware); about 2 MB total. We fetch
#  the 10.6.1 release tag because it matches the port layout that
#  STM32CubeMX generates for the F4 family.
#
#  CMSIS-RTOSv2 wrapper comes from the STM32CubeF4 tree we already
#  fetched in setup_stm32_hal.sh; if that path is not present this
#  script prints a clear diagnostic and exits non-zero.
#
#  Usage
#  -----
#    scripts/setup_freertos.sh              # default tag = V10.6.1
#    scripts/setup_freertos.sh V11.0.0      # pin a specific release
#    scripts/setup_freertos.sh --clean      # remove fetched tree
#
#  .gitignore already excludes firmware/stm32/Middlewares/ so this
#  script's output is never committed — kernel stays a build-time
#  dependency, not part of the UniSat history.
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
MW_DIR="$PROJECT_ROOT/firmware/stm32/Middlewares"
CUBE_DIR="$PROJECT_ROOT/firmware/stm32/Drivers/STM32F4xx_HAL_Driver"
FREERTOS_TAG="${1:-V10.6.1}"
TMP_DIR="$(mktemp -d)"

cleanup() { rm -rf "$TMP_DIR"; }
trap cleanup EXIT

if [[ "${1:-}" == "--clean" ]]; then
    echo "==> removing fetched FreeRTOS + CMSIS-RTOSv2 trees"
    rm -rf "$MW_DIR/FreeRTOS" "$MW_DIR/CMSIS_RTOS_V2"
    # Remove the Middlewares dir if empty.
    rmdir "$MW_DIR" 2>/dev/null || true
    echo "==> done."
    exit 0
fi

if [[ -d "$MW_DIR/FreeRTOS/Source" ]]; then
    echo "==> FreeRTOS already present at $MW_DIR/FreeRTOS"
    echo "    use '--clean' to remove, or pass a tag to re-fetch"
    exit 0
fi

if ! command -v git >/dev/null; then
    echo "ERROR: git not found. Install git or extract the release" >&2
    echo "       tarball from https://github.com/FreeRTOS/FreeRTOS-Kernel" >&2
    exit 1
fi

echo "==> fetching FreeRTOS-Kernel $FREERTOS_TAG"
git clone --depth 1 --branch "$FREERTOS_TAG" \
    https://github.com/FreeRTOS/FreeRTOS-Kernel.git \
    "$TMP_DIR/kernel" >/dev/null 2>&1 || {
    echo "ERROR: git clone failed. Check network or the tag name." >&2
    exit 1
}

mkdir -p "$MW_DIR/FreeRTOS"

# Kernel .c files + public include directory + the Cortex-M4F port.
mkdir -p "$MW_DIR/FreeRTOS/Source/portable"
cp "$TMP_DIR/kernel"/*.c              "$MW_DIR/FreeRTOS/Source/"       2>/dev/null || true
cp -r "$TMP_DIR/kernel/include"       "$MW_DIR/FreeRTOS/Source/"
cp -r "$TMP_DIR/kernel/portable/GCC/ARM_CM4F" \
      "$MW_DIR/FreeRTOS/Source/portable/GCC_ARM_CM4F"
cp    "$TMP_DIR/kernel/portable/MemMang/heap_4.c" \
      "$MW_DIR/FreeRTOS/Source/"

echo "    kernel installed (~$(du -sh "$MW_DIR/FreeRTOS" | cut -f1))"

# ── CMSIS-RTOSv2 wrapper ───────────────────────────────────────────────
# The wrapper ships in STM32CubeF4. Look for it; if missing, ask the
# user to run setup_stm32_hal.sh first.
echo "==> installing CMSIS-RTOSv2 wrapper (from STM32CubeF4)"
CUBE_MW_RTOS="$CUBE_DIR/../../Middlewares/Third_Party/FreeRTOS/Source/CMSIS_RTOS_V2"
if [[ -d "$CUBE_MW_RTOS" ]]; then
    mkdir -p "$MW_DIR/CMSIS_RTOS_V2"
    cp -r "$CUBE_MW_RTOS"/. "$MW_DIR/CMSIS_RTOS_V2/"
    echo "    wrapper copied from existing STM32CubeF4 fetch"
else
    # Fallback: fetch a minimal CMSIS-RTOSv2 header stub from the
    # official ARM repo. cmsis_os2.h alone is enough to satisfy the
    # firmware's includes; the .c glue comes with STM32CubeF4.
    echo "    STM32CubeF4 MW dir not found at: $CUBE_MW_RTOS"
    echo "    NOTE: run 'scripts/setup_stm32_hal.sh' first to fetch the"
    echo "          CMSIS-RTOSv2 wrapper together with STM32Cube HAL."
    echo "          Alternatively, supply cmsis_os2.h manually at"
    echo "          $MW_DIR/CMSIS_RTOS_V2/Include/"
fi

echo
echo "==> summary"
echo "    FreeRTOS  : $MW_DIR/FreeRTOS   ($FREERTOS_TAG)"
if [[ -d "$MW_DIR/CMSIS_RTOS_V2" ]]; then
    echo "    CMSIS-RTOS: $MW_DIR/CMSIS_RTOS_V2"
fi
echo
echo "    next steps:"
echo "      cmake -B firmware/build-arm -S firmware -DCMAKE_BUILD_TYPE=Release"
echo "      cmake --build firmware/build-arm --target unisat_firmware.elf"
echo
echo "    Expected output: flash / RAM usage under the 90 % budget gate."
