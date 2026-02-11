#!/usr/bin/env bash
# UniSat — Flash firmware to STM32F4 via ST-Link
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
FIRMWARE_DIR="$PROJECT_ROOT/firmware"
BUILD_DIR="$FIRMWARE_DIR/build"
BINARY="$BUILD_DIR/unisat_firmware.bin"

echo "=========================================="
echo "  UniSat Firmware Flasher"
echo "=========================================="

# Check ST-Link tools
if ! command -v st-flash &> /dev/null; then
    echo "ERROR: st-flash not found. Install stlink-tools:"
    echo "  Ubuntu: sudo apt-get install stlink-tools"
    echo "  macOS:  brew install stlink"
    exit 1
fi

# Build if needed
if [ ! -f "$BINARY" ]; then
    echo "Binary not found. Building firmware..."
    mkdir -p "$BUILD_DIR"
    cd "$BUILD_DIR"
    cmake ..
    make -j$(nproc)
    cd "$SCRIPT_DIR"
fi

if [ ! -f "$BINARY" ]; then
    echo "ERROR: Build failed. Binary not found at $BINARY"
    exit 1
fi

echo ""
echo "Binary: $BINARY"
echo "Size: $(stat --format=%s "$BINARY" 2>/dev/null || stat -f%z "$BINARY") bytes"
echo ""

# Detect ST-Link
echo "Detecting ST-Link programmer..."
st-info --probe

echo ""
read -p "Flash firmware to STM32? (y/N) " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Flashing..."
    st-flash write "$BINARY" 0x08000000
    echo ""
    echo "Flash complete! Resetting target..."
    st-flash reset
    echo "Done."
else
    echo "Aborted."
fi
