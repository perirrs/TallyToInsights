@echo off
echo ============================================================
echo  TallyToInsights - Windows Setup
echo ============================================================
echo.

REM Setup backend
echo [1/2] Setting up backend...
cd backend
call setup.bat
cd ..

echo.
echo [2/2] Frontend dependencies will be installed on first run.
echo.
echo ============================================================
echo  Setup complete! To start the application:
echo.
echo  Open TWO Command Prompt windows:
echo.
echo  Window 1 (Backend):
echo    cd c:\TallyToInsights\backend
echo    start.bat
echo.
echo  Window 2 (Frontend):
echo    cd c:\TallyToInsights\frontend
echo    start.bat
echo.
echo  Then open: http://localhost:5173
echo.
echo  Register your first admin user at:
echo    http://localhost:5173  (use the Register link)
echo  Or via API:
echo    curl -X POST http://localhost:8000/api/auth/register ^
echo      -H "Content-Type: application/json" ^
echo      -d "{\"email\":\"admin@company.com\",\"name\":\"Admin\",\"password\":\"admin123\",\"is_admin\":true}"
echo ============================================================
