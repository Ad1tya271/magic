@echo off
cd /d "%~dp0vera-bot"
if exist ".venv\Scripts\python.exe" (
    .venv\Scripts\python.exe -X utf8 scripts\local_harness.py %*
) else (
    python -X utf8 scripts\local_harness.py %*
)
