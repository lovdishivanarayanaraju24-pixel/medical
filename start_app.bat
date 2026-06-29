@echo off
echo ===========================================
echo Starting MedVault AI Platform
echo ===========================================

REM Ensure the uploads directory exists
if not exist "uploads" mkdir uploads

REM Start the FastAPI Backend
echo Starting backend server...
start /b cmd /c "cd backend && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000"

echo Waiting for server to start...
timeout /t 3 /nobreak > nul

echo Opening MedVault AI in your default browser...
start http://127.0.0.1:8000/

echo Server is running. Close this window to stop.
pause
