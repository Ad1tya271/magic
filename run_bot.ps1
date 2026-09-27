$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location "$root\vera-bot"
Write-Host "Starting Vera Bot on port 8000..." -ForegroundColor Cyan
& ".\.venv\Scripts\uvicorn.exe" bot:app --host 0.0.0.0 --port 8000
