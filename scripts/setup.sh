#!/usr/bin/env bash
# UniSat — Full project setup script
# Installs all Python dependencies and prepares the development environment

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "=========================================="
echo "  UniSat Development Environment Setup"
echo "=========================================="

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | grep -oP '\d+\.\d+' | head -1)
REQUIRED_VERSION="3.11"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    echo "ERROR: Python >= $REQUIRED_VERSION is required (found $PYTHON_VERSION)"
    exit 1
fi

echo "[1/5] Creating virtual environment..."
cd "$PROJECT_ROOT"
python3 -m venv venv
source venv/bin/activate

echo "[2/5] Installing flight software dependencies..."
pip install -r flight-software/requirements.txt

echo "[3/5] Installing ground station dependencies..."
pip install -r ground-station/requirements.txt

echo "[4/5] Installing simulation & configurator dependencies..."
pip install -r simulation/requirements.txt
pip install -r configurator/requirements.txt

echo "[5/5] Installing development tools..."
pip install pytest pytest-cov pytest-asyncio ruff mypy

echo ""
echo "=========================================="
echo "  Setup complete!"
echo "=========================================="
echo ""
echo "Activate the environment:"
echo "  source venv/bin/activate"
echo ""
echo "Run tests:"
echo "  ./scripts/run_tests.sh"
echo ""
echo "Start ground station:"
echo "  cd ground-station && streamlit run app.py"
