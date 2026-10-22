#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
(cd web && npm run build -- --base=/dwg-3d-viewer/)
mkdir -p docs
cp -a web/dist/. docs/
touch docs/.nojekyll
cp web/node_modules/three/LICENSE docs/THIRD_PARTY_NOTICES.txt
