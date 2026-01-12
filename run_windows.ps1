Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
  Write-Error "Python not found. Please install Python 3.12+ from https://www.python.org/downloads/ and retry."
}

if (-not (Test-Path ".venv")) {
  python -m venv .venv
}

& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
& .\.venv\Scripts\python.exe -m novelja

