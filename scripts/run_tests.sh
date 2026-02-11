#!/usr/bin/env bash
# UniSat — Run all test suites
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

echo "=========================================="
echo "  UniSat Test Runner"
echo "=========================================="

FAILED=0

echo ""
echo "[1/3] Running flight software tests..."
echo "--------------------------------------"
if pytest flight-software/tests/ -v --cov=flight-software --tb=short; then
    echo "PASS: Flight software tests"
else
    echo "FAIL: Flight software tests"
    FAILED=1
fi

echo ""
echo "[2/3] Running ground station tests..."
echo "--------------------------------------"
if pytest ground-station/tests/ -v --cov=ground-station --tb=short; then
    echo "PASS: Ground station tests"
else
    echo "FAIL: Ground station tests"
    FAILED=1
fi

echo ""
echo "[3/3] Running linter..."
echo "--------------------------------------"
if ruff check flight-software/ ground-station/ simulation/ configurator/ payloads/; then
    echo "PASS: Linting"
else
    echo "FAIL: Linting"
    FAILED=1
fi

echo ""
echo "=========================================="
if [ $FAILED -eq 0 ]; then
    echo "  All tests passed!"
else
    echo "  Some tests failed. See output above."
    exit 1
fi
echo "=========================================="
