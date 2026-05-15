# TallyInsights — Desktop Build Guide

## Architecture

```
TallyInsights.exe (Electron)
├── electron/main.js          ← Window manager, activation guard, backend spawner
├── electron/product-key.js   ← Offline HMAC-SHA256 key validation
├── frontend/dist/            ← Built React app (loaded as file://)
└── resources/backend/        ← PyInstaller-bundled Python backend
    └── backend.exe           ← FastAPI + all 300 audit checks
```

All data stored locally in `%APPDATA%\TallyInsights\`:
- `tallyinsights.db` — SQLite database
- `uploads/` — Tally dump files
- `activation` — encrypted license store (separate, in Electron userData)

## Product Key System

Keys are validated **offline** (no internet needed) using HMAC-SHA256.
Each key is **machine-locked** — tied to the Windows hardware UUID on first use.

### Generating Keys (Developer Only)

```bash
python generate_keys.py         # generates keys #1–#10
python generate_keys.py 50      # generates 50 keys from #1
python generate_keys.py 20 101  # generates 20 keys from #101

python generate_keys.py validate TALLY-XXXXX-XXXXX-XXXXX-XXXXX
```

**KEEP `generate_keys.py` AND `electron/product-key.js`'s MASTER_SECRET PRIVATE.**
If the secret leaks, anyone can generate valid keys.

## Development Setup

### Prerequisites
- Python 3.11+
- Node.js 20+
- npm

### Step 1 — Backend (Terminal 1)
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements_windows.txt
uvicorn app.main:app --reload --port 8000
```

### Step 2 — Frontend dev server (Terminal 2)
```bash
cd frontend
npm install
npm run dev
```

### Step 3 — Electron (Terminal 3)
```bash
# From repo root
npm install
npm run dev        # starts Electron loading http://localhost:5173
```

In dev mode, the activation screen is skipped (no `window.electron` in plain browser,
and Electron checks local encrypted store). To test activation:
- Press `Ctrl+Shift+I` in the Electron window → Application tab → Clear Storage
  (or delete `%APPDATA%\TallyInsights\` userData folder)

## Production Build

### Step 1 — Build React frontend
```bash
cd frontend
npm run build      # outputs to frontend/dist/
```

### Step 2 — Bundle Python backend (run from backend/)
```bash
cd backend
pip install pyinstaller
pyinstaller TallyInsights.spec
# Output: backend/dist/backend/
```

### Step 3 — Prepare resources for electron-builder
```bash
# From repo root
mkdir -p backend-dist
xcopy /E /I backend\dist\backend backend-dist\backend
```

### Step 4 — Package Electron app
```bash
# From repo root
npm install
npm run build      # builds React + packages with electron-builder
# Output: dist-installer/TallyInsights Setup x.x.x.exe
```

## Installer

The NSIS installer (`dist-installer/TallyInsights Setup x.x.x.exe`):
- Installs to `C:\Program Files\TallyInsights\` by default
- Creates Desktop + Start Menu shortcuts
- Includes uninstaller

## First-Time User Flow

1. Install from `.exe` installer
2. Launch TallyInsights from Desktop/Start Menu
3. **Activation screen** appears — enter product key `TALLY-XXXXX-XXXXX-XXXXX-XXXXX`
4. App validates key locally, records machine ID, and relaunches
5. **Login screen** — register first admin user
6. Start uploading Tally data files

## Changing the Master Secret (IMPORTANT before distribution)

1. Generate a new random secret (32+ chars)
2. Update `MASTER_SECRET` in **both** files — they must match:
   - `generate_keys.py` line: `MASTER_SECRET = '...'`
   - `electron/product-key.js` line: `const MASTER_SECRET = '...'`
3. Regenerate all your product keys
