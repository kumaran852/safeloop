# SAFELOOP one-time setup (Windows 11, PowerShell). Run from the project root:  .\scripts\setup_windows.ps1
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

foreach ($cmd in "python", "node", "npm") {
  if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) { throw "$cmd was not found on PATH. Install Python 3.11+ and Node.js 18+ first (see README)." }
}
python --version; node --version

Set-Location "$root\backend"
if (-not (Test-Path ".venv")) { python -m venv .venv }
& ".\.venv\Scripts\python.exe" -m pip install --upgrade pip
& ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw "Backend dependency install failed." }

Set-Location "$root\frontend"
npm install
if ($LASTEXITCODE -ne 0) { throw "npm install failed." }

Write-Host "`nSetup complete. Start with:  .\scripts\start_windows.ps1" -ForegroundColor Green
