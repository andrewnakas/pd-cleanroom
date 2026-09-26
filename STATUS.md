# Perfect Dark clean room: status

## Decisions (log)
- 2026-09-25 22:50 **Web route = PC port (perfect-dark-pc-port/perfect_dark) + Emscripten** (playbook §4 route 1/2).
  Why: the port is plain C/C++ with SDL2 + a GLES3 path in fast3d (maps to WebGL2), 32-bit safe (i686 builds exist),
  MP3 via bundled minimp3, and it already loads *all* game data at runtime from ROM segments/files with
  per-file external overrides (`segs/<name>`, `files/<name>`, `filenames.lst`). So the clean deliverable is a
  data pack (no ROM) + one wasm build. No existing web fork found; we port it (SDL2 emscripten port, WebGL2, ASYNCIFY or main-loop callback).
- Work dirs: `D:/n64work/pd/{pcport,decomp,dirty,rom}`. Deleted non-ntsc-final asset trees (disk).

## Kept facts vs regenerated (plan)
| Data | Treatment |
|---|---|
| code, setups, pads, tiles (collision), lang text, mp strings, mp configs, firing range | kept (decomp text/geometry/code) |
| model + bg geometry (props/chrs/guns/bg files) | geometry kept; any embedded textures regenerated |
| animations segment | kept (motion data = geometry-like fact, like demo inputs) |
| note sequences | kept |
| textures segment (3503) | regenerated: format/size/4x4 grid/2-bit alpha kept |
| fonts | regenerated (stroke font) |
| sfx/seq sample banks | resynthesised from descriptors, own VADPCM books, bank sizes kept |
| voice MP3s (548 A* files) | placeholder Piper TTS, practice pack for the user |
| copyright / accessingpak images | redrawn |

## Works
- Dirty spec: textures (3503, decoded with the game's own decompressor in a host harness), 481 embedded model
  textures, fonts (metrics+kerning kept), sfx/seq banks (961 waves), 548 voice lines (Whisper words), heads (faces.json).
- Clean pack generator `python -m games.pd.generate <pack>`: textures (grid+alpha, re-encoded; round-trips through
  the game decompressor with 0 format/size mismatches), model textures, fonts (stroke font, all 6 in-game fonts
  readable), boot banner (own emblem, no Rare logo), audio banks (in-place: same wave sizes, own 4/1-predictor books).
- Readable signs re-typeset (`tex_labels.json`): SECTOR ONE..FOUR, RESTRICTED, HAZARDOUS, POLICE, SECURITY, SURROUND SOUND.
- Faces: 180 head textures (59 front, 8 back, rest ear-sides) painted procedurally (`faces.py`) from kind + a few feature rows.

## Decisions (cont.)
- PD ctl books are 4 predictors (a few 1): regenerate in place with the same predictor count per wave so bank
  sizes stay exact (playbook "2 predictors" rule generalised to "retail count").
- Voices: words from Whisper small.en on the dirty MP3s (facts: words, length, rate, median f0), Piper placeholders
  by character code (jo=Joanna, ca=Carrington, el=Elvis, ...), MP3 32 kbps 22.05 kHz mono without ID3/Xing.
- Dolby-style surround logo texture -> plain words "SURROUND SOUND" (no trademark art).

## Next
- Boot the clean pack in the browser; taint scan; publish
- Mission-select thumbnails (0x385, 0x617-0x626, 0x63c, 0xb4f-0xb52; 56x36): render from level geometry
- Controller diagram (0xda0-0xda3), radar (0x3c), menu icons: draw procedurally

## For the morning
- (tbd)

## Web build (agent)
- `games/pd/build_web.sh <pcport> <build>` (emcmake+ninja, -O2, ASYNCIFY, WebGL2) -> `make_site.sh <build> <pack> <site>` (file_packager `pd-data.data` mounted at /data, IDBFS /save). Patches: `port_patches.diff` (applied by `port_patches.py`).
- Pack layout: `filenames.lst` (names in file-number order, file 1 first), `files/<name>` (ROM-form, 1173-zipped where retail zips), `segs/<seg>` (all ROMSEG_LIST segs present in ntsc-final: 26). Dev pack via `dev_dump_pack.py` (dirty, never publish).
- Dev pack: boots intro -> title -> file select; `?args=--boot-stage%2048` plays Defection (move/turn/fire, guard AI, audio ok, no dropouts at 250 ms). 60 fps in headless SwiftShader in menus, ~30 fps in-level (GPU-bound in software GL; JS work ~4-8 ms/frame).
- Missing voice MP3s: mp3PlayFile skips romaddr 0 / size <= 0 (no crash).
- fileLoad (non-N64) inflates straight from the in-memory file (regenerated streams need not be in-place safe).
- Clean pack: level (Defection) plays; title path crashes in convertModel on `Pmisc_irspecsZ` (clean file differs at 0xc5e-0x133f, past the texture at 0xb40 -> probably overwrote model data). With that one file retail (dev test) the clean pack reaches the file-select menu.
