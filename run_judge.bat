@echo off
cd /d "%~dp0vera-bot"
if exist ".venv\Scripts\python.exe" (
    echo Running Judge Simulator using virtualenv...
    .venv\Scripts\python.exe -X utf8 scripts\run_judge.py %*
) else (
    echo Running Judge Simulator using system python...
    python -X utf8 scripts\run_judge.py %*
)
