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
- (nothing yet)

## Next
- Emscripten build of the port (dev test uses a local ROM, never published)
- Dirty spec, texture codec, generator, taint

## For the morning
- (tbd)
