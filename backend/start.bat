@echo off
echo Starting TallyToInsights backend on http://localhost:8000 ...
call .venv\Scripts\activate.bat
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
