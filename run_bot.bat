@echo off
cd /d "%~dp0vera-bot"
echo Starting Vera Bot on port 8000...
.venv\Scripts\uvicorn.exe bot:app --host 0.0.0.0 --port 8000
