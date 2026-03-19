#!/bin/bash
# ═══════════════════════════════════════════════════════════════
#  UltimatePing — macOS Build Script
#  Produces: dist/UltimatePing.app
# ═══════════════════════════════════════════════════════════════
set -e

echo ""
echo "  ╔══════════════════════════════════════════╗"
echo "  ║   UltimatePing — macOS App Builder       ║"
echo "  ╚══════════════════════════════════════════╝"
echo ""

cd "$(dirname "$0")"

# ── 1. check Python ──
if ! command -v python3 &>/dev/null; then
    echo "  [ERROR] Python3 not found. Install from python.org or via brew."
    exit 1
fi
echo "  [OK] Python3 found: $(python3 --version)"

# ── 2. create/activate venv ──
if [ ! -d ".venv" ]; then
    echo "  [..] Creating virtual environment..."
    python3 -m venv .venv
fi
source .venv/bin/activate
echo "  [OK] Virtual environment activated"

# ── 3. install dependencies ──
echo "  [..] Installing dependencies..."
pip install --upgrade pip -q
pip install -r requirements.txt -q
pip install pyinstaller -q
echo "  [OK] Dependencies installed"

# ── 4. generate icons if missing ──
if [ ! -f "icon.icns" ]; then
    echo "  [..] Generating icon..."
    pip install Pillow -q
    python3 gen_icon.py
    python3 -c "
from PIL import Image
ico = Image.open('icon.ico')
ico.save('icon.icns', format='ICNS')
print('  [OK] icon.icns created')
"
fi

# ── 5. build ──
echo "  [..] Building UltimatePing.app ..."
echo ""
pyinstaller ultimateping.spec --noconfirm --clean
echo ""

if [ -d "dist/UltimatePing.app" ]; then
    echo "  ═══════════════════════════════════════════"
    echo "   BUILD SUCCESSFUL!"
    echo "   Output: dist/UltimatePing.app"
    echo "  ═══════════════════════════════════════════"
    echo ""
    echo "  To run:  open dist/UltimatePing.app"
    echo "  To install: drag dist/UltimatePing.app to /Applications"
else
    echo "  [ERROR] Build failed — check the output above."
    exit 1
fi
