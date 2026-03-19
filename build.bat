@echo off
setlocal enabledelayedexpansion

echo ============================================================
echo  TallyInsights — Full Installer Build
echo  Output: dist-installer\TallyInsights-Setup.exe
echo ============================================================
echo.

REM ── Check prerequisites ────────────────────────────────────────────────────
echo [Check] Verifying prerequisites...

python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Install from https://python.org
    pause & exit /b 1
)

node --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Node.js not found. Install from https://nodejs.org
    pause & exit /b 1
)

echo [Check] OK — Python and Node.js found.
echo.

REM ── Step 1: Create app icon ────────────────────────────────────────────────
echo [1/5] Creating app icon...
python create_icon.py
if errorlevel 1 (
    echo ERROR: Failed to create icon.
    pause & exit /b 1
)
echo.

REM ── Step 2: Build Python backend into backend.exe ─────────────────────────
echo [2/5] Building Python backend (this takes 3-5 minutes)...
cd backend

if not exist ".venv" (
    echo       Creating virtual environment...
    python -m venv .venv
)

call .venv\Scripts\activate.bat

echo       Installing dependencies...
pip install -r requirements_windows.txt -q
if errorlevel 1 (
    echo ERROR: pip install failed.
    cd ..
    pause & exit /b 1
)

echo       Installing PyInstaller...
pip install pyinstaller==6.10.0 -q

echo       Running PyInstaller...
pyinstaller TallyInsights.spec --noconfirm
if errorlevel 1 (
    echo ERROR: PyInstaller failed.
    cd ..
    pause & exit /b 1
)

cd ..

REM Copy PyInstaller output to backend-dist (where electron-builder looks)
echo       Copying backend to backend-dist\...
if exist "backend-dist" rmdir /s /q backend-dist
mkdir backend-dist
xcopy /e /i /q backend\dist\backend backend-dist\backend
echo.

REM ── Step 3: Build React frontend ──────────────────────────────────────────
echo [3/5] Building frontend...
cd frontend

if not exist "node_modules" (
    echo       Installing frontend dependencies...
    npm install
)

npm run build
if errorlevel 1 (
    echo ERROR: Frontend build failed.
    cd ..
    pause & exit /b 1
)
cd ..
echo.

REM ── Step 4: Install Electron dependencies ─────────────────────────────────
echo [4/5] Installing Electron dependencies...
if not exist "node_modules" (
    npm install
)
echo.

REM ── Step 5: Build Windows installer ───────────────────────────────────────
echo [5/5] Building Windows installer with electron-builder...
npx electron-builder --win
if errorlevel 1 (
    echo ERROR: electron-builder failed.
    pause & exit /b 1
)

echo.
echo ============================================================
echo  BUILD COMPLETE!
echo.
echo  Installer: dist-installer\TallyInsights-Setup.exe
echo.
echo  Share this file with customers. They double-click it,
echo  install like any Windows app, and enter their product key.
echo ============================================================
pause
