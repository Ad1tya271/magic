@echo off
cd /d "%~dp0vera-bot"
.venv\Scripts\python.exe -X utf8 scripts/local_harness.py %*
