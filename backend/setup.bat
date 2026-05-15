@echo off
echo Setting up TallyToInsights backend...

REM Create virtual environment
if not exist ".venv" (
    echo Creating virtual environment...
    python -m venv .venv
)

REM Activate and install dependencies
call .venv\Scripts\activate.bat
echo Installing dependencies...
pip install -r requirements_windows.txt -q

REM Create .env if it doesn't exist
if not exist ".env" (
    echo Creating .env from example...
    copy .env.example .env
    echo IMPORTANT: Edit backend\.env and set a strong SECRET_KEY
)

REM Create uploads directory
if not exist "uploads" mkdir uploads

REM Initialize database
echo Initializing database...
python -c "from app.database import Base, engine; from app.models import user, company, dump, ledger, voucher, stock, audit_result; Base.metadata.create_all(bind=engine); print('Database tables created.')"

echo.
echo Backend setup complete!
echo Run 'start.bat' to start the backend server.
