#!/usr/bin/env bash
set -euo pipefail

python3 -m pip install -r requirements.txt

# Build a single-folder dist (more reliable for Qt)
python3 -m PyInstaller \
  --noconfirm \
  --clean \
  --name "novelja" \
  --windowed \
  -m novelja

echo "Build complete: dist/novelja/"

