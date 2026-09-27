@echo off
cd /d "%~dp0vera-bot"
if exist ".venv\Scripts\python.exe" (
    echo Starting Vera Bot using virtualenv...
    .venv\Scripts\python.exe -m uvicorn bot:app --host 0.0.0.0 --port 8000
) else (
    echo Starting Vera Bot using system python...
    python -m uvicorn bot:app --host 0.0.0.0 --port 8000
)
