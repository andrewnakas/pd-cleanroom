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
