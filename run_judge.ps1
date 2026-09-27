$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location "$root\vera-bot"
Write-Host "Running Judge Simulator..." -ForegroundColor Cyan
& ".\.venv\Scripts\python.exe" -X utf8 scripts/run_judge.py $args
