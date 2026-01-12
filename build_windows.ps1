Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host "== novelja Windows build =="

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
  Write-Error "Python not found. Please install Python 3.12+ from https://www.python.org/downloads/ and retry."
}

python --version

# Create venv if missing
if (-not (Test-Path ".venv")) {
  python -m venv .venv
}

& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt

# Build a one-folder app (more reliable for Qt)
& .\.venv\Scripts\python.exe -m PyInstaller `
  --noconfirm `
  --clean `
  --name "novelja" `
  --windowed `
  "novelja\__main__.py"

Write-Host "Build complete: dist\novelja\"

