@echo off
cd /d "%~dp0vera-bot"
echo Running Judge Simulator...
.venv\Scripts\python.exe -X utf8 scripts/run_judge.py %*
