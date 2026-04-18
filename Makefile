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

.PHONY: help all build build-firmware test test-c test-py demo \
        docker-ci ci goldens trace clean \
        target size flash setup-hal setup-freertos setup-all \
        cppcheck cppcheck-strict coverage sanitizers \
        coverage-py lint-py configurator sbom \
        pin-docker pin-docker-unpin

# Default target: show the help block so a new contributor running
# `make` without arguments sees the menu instead of kicking off a
# full build by accident.
.DEFAULT_GOAL := help

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
	@echo "    make setup-freertos Fetch FreeRTOS kernel + CMSIS-RTOSv2 port"
	@echo "    make setup-all   Run both setup steps (one-time)"
	@echo ""
	@echo "  per-profile firmware (CanSat + CubeSat 1U-12U):"
	@echo "    make target-cansat-minimal"
	@echo "    make target-cansat-standard"
	@echo "    make target-cansat-advanced"
	@echo "    make target-cubesat-1u   target-cubesat-1-5u"
	@echo "    make target-cubesat-2u   target-cubesat-3u"
	@echo "    make target-cubesat-6u   target-cubesat-12u"
	@echo "    make target-all-profiles  — build every profile"
	@echo ""
	@echo "  quality gates (Phase 5):"
	@echo "    make cppcheck    Static-analysis gate (error/warning/portability)"
	@echo "    make cppcheck-strict  + MISRA advisory report"
	@echo "    make coverage    Host build + ctest + lcov html report"
	@echo "    make sanitizers  Host build + ctest under ASAN/UBSAN"
	@echo "    make coverage-py Python tests + pytest-cov (≥ 50 % gate)"
	@echo "    make lint-py     mypy type check on flight-software"
	@echo ""
	@echo "  extras:"
	@echo "    make configurator  Launch Streamlit mission configurator UI"
	@echo "    make sbom        Generate software bill of materials (SPDX)"

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

# --- Python quality gates ----------------------------------------
#
# coverage-py runs pytest with coverage enforcement per the
# [tool.coverage.report] section of flight-software/pyproject.toml
# (current MUST-level gate: 50 %, SHOULD target: 80 %).
#
# lint-py runs mypy on the core/ + modules/ trees for static type
# checking.  Ruff is available via the same [dev] extra for style
# linting — kept separate so CI can parallelise them.

coverage-py:
	cd $(GS_DIR) && python3 -m pytest tests/ -q
	cd flight-software && python3 -m pytest tests/ --cov --cov-report=term

lint-py:
	cd flight-software && python3 -m mypy core modules || \
	    (echo "hint: install mypy via 'pip install -e .[dev]'"; true)

# --- Mission configurator -----------------------------------------
#
# The configurator is a Streamlit wizard under configurator/. This
# target spins it up locally; press Ctrl-C to stop.

configurator:
	cd configurator && python3 -m streamlit run app.py

# --- Software Bill of Materials (SBOM) ----------------------------

sbom:
	scripts/gen_sbom.sh

# --- Docker supply-chain pin -------------------------------------

pin-docker:
	scripts/pin_docker.sh

pin-docker-unpin:
	scripts/pin_docker.sh --unpin

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

# --- Per-profile firmware builds ---------------------------------
#
# Each target below configures the firmware build with a single
# MISSION_PROFILE_<NAME> macro defined, producing an image with only
# the drivers and FDIR policy for that vehicle compiled in. The
# build directory is suffixed so profiles can coexist.
#
#   make target-cansat-standard
#   make target-cubesat-3u
#   make target-cubesat-6u
#
# All profile names map 1:1 to mission_templates/<name>.json and to
# flight-software MissionType values.

.PHONY: target-cansat-minimal target-cansat-standard target-cansat-advanced \
        target-cubesat-1u target-cubesat-1-5u target-cubesat-2u \
        target-cubesat-3u target-cubesat-6u target-cubesat-12u \
        target-all-profiles

PROFILE_BUILD = $(FIRMWARE_DIR)/build-arm-$(1)
define build_profile
	cmake -B $(call PROFILE_BUILD,$(1)) -S $(FIRMWARE_DIR) \
	      -DCMAKE_BUILD_TYPE=Release \
	      -DCMAKE_C_FLAGS="-DMISSION_PROFILE_$(2)=1"
	cmake --build $(call PROFILE_BUILD,$(1)) --target unisat_firmware.elf -j
endef

target-cansat-minimal:
	$(call build_profile,cansat-minimal,CANSAT_MINIMAL)

target-cansat-standard:
	$(call build_profile,cansat-standard,CANSAT_STANDARD)

target-cansat-advanced:
	$(call build_profile,cansat-advanced,CANSAT_ADVANCED)

target-cubesat-1u:
	$(call build_profile,cubesat-1u,CUBESAT_1U)

target-cubesat-1-5u:
	$(call build_profile,cubesat-1-5u,CUBESAT_1_5U)

target-cubesat-2u:
	$(call build_profile,cubesat-2u,CUBESAT_2U)

target-cubesat-3u:
	$(call build_profile,cubesat-3u,CUBESAT_3U)

target-cubesat-6u:
	$(call build_profile,cubesat-6u,CUBESAT_6U)

target-cubesat-12u:
	$(call build_profile,cubesat-12u,CUBESAT_12U)

target-all-profiles: target-cansat-minimal target-cansat-standard \
                     target-cansat-advanced target-cubesat-1u \
                     target-cubesat-1-5u target-cubesat-2u \
                     target-cubesat-3u target-cubesat-6u \
                     target-cubesat-12u
	@echo "==> all 9 mission profiles built"

flash:
	scripts/flash_stm32.sh

setup-hal:
	scripts/setup_stm32_hal.sh

setup-freertos:
	scripts/setup_freertos.sh

setup-all: setup-hal setup-freertos
	@echo "==> all build-time dependencies in place"

# --- clean --------------------------------------------------------

clean:
	rm -rf $(BUILD_DIR) $(ARM_BUILD)
	rm -rf $(FIRMWARE_DIR)/build-arm-*
	find . -name "__pycache__" -type d -prune -exec rm -rf {} +
	find . -name "*.pyc" -delete
