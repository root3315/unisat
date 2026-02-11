#!/usr/bin/env bash
# UniSat — Run full mission simulation
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
SIM_DIR="$PROJECT_ROOT/simulation"

echo "=========================================="
echo "  UniSat Mission Simulation"
echo "=========================================="

cd "$SIM_DIR"

# Check dependencies
if ! python3 -c "import numpy, plotly" 2>/dev/null; then
    echo "Installing simulation dependencies..."
    pip install -r requirements.txt
fi

echo ""
echo "[1/5] Orbit simulation..."
python3 orbit_simulator.py

echo ""
echo "[2/5] Power budget simulation..."
python3 power_simulator.py

echo ""
echo "[3/5] Thermal analysis..."
python3 thermal_simulator.py

echo ""
echo "[4/5] Link budget calculation..."
python3 link_budget_calculator.py

echo ""
echo "[5/5] Comprehensive mission analysis..."
python3 mission_analyzer.py

echo ""
echo "=========================================="
echo "  Simulation complete!"
echo "  Results saved in: $SIM_DIR/output/"
echo "=========================================="
