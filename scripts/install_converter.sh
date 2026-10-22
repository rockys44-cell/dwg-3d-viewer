#!/usr/bin/env bash
set -euo pipefail
tools=${DWG_TOOLS_DIR:-/workspace/tools}
mkdir -p "$tools"
cd "$tools"
archive=libredwg-0.13.4.tar.xz
if [[ ! -f "$archive" ]]; then
  curl -fL --retry 2 "https://github.com/LibreDWG/libredwg/releases/download/0.13.4/$archive" -o "$archive"
fi
echo "7e153ea4dac4cbf3dc9c50b9ef7a5604e09cdd4c5520bcf8017877bbe1422cd5  $archive" | sha256sum -c -
if [[ ! -d libredwg-0.13.4 ]]; then tar -xf "$archive"; fi
cd libredwg-0.13.4
if [[ ! -f Makefile ]]; then ./configure --prefix="$tools/libredwg" --disable-python --disable-bindings --disable-shared; fi
make -j4
./programs/dwg2dxf --version
