"""DIRTY ROOM: ROM -> spec/kept (user-approved facts) + spec/models.json + spec/rom_layout.json.

Kept verbatim (decomp code/geometry/text, note sequences, motion data):
  files: bg geometry (*.seg), pads, tiles, setups (U*), text (L*), ob_mid
  segs:  animations, mpconfigs, mpstrings*, firingrange, sequences
Model files (C*, G*, P*): geometry kept, embedded texel bytes zeroed; their
format/size/grid/alpha2 go to models.json like every other texture.
Not kept: voice MP3s (A*), textures, fonts, sample banks, copyright images.

    python -m games.pd.extract_kept <rom.z64> <spec dir>

spec/kept is local only (gitignored): it is retail geometry, not ours to publish in the repo.
"""
import json
import os
import sys

import numpy as np

from cleanroom.decomp.spec import grid, alpha2
from games.pd import dev_dump_pack as ddp, pdmodel, pdtex

KEEP_SEGS = ("animations", "mpconfigs", "mpstringsE", "mpstringsJ", "mpstringsP", "mpstringsG", "mpstringsF",
             "mpstringsS", "mpstringsI", "firingrange", "sequences")


def rom_files(rom):
    data = ddp.rzip(rom[ddp.DATA_OFS:])
    offs, p = [], ddp.FILES_OFS
    while True:
        o = int.from_bytes(data[p:p + 4], "big")
        if o == 0 and offs:
            break
        offs.append(o)
        p += 4
    table = offs[-1]
    names, i = [], 4
    while True:
        o = int.from_bytes(rom[table + i:table + i + 4], "big")
        if o == 0:
            break
        a = table + o
        names.append(rom[a:rom.index(0, a)].decode())
        i += 4
    return [(n, rom[offs[k + 1]:offs[k + 2]]) for k, n in enumerate(names)]


# fonts packed after handelgothiclg inside its segment (ntsc-final ROM offsets)
SUBFONTS = {"fonthandelgothiclg": [0x8008e0, 0x803da0, 0x806ac0]}


def blank_font_seg(name, ofs, seg):
    """Kerning + glyph metrics kept (numbers); glyph pixels zeroed."""
    from games.pd import fonts
    starts = [s - ofs for s in SUBFONTS.get(name, [ofs])]
    out = bytearray(seg)
    for k, st in enumerate(starts):
        en = starts[k + 1] if k + 1 < len(starts) else len(seg)
        ms = fonts.metrics(seg[st:en])
        p0 = min(m["ptr"] for m in ms if m["ptr"])
        out[st + p0:en] = bytes(en - st - p0)
    return bytes(out)


def blank_ctl(ctl):
    """Bank structure kept; codebook coefficients and loop states zeroed."""
    import struct
    from games.pd import pdaudio
    out = bytearray(ctl)
    for wo, w in pdaudio.waves(ctl).items():
        n = w["order"] * w["npred"] * 8
        out[w["book_ofs"] + 8:w["book_ofs"] + 8 + 2 * n] = bytes(2 * n)
        if w["loop_ofs"]:
            out[w["loop_ofs"] + 12:w["loop_ofs"] + 44] = bytes(32)
    return bytes(out)


def unzip(blob):
    return pdtex.rzip_inflate(blob, 0)[0]


def main(argv):
    rompath, spec = argv[:2]
    romdata = os.path.join(os.path.dirname(__file__), "..", "..", "..", "pd", "pcport", "port", "src", "romdata.c")
    rom = open(rompath, "rb").read()
    kept = os.path.join(spec, "kept")
    os.makedirs(os.path.join(kept, "segs"), exist_ok=True)
    os.makedirs(os.path.join(kept, "files"), exist_ok=True)
    segs = ddp.seg_list(romdata)
    layout = {"segs": {}, "files": []}
    for i, (name, ofs, size) in enumerate(segs):
        if not ofs:
            continue
        if not size:
            size = (segs[i + 1][1] if i + 1 < len(segs) else len(rom)) - ofs
        layout["segs"][name] = {"ofs": ofs, "size": size}
        if name in KEEP_SEGS:
            open(os.path.join(kept, "segs", name), "wb").write(rom[ofs:ofs + size])
        elif name.startswith("font") and "jpn" not in name:
            open(os.path.join(kept, "segs", name), "wb").write(blank_font_seg(name, ofs, rom[ofs:ofs + size]))
        elif name in ("sfxctl", "seqctl"):
            open(os.path.join(kept, "segs", name), "wb").write(blank_ctl(rom[ofs:ofs + size]))
    models, counts = {}, {"kept": 0, "model": 0, "voice": 0, "other": 0}
    for name, blob in rom_files(rom):
        zipped = blob[:2] == b"\x11\x73"
        layout["files"].append({"name": name, "size": len(blob), "zipped": zipped})
        base = os.path.basename(name)
        path = os.path.join(kept, "files", name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        if base[:1] == "A":
            counts["voice"] += 1
            continue
        if base[:1] in "CGP" and zipped:
            raw = bytearray(unzip(blob))
            tcs = pdmodel.texconfigs(bytes(raw))
            facts = []
            lims = pdmodel.limits(bytes(raw), tcs)
            for tc, n in zip(tcs, lims):
                im = pdmodel.decode(bytes(raw), tc)
                f = {k: tc[k] for k in ("index", "ofs", "w", "h", "fmt", "siz")}
                f["len"] = n
                if im is not None:
                    g = 16 if max(tc["w"], tc["h"]) >= 128 else 4
                    f["grid"] = grid(im.astype(np.float32), g)
                    if (im[..., 3] < 250).any():
                        f["alpha2"] = alpha2(im[..., 3])
                raw[tc["ofs"]:tc["ofs"] + n] = bytes(min(n, len(raw) - tc["ofs"]))
                facts.append(f)
            if facts:
                models[name] = facts
            open(path, "wb").write(bytes(raw))
            counts["model"] += 1
            continue
        open(path, "wb").write(blob)
        counts["kept" if base[:1] in "UL" or name.endswith(".seg") or "pads" in name or "tiles" in name else "other"] += 1
    json.dump(models, open(os.path.join(spec, "models.json"), "w"), separators=(",", ":"))
    json.dump(layout, open(os.path.join(spec, "rom_layout.json"), "w"), indent=0)
    others = [f["name"] for f in layout["files"] if not (os.path.basename(f["name"])[:1] in "ACGPUL" or
              f["name"].endswith(".seg") or "pads" in f["name"] or "tiles" in f["name"])]
    print("segs %d (kept %d)  files %d  counts %s  models with embedded tex %d (%d tex)" % (
        len(layout["segs"]), len(KEEP_SEGS), len(layout["files"]), counts, len(models),
        sum(len(v) for v in models.values())))
    print("unclassified kept files:", others[:20])


if __name__ == "__main__":
    main(sys.argv[1:])
