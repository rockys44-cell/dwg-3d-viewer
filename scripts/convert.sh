#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p logs
converter=${DWG2DXF:-/workspace/tools/libredwg-0.13.4/programs/dwg2dxf}
if [[ ! -x "$converter" ]]; then
  echo 'LibreDWG dwg2dxf is missing. Run scripts/install_converter.sh first.' >&2
  exit 1
fi
"$converter" --version > logs/converter-version.txt
"$converter" -y -v1 -o converted.dxf '湖南宝峰配料工艺图T6.dwg' > logs/conversion.log 2>&1
XDG_CACHE_HOME=/workspace/.cache python3 scripts/inspect_dxf.py > logs/dxf-inventory.txt
