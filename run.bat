@echo off
cd /d "%~dp0"

echo [1/3] Starting backend...
start "Datalytica Backend" /B cmd /c "cd backend && python -m uvicorn main:app --host 127.0.0.1 --port 8765"

echo [2/3] Waiting for backend to be ready...
:wait
timeout /t 1 /nobreak >nul
curl -s http://127.0.0.1:8765/api/health >nul 2>&1
if errorlevel 1 goto wait

echo [3/3] Launching Datalytica...
set ELECTRON_RUN_AS_NODE=
"frontend\node_modules\electron\dist\electron.exe" "frontend"
