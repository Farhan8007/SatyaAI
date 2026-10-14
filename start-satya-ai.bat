@echo off
echo Starting SATYA AI backend and frontend...

start "SATYA AI Backend" cmd /k "cd /d %~dp0backend && venv\Scripts\activate && uvicorn app.main:app --reload"

timeout /t 3 /nobreak >nul

start "SATYA AI Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

echo Both are starting in their own windows. You can minimize them, just don't close them.
echo Once ready, go to http://localhost:3000
