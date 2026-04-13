#!/bin/bash
# FRAME Cinema Blog — Start Script
# Works on macOS and Linux

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"

echo ""
echo "╔════════════════════════════════════╗"
echo "║   FRAME Cinema Blog                 ║"
echo "╚════════════════════════════════════╝"
echo ""

# Check Python
if ! command -v python3 &>/dev/null; then
  echo "❌ Python 3 not found. Install from https://python.org"
  exit 1
fi

# Install deps if needed
echo "📦 Checking Python dependencies..."
python3 -c "import flask" 2>/dev/null || pip3 install flask flask-cors werkzeug --break-system-packages 2>/dev/null || pip3 install flask flask-cors werkzeug

echo ""
echo "🎬 Starting backend on http://localhost:5000"
echo "   Admin login: admin / frame2025"
echo "   Open: http://localhost:5000"
echo ""
echo "Press Ctrl+C to stop."
echo ""

cd "$BACKEND_DIR"
python3 app.py
