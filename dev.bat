@echo off
setlocal

echo ============================================================
echo  TallyInsights — Dev Preview
echo  Opens the full app without building an installer
echo ============================================================
echo.

REM ── Start Python backend in a new window ──────────────────────────────────
echo [1/3] Starting Python backend (port 8000)...
start "TallyInsights Backend" cmd /k "cd /d %~dp0backend && .venv\Scripts\activate && python desktop_entry.py"

REM ── Start Vite dev server in a new window ─────────────────────────────────
echo [2/3] Starting frontend dev server (port 5173)...
start "TallyInsights Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

REM ── Wait for Vite to be ready, then launch Electron ───────────────────────
echo [3/3] Waiting 5 seconds for servers to start, then opening Electron...
timeout /t 5 /nobreak >nul

echo       Launching Electron window...
cd /d %~dp0
npx electron .

echo.
echo Dev session ended. Close the Backend and Frontend windows manually.
pause
