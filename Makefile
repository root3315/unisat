# UniSat — top-level build & test orchestration
# ------------------------------------------------------------------
# Common entry points:
#   make all         — host build + all tests (C + Python)
#   make build       — firmware host build (unisat_core + all test targets)
#   make test        — ctest + pytest
#   make demo        — end-to-end SITL beacon demo
#   make docker-ci   — build the local CI Docker image (one-time)
#   make ci          — run everything inside docker unisat-ci (no local gcc needed)
#   make goldens     — regenerate shared AX.25 golden vectors
#   make trace       — regenerate verification trace matrix
#   make clean       — remove build dir and pycache
#
# STM32 target (requires arm-none-eabi-gcc + st-flash):
#   make target      — cross-compile firmware for STM32F446RE
#   make size        — print per-section flash/RAM usage
#   make flash       — flash built firmware to STM32 via ST-Link
#   make setup-hal   — fetch upstream STM32Cube HAL for production build
# ------------------------------------------------------------------

.PHONY: all build build-firmware test test-c test-py demo \
        docker-ci ci goldens trace clean help \
        target size flash setup-hal

FIRMWARE_DIR := firmware
BUILD_DIR    := $(FIRMWARE_DIR)/build
ARM_BUILD    := $(FIRMWARE_DIR)/build-arm
GS_DIR       := ground-station

# --- help ---------------------------------------------------------

help:
	@echo "UniSat Makefile targets:"
	@echo ""
	@echo "  host / test pipeline:"
	@echo "    make all         Build host + run all tests (C + Python)"
	@echo "    make build       Configure + build firmware host binaries"
	@echo "    make test        Run ctest + pytest"
	@echo "    make test-c      Run C ctest only"
	@echo "    make test-py     Run pytest only"
	@echo "    make demo        End-to-end SITL AX.25 beacon demo"
	@echo "    make docker-ci   Build the unisat-ci image (one-time)"
	@echo "    make ci          Full green pipeline inside unisat-ci container"
	@echo "    make goldens     Regenerate tests/golden/ax25_vectors.{json,inc}"
	@echo "    make trace       Regenerate docs/verification/ax25_trace_matrix.md"
	@echo "    make clean       Remove all build artifacts (host + arm)"
	@echo ""
	@echo "  STM32F446RE target (needs arm-none-eabi-gcc + st-flash):"
	@echo "    make target      Cross-compile firmware .elf / .bin / .hex"
	@echo "    make size        Print per-section flash / RAM usage (sysv)"
	@echo "    make flash       Flash firmware to STM32 via ST-Link"
	@echo "    make setup-hal   Fetch STM32Cube HAL for production build"
	@echo ""
	@echo "  quality gates (Phase 5):"
	@echo "    make cppcheck    Static-analysis gate (error/warning/portability)"
	@echo "    make cppcheck-strict  + MISRA advisory report"
	@echo "    make coverage    Host build + ctest + lcov html report"
	@echo "    make sanitizers  Host build + ctest under ASAN/UBSAN"

# --- main ---------------------------------------------------------

all: build test

build: build-firmware

build-firmware:
	cmake -B $(BUILD_DIR) -S $(FIRMWARE_DIR)
	cmake --build $(BUILD_DIR)

# --- tests --------------------------------------------------------

test: test-c test-py

test-c: build-firmware
	ctest --test-dir $(BUILD_DIR) --output-on-failure

test-py:
	cd $(GS_DIR) && python3 -m pytest tests/test_ax25.py -v

# --- demo ---------------------------------------------------------

demo: build-firmware
	python3 scripts/demo.py --port 52100

# --- goldens & verification ---------------------------------------

goldens:
	python3 scripts/gen_golden_vectors.py

trace:
	python3 scripts/gen_trace_matrix.py

# --- Docker CI ----------------------------------------------------

docker-ci:
	docker build -f docker/Dockerfile.ci -t unisat-ci .

# Run the full pipeline inside the pre-built unisat-ci image — no
# local gcc / cmake required on the host. This is what CI runs and
# what a reviewer should run to reproduce "all green".
ci:
	docker run --rm -v "$(CURDIR):/work" -w /work unisat-ci bash -lc "\
	  cmake -B $(BUILD_DIR) -S $(FIRMWARE_DIR) && \
	  cmake --build $(BUILD_DIR) && \
	  ctest --test-dir $(BUILD_DIR) --output-on-failure && \
	  cd $(GS_DIR) && python3 -m pytest tests/test_ax25.py -v"

# --- Phase 5 quality gates ---------------------------------------
#
#   make cppcheck       static-analysis gate (error/warning/portability)
#   make cppcheck-strict same + MISRA advisory report
#   make coverage       host build + ctest + lcov report
#   make sanitizers     host build + ctest under ASAN/UBSAN
#

.PHONY: cppcheck cppcheck-strict coverage sanitizers

cppcheck:
	scripts/run_cppcheck.sh

cppcheck-strict:
	scripts/run_cppcheck.sh --strict

coverage:
	cmake -B $(BUILD_DIR) -S $(FIRMWARE_DIR) -DCOVERAGE=ON
	cmake --build $(BUILD_DIR)
	ctest --test-dir $(BUILD_DIR) --output-on-failure
	cmake --build $(BUILD_DIR) --target coverage

sanitizers:
	cmake -B $(BUILD_DIR)-san -S $(FIRMWARE_DIR) -DSANITIZERS=ON
	cmake --build $(BUILD_DIR)-san
	ctest --test-dir $(BUILD_DIR)-san --output-on-failure

# --- STM32F446RE target build ------------------------------------
#
# `make target` produces a real ARM .elf / .bin / .hex with size
# report. `make flash` delegates to scripts/flash_stm32.sh which
# enforces the same 90 %-flash / 90 %-RAM budget CI uses.
#
# `make setup-hal` is a one-time fetch of the STM32Cube HAL for a
# production build; without it the firmware still links (via the
# weak shim in firmware/stm32/Target/hal_shim.c) but every bus
# transaction returns HAL_ERROR.

target:
	cmake -B $(ARM_BUILD) -S $(FIRMWARE_DIR) -DCMAKE_BUILD_TYPE=Release
	cmake --build $(ARM_BUILD) --target unisat_firmware.elf -j

size: target
	cmake --build $(ARM_BUILD) --target size

flash:
	scripts/flash_stm32.sh

setup-hal:
	scripts/setup_stm32_hal.sh

# --- clean --------------------------------------------------------

clean:
	rm -rf $(BUILD_DIR) $(ARM_BUILD)
	find . -name "__pycache__" -type d -prune -exec rm -rf {} +
	find . -name "*.pyc" -delete
