#!/bin/sh
# Copy the PD clean-room sources into a standalone repo dir (no ROM data, no kept retail files,
# no dirty caches). Usage: games/pd/export_repo.sh <repo dir>
R="$1"; mkdir -p "$R/games" "$R/ports/wasm"
copy_tree() { (cd "$1" && find . -type f ! -path "*/__pycache__/*" ! -name "*.pyc" ! -path "./spec/kept/*" \
  ! -name "voices.partial.jsonl" ! -path "./voices/_raw/*" ! -path "./takes/*") | while read f; do
  mkdir -p "$2/$(dirname "$f")"; cp "$1/$f" "$2/$f"; done; }
copy_tree cleanroom "$R/cleanroom"
copy_tree games/pd "$R/games/pd"
cp games/__init__.py "$R/games/"
cp ports/wasm/headless_shot.py ports/wasm/serve.py ports/wasm/cdp_stack.py "$R/ports/wasm/"
cp games/pd/README.md "$R/README.md"
printf '__pycache__/\n*.pyc\n*.z64\n*.n64\n*.v64\n*.zip\ngames/pd/spec/kept/\ngames/pd/takes/\n' > "$R/.gitignore"
echo "exported: $(find "$R" -type f ! -path "*/.git/*" | wc -l) files -> $R"
