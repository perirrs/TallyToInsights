#!/bin/bash
# Quick start for development
echo "Starting TallyToInsights..."

# Backend
cd backend
pip install -r requirements.txt -q
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
echo "Backend started (PID: $BACKEND_PID)"

# Frontend
cd ../frontend
npm install -q
npm run dev &
FRONTEND_PID=$!
echo "Frontend started (PID: $FRONTEND_PID) → http://localhost:5173"

echo ""
echo "TallyToInsights running:"
echo "  API:      http://localhost:8000/api/docs"
echo "  Frontend: http://localhost:5173"
echo ""
echo "Create your first admin user:"
echo "  curl -X POST http://localhost:8000/api/auth/register \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -d '{\"email\":\"admin@company.com\",\"name\":\"Admin\",\"password\":\"admin123\",\"is_admin\":true}'"

wait
