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
REM Remove trailing backslash
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"

REM ── Check that node_modules exist ────────────────────────────────────────────
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

REM ── Start Python backend ─────────────────────────────────────────────────────
echo  [1/3] Starting backend (port 8000)...
start /min "TallyInsights-Backend" cmd /c "cd /d "%ROOT%\backend" && .venv\Scripts\activate.bat && python desktop_entry.py"

REM ── Start Vite dev server ────────────────────────────────────────────────────
echo  [2/3] Starting frontend dev server (port 5173)...
start /min "TallyInsights-Frontend" cmd /c "cd /d "%ROOT%\frontend" && npm run dev"

REM ── Wait for frontend to be ready ────────────────────────────────────────────
echo  [3/3] Waiting for services to be ready...
echo        (minimised windows in your taskbar — you can close them after the app opens)
echo.

set /a waited=0
:wait_loop
timeout /t 2 /nobreak >nul
set /a waited+=2
REM Try to reach Vite
curl -s --max-time 1 http://localhost:5173 >nul 2>&1
if %errorlevel%==0 goto launch
if %waited% geq 40 goto timeout_err
echo        Still waiting... (%waited%s)
goto wait_loop

:timeout_err
echo.
echo  [ERROR] Services did not start within 40 seconds.
echo.
echo  Possible causes:
echo    - backend\.venv does not exist  (run setup.bat first)
echo    - Node / npm not installed
echo    - Port 5173 or 8000 already in use
echo.
pause
goto cleanup

:launch
echo  Opening TallyInsights...
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
