#!/usr/bin/env bash
set -e

# Unified Python detection: prefer venv, fall back to system
PYTHON=${PYTHON:-python3}
if [ -d ".venv" ]; then
  . .venv/bin/activate 2>/dev/null || true
  PYTHON=python
fi

echo "============================================"
VER=$(cat VERSION 2>/dev/null || echo "v0.6.0")
echo "  Novel Pipeline - Write Engine $VER"
echo "  Install (Mac / Linux)"
echo "============================================"
echo ""

if ! command -v $PYTHON >/dev/null 2>&1; then
  echo "[ERROR] $PYTHON not found. Please install Python 3.10+."
  exit 1
fi

PYVER=$($PYTHON -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "[OK] Python $PYVER"

if [ ! -f "config.json" ] && [ -f "config.example.json" ]; then
  cp config.example.json config.json
  echo "[OK] config.json created from config.example.json"
fi

$PYTHON -m venv .venv
source .venv/bin/activate
PYTHON=python
$PYTHON -m pip install --upgrade pip -q
pip install -r requirements.txt -q

echo ""
$PYTHON novel.py status

echo ""
echo "============================================"
echo "  Install complete."
echo "  Run: ./run_demo.sh"
echo "============================================"
