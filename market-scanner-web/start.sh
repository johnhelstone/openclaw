#!/bin/bash
# start.sh — Start de DEGIRO Market Scanner webapp
# Gebruik: bash start.sh

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo "================================================"
echo "  DEGIRO Market Scanner — Opstarten"
echo "================================================"

# Controleer Python
if ! command -v python3 &>/dev/null; then
  echo "FOUT: Python 3 is niet geïnstalleerd."
  echo "Download van: https://www.python.org/downloads/"
  exit 1
fi

# Installeer dependencies als ze ontbreken
echo "Controleren dependencies..."
python3 -c "import fastapi, uvicorn, yfinance, pandas, numpy" 2>/dev/null || {
  echo "Dependencies installeren..."
  pip install -r requirements.txt -q
}

# Start de server
echo "Server starten..."
echo ""
python3 main.py
