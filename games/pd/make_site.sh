#!/bin/sh
# Assemble the web site: page + pd.js/pd.wasm + data package.
# usage: games/pd/make_site.sh <build_dir> <pack_dir> <site_dir>
# pack_dir holds filenames.lst, segs/, files/ (see dev_dump_pack.py for the layout).
B="$1"; P="$2"; S="$3"
HERE="$(cd "$(dirname "$0")" && pwd)"
export PATH="/e/n64web/emsdk/upstream/emscripten:/e/n64web/emsdk/upstream/bin:$PATH"
export EM_CACHE=E:/n64web/emcache EMSDK=E:/n64web/emsdk
mkdir -p "$S"
JS=$(ls "$B"/pd*.js | head -1); W="${JS%.js}.wasm"
cp "$JS" "$S/pd.js" && cp "$W" "$S/pd.wasm" || exit 1
# the js refers to its wasm by the original name
sed -i "s/$(basename "$W")/pd.wasm/g" "$S/pd.js"
python /e/n64web/emsdk/upstream/emscripten/tools/file_packager.py "$S/pd-data.data" \
  --preload "$P@/data" --js-output="$S/pd-data.js" --no-node --exclude '*.z64' > /dev/null || exit 1
python - "$HERE/web/shell.html" "$S/index.html" <<'PY'
import sys
s = open(sys.argv[1], encoding='utf-8').read()
s = (s.replace('{{TITLE}}', 'Perfect Dark (clean room)')
      .replace('{{ABOUT}}', 'Perfect Dark built from the decompilation for the browser, with regenerated assets.')
      .replace('{{CONTROLS}}', '<kbd>W</kbd><kbd>A</kbd><kbd>S</kbd><kbd>D</kbd> move &middot; mouse / arrows look &middot; '
               '<kbd>Click</kbd>/<kbd>Space</kbd> fire &middot; <kbd>Right click</kbd>/<kbd>Z</kbd> aim &middot; <kbd>E</kbd> use &middot; '
               '<kbd>R</kbd> reload &middot; <kbd>F</kbd> alt fire &middot; <kbd>Q</kbd> weapon menu &middot; <kbd>Tab</kbd> pause &middot; '
               '<kbd>Enter</kbd> accept &middot; gamepads work too')
      .replace('{{DATASCRIPT}}', 'pd-data.js').replace('{{SCRIPT}}', 'pd.js'))
open(sys.argv[2], 'w', encoding='utf-8', newline='\n').write(s)
PY
ls -la "$S" | awk 'NR>1 {print $5, $9}'
