# Starts backend (port 8000) and frontend (port 5173) in two visible PowerShell windows, so startup errors stay visible.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
if (-not (Test-Path "$root\backend\.venv\Scripts\python.exe")) { throw "Run .\scripts\setup_windows.ps1 first." }
if (-not (Test-Path "$root\frontend\node_modules")) { throw "Run .\scripts\setup_windows.ps1 first." }

foreach ($port in 8000, 5173) {
  if (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue) { throw "Port $port is already in use. Close the other program or see 'Port conflicts' in README.md." }
}

Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$root\backend'; .\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$root\frontend'; npm run dev"

Write-Host "Dashboard : http://localhost:5173"
Write-Host "API docs  : http://localhost:8000/docs"
Write-Host "Stop both by closing the two new windows (or press Ctrl+C in each)."
