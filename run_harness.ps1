$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location "$root\vera-bot"
& ".\.venv\Scripts\python.exe" -X utf8 scripts/local_harness.py $args
