$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location "$root\vera-bot"
$python = if (Test-Path ".\.venv\Scripts\python.exe") { ".\.venv\Scripts\python.exe" } else { "python" }
Write-Host "Starting Vera Bot on port 8000 using $python..." -ForegroundColor Cyan
& $python -m uvicorn bot:app --host 0.0.0.0 --port 8000
