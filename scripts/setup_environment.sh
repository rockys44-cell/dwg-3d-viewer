#!/usr/bin/env bash
set -euo pipefail
cd /workspace/dwg-3d-viewer
export XDG_CACHE_HOME=/workspace/.cache
mkdir -p "$XDG_CACHE_HOME" logs
python3 -m venv --system-site-packages /workspace/.venvs/dwg-viewer
source /workspace/.venvs/dwg-viewer/bin/activate
python -m pip install --cache-dir /workspace/.cache/pip -r requirements.txt
./scripts/install_converter.sh
if [[ ! -s converted.dxf ]]; then ./scripts/convert.sh; fi
if [[ ! -s analysis/entities.json || converted.dxf -nt analysis/entities.json ]]; then python scripts/analyze_drawing.py; fi
if [[ ! -s web/public/drawing.json || ! -s web/public/geometry.bin || converted.dxf -nt web/public/drawing.json || scripts/build_scene.py -nt web/public/drawing.json ]]; then python scripts/build_scene.py; fi
python scripts/validate_analysis.py
python scripts/write_report.py
cd web
npm ci --cache /workspace/.cache/npm --no-audit --no-fund
npm run build
