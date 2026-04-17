# UniSat — top-level build & test orchestration
# ------------------------------------------------------------------
# Common entry points:
#   make all        — host build + all tests (C + Python)
#   make build      — firmware host build (unisat_core + all test targets)
#   make test       — ctest + pytest
#   make demo       — end-to-end SITL beacon demo
#   make docker-ci  — build the local CI Docker image (one-time)
#   make ci         — run everything inside docker unisat-ci (no local gcc needed)
#   make goldens    — regenerate shared AX.25 golden vectors
#   make trace      — regenerate verification trace matrix
#   make clean      — remove build dir and pycache
# ------------------------------------------------------------------

.PHONY: all build build-firmware test test-c test-py demo \
        docker-ci ci goldens trace clean help

FIRMWARE_DIR := firmware
BUILD_DIR    := $(FIRMWARE_DIR)/build
GS_DIR       := ground-station

# --- help ---------------------------------------------------------

help:
	@echo "UniSat Makefile targets:"
	@echo "  make all         Build host + run all tests (C + Python)"
	@echo "  make build       Configure + build firmware host binaries"
	@echo "  make test        Run ctest + pytest"
	@echo "  make test-c      Run C ctest only"
	@echo "  make test-py     Run pytest only"
	@echo "  make demo        End-to-end SITL AX.25 beacon demo"
	@echo "  make docker-ci   Build the unisat-ci image (one-time)"
	@echo "  make ci          Full green pipeline inside unisat-ci container"
	@echo "  make goldens     Regenerate tests/golden/ax25_vectors.{json,inc}"
	@echo "  make trace       Regenerate docs/verification/ax25_trace_matrix.md"
	@echo "  make clean       Remove build artifacts"

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

# --- clean --------------------------------------------------------

clean:
	rm -rf $(BUILD_DIR)
	find . -name "__pycache__" -type d -prune -exec rm -rf {} +
	find . -name "*.pyc" -delete
