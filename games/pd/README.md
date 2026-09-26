# Perfect Dark — clean room web build

Play: **https://andrewnakas.github.io/pd-cleanroom/**

Perfect Dark built from the [n64decomp](https://github.com/n64decomp/perfect_dark) /
[perfect-dark-pc-port](https://github.com/perfect-dark-pc-port/perfect_dark) source for the browser
(Emscripten + WebGL2), with **every asset the decomp extracts from a ROM regenerated**: textures,
textures inside models, fonts, sample banks, voice lines and the boot banner. No ROM is needed to play it.

Controls: `W A S D` move · mouse or arrow keys look · click / `Space` fire · right click / `Z` aim ·
`E` use · `R` reload · `F` alt fire · `Q` weapon menu · `Tab` pause · `Enter` accept · gamepads work too.

## What is kept, what is generated

The port loads all game data at runtime from ROM segments and files, and accepts external replacements
for each. This project reads the ROM **once, in a dirty-room step**, keeps only coarse facts, and builds a
data pack (`filenames.lst`, `segs/`, `files/`) from those facts.

| Data | Kept fact | Generated |
|---|---|---|
| Textures (3503) | format, size, LOD count, palette size, a 4×4 colour grid (16×16 for ≥128 px), a 2-bit alpha outline | colour from the grid plus our own detail, re-encoded in the game's texture container |
| Textures inside models (481) | the same, plus where they sit in the model file | the same |
| Signs with words (SECTOR ONE…, RESTRICTED, POLICE, SECURITY…) | the words | re-typeset with an original stroke font (`tex_labels.json`) |
| Heads (180 textures: faces, ears, hair) | kind (front/side/back), a few feature rows, average colours | painted procedurally (`faces.py`, `face_briefs.json`) |
| Mission pictures (menu thumbnails) | — | rendered by the clean build itself from each level's geometry (`pictures.py`) |
| Controller diagram, boot banner | alpha outline | drawn (`drawn.py`) — no third-party logos |
| Fonts (6 in-game fonts) | glyph boxes, baselines, kerning table | every glyph drawn with the stroke font |
| Sample banks (961 waves) | length, rate, loop points, a coarse spectral outline, median pitch | resynthesised; our own VADPCM codebooks with the retail predictor count, so bank sizes are exact |
| Voice lines (548 MP3s) | the words, length, one median pitch | placeholder TTS character voices (Piper), to be replaced by the author's own performances |
| Geometry, level/prop models, setups, collision, text, animations, note sequences | kept as in the decomp | — |

`taint_report.py` decodes every regenerated asset (pixels, glyph bits, PCM) and compares it with the retail
extraction for shared byte runs of 32 bytes or more: **0 failing**. For 16-colour textures, where short
colour runs can coincide by chance, the generator re-rolls its grain seed for any flagged texture
(`reseed.py`); the scan only vetoes, nothing retail flows into the output.

## Build (Windows, Git Bash)

Needs Python 3 (numpy, scipy, librosa, av, piper-tts, faster-whisper), CMake, Zig (host harness), emsdk.

```sh
# dirty room, once: needs your own ROM (ntsc-final), never published
python -m games.pd.extract_kept   pd.ntsc-final.z64 games/pd/spec      # layout + kept facts (local only)
ROMID=ntsc-final python pcport/tools/extract                           # decomp extractor into a dirty dir
python -m games.pd.extract_spec   <dirty>/src/assets/ntsc-final texdump.bin games/pd/spec
python -m games.pd.extract_spec   audio <dirty>/src/assets/ntsc-final games/pd/spec
python -m games.pd.extract_faces  games/pd/spec
python -m games.pd.extract_voices <dirty>/src/assets/ntsc-final/files/audio games/pd/spec

# clean room: from the spec only
python -m games.pd.voices build
python -m games.pd.generate pack
games/pd/build_web.sh pcport build/web        # applies port_patches.py, emcmake, make
games/pd/make_site.sh build/web pack site
python -m games.pd.taint_report pd.ntsc-final.z64 pack    # optional check
```

`port_patches.py` lists every source change to the port (web platform, WebGL2 context, ASYNCIFY frame
pacing, optional ROM, file loading fixes).

Voice recording: `python -m games.pd.practice build ...` makes call-and-response practice tracks from your
own ROM (personal use); `python -m games.pd.practice cut <recording> <character>` cuts your takes, which
then replace the placeholders.
