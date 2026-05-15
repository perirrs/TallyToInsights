@echo off
setlocal
title TallyInsights Launcher

echo.
echo  ============================================================
echo   TallyInsights - Starting up...
echo  ============================================================
echo.

REM ── Figure out root directory ────────────────────────────────────────────────
set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"

REM ── Check node_modules ───────────────────────────────────────────────────────
if not exist "%ROOT%\node_modules" (
    echo  [!] Root node_modules missing. Running npm install...
    cd /d "%ROOT%"
    npm install
    echo.
)
if not exist "%ROOT%\frontend\node_modules" (
    echo  [!] Frontend node_modules missing. Running npm install in frontend...
    cd /d "%ROOT%\frontend"
    npm install
    echo.
)

REM ── Start Python backend (minimised) ─────────────────────────────────────────
echo  [1/3] Starting backend (port 8000)...
start /min "TallyInsights-Backend" cmd /c "cd /d "%ROOT%\backend" && .venv\Scripts\activate.bat && python desktop_entry.py"

REM ── Start Vite dev server (minimised) ────────────────────────────────────────
echo  [2/3] Starting frontend dev server (port 5173)...
start /min "TallyInsights-Frontend" cmd /c "cd /d "%ROOT%\frontend" && npm run dev"

REM ── Wait for BOTH backend and frontend to be ready ───────────────────────────
echo  [3/3] Waiting for backend and frontend to be ready...
echo        (two minimised windows in taskbar — ignore them)
echo.

set /a waited=0
set "backend_ok=0"
set "frontend_ok=0"

:wait_loop
timeout /t 2 /nobreak >nul
set /a waited+=2

if "%backend_ok%"=="0" (
    curl -s --max-time 1 http://localhost:8000/api/health >nul 2>&1
    if not errorlevel 1 set "backend_ok=1"
)
if "%frontend_ok%"=="0" (
    curl -s --max-time 1 http://localhost:5173 >nul 2>&1
    if not errorlevel 1 set "frontend_ok=1"
)

if "%backend_ok%"=="1" if "%frontend_ok%"=="1" goto launch

if %waited% geq 60 goto timeout_err

echo        Backend: %backend_ok%  Frontend: %frontend_ok%  (%waited%s elapsed)
goto wait_loop

:timeout_err
echo.
echo  [ERROR] Services did not start within 60 seconds.
echo.
echo  Check:
echo    - backend\.venv exists (run setup.bat if missing)
echo    - Node / npm installed
echo    - Ports 5173 and 8000 are free
echo.
pause
goto cleanup

:launch
echo  Both services ready. Opening TallyInsights...
echo.
cd /d "%ROOT%"
npx electron .

:cleanup
echo.
echo  Shutting down background services...
taskkill /FI "WINDOWTITLE eq TallyInsights-Backend*" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq TallyInsights-Frontend*" /F >nul 2>&1
echo  Done.
timeout /t 2 /nobreak >nul
