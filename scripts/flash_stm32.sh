#!/usr/bin/env bash
# =============================================================================
#  UniSat — flash the STM32F446RE OBC via ST-Link.
#
#  Pipeline:
#    1. Validate arm-none-eabi + st-flash / st-info are on PATH.
#    2. Build firmware for target (build-arm/ tree) if the .bin is
#       missing or older than any source under firmware/stm32/.
#    3. Report .elf section sizes and overflow-guard (90 % of 512 KB
#       flash, 90 % of 128 KB SRAM) — matches the gate in verify.sh
#       so local flashing cannot ship an image CI would reject.
#    4. Detect the ST-Link probe (st-info --probe) and confirm with
#       the user before writing flash at 0x08000000 + resetting.
#
#  Usage:
#    scripts/flash_stm32.sh                 # interactive confirm
#    scripts/flash_stm32.sh --yes           # no prompt, for CI
#    scripts/flash_stm32.sh --size-only     # build + print size, no flash
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
FIRMWARE_DIR="$PROJECT_ROOT/firmware"
BUILD_DIR="$FIRMWARE_DIR/build-arm"
ELF="$BUILD_DIR/unisat_firmware.elf"
BIN="$BUILD_DIR/unisat_firmware.bin"

AUTO_YES=0
SIZE_ONLY=0
for arg in "$@"; do
    case "$arg" in
        --yes|-y)     AUTO_YES=1 ;;
        --size-only)  SIZE_ONLY=1 ;;
        -h|--help)
            sed -n '3,20p' "$0"
            exit 0
            ;;
    esac
done

echo "=========================================="
echo "  UniSat Firmware Flasher (STM32F446RE)"
echo "=========================================="

# --- toolchain checks -------------------------------------------------------
need() {
    command -v "$1" >/dev/null || {
        echo "ERROR: '$1' not in PATH." >&2
        shift
        echo "       install: $*" >&2
        exit 1
    }
}
need arm-none-eabi-gcc "Ubuntu: apt-get install gcc-arm-none-eabi | macOS: brew install --cask gcc-arm-embedded"
need arm-none-eabi-size "same package as arm-none-eabi-gcc"
need cmake             "Ubuntu: apt-get install cmake | macOS: brew install cmake"
if [ "$SIZE_ONLY" -eq 0 ]; then
    need st-flash "Ubuntu: apt-get install stlink-tools | macOS: brew install stlink"
    need st-info  "same package as st-flash"
fi

# --- build (unconditional — incremental cmake is fast) ----------------------
echo "==> configure (build-arm/)"
cmake -S "$FIRMWARE_DIR" -B "$BUILD_DIR" -DCMAKE_BUILD_TYPE=Release >/dev/null

echo "==> build firmware"
cmake --build "$BUILD_DIR" --target unisat_firmware.elf -j"$(getconf _NPROCESSORS_ONLN 2>/dev/null || echo 2)"

# --- size + budget gate -----------------------------------------------------
echo ""
echo "==> section sizes"
arm-none-eabi-size --format=sysv "$ELF" | awk 'NF'

FLASH_MAX=$((512 * 1024 * 90 / 100))
RAM_MAX=$((128 * 1024 * 90 / 100))
read text data bss _ < <(arm-none-eabi-size "$ELF" | tail -1 | awk '{print $1,$2,$3}')
flash=$((text + data))
ram=$((data + bss))
echo ""
echo "    flash (text+data) = ${flash} B (limit 90 % = ${FLASH_MAX} B)"
echo "    ram   (data+bss)  = ${ram} B (limit 90 % = ${RAM_MAX} B)"

if [ "$flash" -gt "$FLASH_MAX" ] || [ "$ram" -gt "$RAM_MAX" ]; then
    echo "ERROR: firmware exceeds 90 % footprint budget — refusing to flash." >&2
    exit 1
fi

if [ "$SIZE_ONLY" -eq 1 ]; then
    echo ""
    echo "--size-only → done."
    exit 0
fi

# --- probe + confirm + flash ------------------------------------------------
echo ""
echo "==> ST-Link probe"
st-info --probe

if [ "$AUTO_YES" -eq 0 ]; then
    echo ""
    read -p "Flash ${BIN} to STM32 @ 0x08000000 ? (y/N) " -n 1 -r
    echo ""
    [[ $REPLY =~ ^[Yy]$ ]] || { echo "aborted."; exit 0; }
fi

echo "==> writing flash"
st-flash write "$BIN" 0x08000000
echo "==> resetting target"
st-flash reset
echo "done."
