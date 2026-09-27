$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location "$root\vera-bot"
$python = if (Test-Path ".\.venv\Scripts\python.exe") { ".\.venv\Scripts\python.exe" } else { "python" }
Write-Host "Running Judge Simulator using $python..." -ForegroundColor Cyan
& $python -X utf8 scripts/run_judge.py $args
