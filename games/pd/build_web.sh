#!/bin/sh
# Build the Perfect Dark PC port for the web (Emscripten, WebGL2).
# usage: games/pd/build_web.sh <pcport_dir> <build_dir> [Release|RelWithDebInfo]
# Prints a summary; full log at <build_dir>/build_web.log
SRC="$1"; B="$2"; TYPE="${3:-Release}"
HERE="$(cd "$(dirname "$0")/../.." && pwd)"
(cd "$HERE" && python -m games.pd.port_patches "$SRC") || exit 1
export PATH="$HOME/bin:/e/n64web/emsdk/upstream/emscripten:/e/n64web/emsdk/upstream/bin:$PATH"
export EM_CACHE=E:/n64web/emcache EMSDK=E:/n64web/emsdk
mkdir -p "$B"
if [ ! -f "$B/CMakeCache.txt" ]; then
  emcmake.exe cmake -G Ninja -S "$SRC" -B "$B" -DCMAKE_BUILD_TYPE="$TYPE" -DPD_PYTHON=python "-DPD_OPT_LEVEL=${PD_OPT:--O2}" \
    "-DPD_WEB_LINK_FLAGS=${PD_WEB_LINK_FLAGS:-}" > "$B/build_web.log" 2>&1 || { tail -20 "$B/build_web.log"; exit 1; }
fi
cmake --build "$B" -j 12 >> "$B/build_web.log" 2>&1
rc=$?
echo "build rc=$rc"
grep -E "error:|Error " "$B/build_web.log" | sed -E 's/^[^ ]*:[0-9]+:[0-9]+: //' | sort | uniq -c | sort -rn | head -12
ls -la "$B"/pd*.js "$B"/pd*.wasm 2>/dev/null | awk '{print $5, $9}'
exit $rc
