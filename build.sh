#!/bin/bash
set -e

echo "============================================================"
echo " TallyInsights — macOS DMG Build"
echo " Output: dist-installer/TallyInsights-<version>.dmg"
echo "============================================================"
echo

# ── Check prerequisites ────────────────────────────────────────────────────
echo "[Check] Verifying prerequisites..."

if ! command -v python3 &>/dev/null; then
    echo "ERROR: python3 not found. Install from https://python.org"
    exit 1
fi

if ! command -v node &>/dev/null; then
    echo "ERROR: node not found. Install from https://nodejs.org"
    exit 1
fi

echo "[Check] OK — Python 3 and Node.js found."
echo

# ── Step 1: Create app icons ───────────────────────────────────────────────
echo "[1/5] Creating app icons..."
if [ -f create_icon.py ]; then
    python3 create_icon.py
fi

# electron-builder needs a .icns for macOS — generate from icon.png if present
if [ -f assets/icon.png ] && [ ! -f assets/icon.icns ]; then
    echo "      Generating icon.icns from icon.png..."
    mkdir -p assets/icon.iconset
    for size in 16 32 64 128 256 512; do
        sips -z $size $size assets/icon.png --out "assets/icon.iconset/icon_${size}x${size}.png" 2>/dev/null || true
        double=$((size * 2))
        sips -z $double $double assets/icon.png --out "assets/icon.iconset/icon_${size}x${size}@2x.png" 2>/dev/null || true
    done
    iconutil -c icns assets/icon.iconset -o assets/icon.icns 2>/dev/null || \
        echo "      Warning: iconutil failed — DMG will use default icon"
    rm -rf assets/icon.iconset
fi
echo

# ── Step 2: Build Python backend ──────────────────────────────────────────
echo "[2/5] Building Python backend (this takes 3–5 minutes)..."
cd backend

if [ ! -d ".venv" ]; then
    echo "      Creating virtual environment..."
    python3 -m venv .venv
fi

source .venv/bin/activate

echo "      Installing dependencies..."
pip install -r requirements.txt -q

echo "      Installing PyInstaller..."
pip install pyinstaller==6.10.0 -q

echo "      Running PyInstaller..."
pyinstaller TallyInsights.spec --noconfirm

cd ..

echo "      Copying backend to backend-dist/..."
rm -rf backend-dist
mkdir -p backend-dist
cp -r backend/dist/backend backend-dist/backend
echo

# ── Step 3: Build React frontend ──────────────────────────────────────────
echo "[3/5] Building frontend..."
cd frontend

if [ ! -d "node_modules" ]; then
    echo "      Installing frontend dependencies..."
    npm install
fi

npm run build
cd ..
echo

# ── Step 4: Install Electron dependencies ─────────────────────────────────
echo "[4/5] Installing Electron dependencies..."
if [ ! -d "node_modules" ]; then
    npm install
fi
echo

# ── Step 5: Build macOS DMG ───────────────────────────────────────────────
echo "[5/5] Building macOS DMG with electron-builder..."
npx electron-builder --mac
echo

echo "============================================================"
echo " BUILD COMPLETE!"
echo
echo " DMG: dist-installer/TallyInsights-*.dmg"
echo
echo " Share this DMG with Mac users. They open it, drag"
echo " TallyInsights to Applications, and enter their product key."
echo "============================================================"
