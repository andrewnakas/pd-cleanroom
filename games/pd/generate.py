"""CLEAN ROOM: games/pd/spec -> data pack for the web build (no ROM needed).

    python -m games.pd.generate <pack dir> [--only textures,fonts,audio,models,voices,kept]

Layout (what port/src/romdata.c loads without a ROM):
  filenames.lst, files/<name>, segs/<seg>
"""
import hashlib
import json
import os
import shutil
import sys
import time

import numpy as np

from cleanroom.decomp.gen import from_digest
from games.pd import pdtex, pdmodel, fonts, pdaudio

HERE = os.path.dirname(os.path.abspath(__file__))
SPEC = os.path.join(HERE, "spec")
KEPT = os.path.join(SPEC, "kept")
DECOMP_ASSETS = os.environ.get("PD_DECOMP_ASSETS", "D:/n64work/pd/pcport/src/assets/ntsc-final")
FMT = {n: i for i, n in enumerate(pdtex.NAMES)}


def h32(*parts):
    return int.from_bytes(hashlib.sha1("/".join(map(str, parts)).encode()).digest()[:4], "little")


def load(name):
    return json.load(open(os.path.join(SPEC, name)))


# ------------------------------------------------------------------ textures

def texture_rgba(key, d, hooks):
    for hook in hooks:
        img = hook(key, d)
        if img is not None:
            return np.asarray(img, np.uint8)
    return from_digest("tex/" + key, d)


def build_textures(pack, hooks=()):
    T = load("textures.json")
    data, lst = bytearray(), bytearray()
    rows = json.load(open(os.path.join(DECOMP_ASSETS, "textures.json")))   # decomp source: surface types
    flags = [((r["flag00"] & 15) << 4) | (r["surfacetype"] & 15) for r in rows]
    for num in range(len(T)):
        key = "%04x" % num
        d = T[key]
        f = flags[num] if flags else 0
        lst += bytes([f]) + len(data).to_bytes(3, "big") + bytes(4)
        if not d:
            continue
        rgba = texture_rgba(key, d, hooks)
        blob = pdtex.encode(rgba, FMT[d["fmt"]], d["numlods"], d.get("ncol"))
        data += blob
    lst += len(data).to_bytes(4, "big") + bytes(4)
    write(pack, "segs/texturesdata", bytes(data))
    write(pack, "segs/textureslist", bytes(lst))
    return len(T)


# ------------------------------------------------------------------ models

def build_models(pack, hooks=()):
    M = load("models.json")
    n = 0
    for name, facts in M.items():
        raw = bytearray(open(os.path.join(KEPT, "files", name), "rb").read())
        for f in facts:
            tc = dict(f)
            if "grid" not in f:
                continue
            key = "%s#%d" % (name, f["index"])
            rgba = texture_rgba(key, f, hooks)
            blob = pdmodel.encode(rgba, tc)
            raw[f["ofs"]:f["ofs"] + len(blob)] = blob[:len(raw) - f["ofs"]]
            n += 1
        write(pack, "files/" + name, pdtex.rzip_deflate(bytes(raw)))
    # model files without embedded textures: kept geometry, zipped as stored
    lay = load("rom_layout.json")
    for f in lay["files"]:
        base = os.path.basename(f["name"])
        if base[:1] in "CGP" and f["name"] not in M:
            raw = open(os.path.join(KEPT, "files", f["name"]), "rb").read()
            write(pack, "files/" + f["name"], pdtex.rzip_deflate(raw) if f["zipped"] else raw)
    return n


# ------------------------------------------------------------------ fonts

def build_fonts(pack):
    from games.pd.extract_kept import SUBFONTS
    lay = load("rom_layout.json")["segs"]
    n = 0
    for name in lay:
        if not name.startswith("font") or "jpn" in name:
            continue
        seg = open(os.path.join(KEPT, "segs", name), "rb").read()
        ofs = lay[name]["ofs"]
        starts = [s - ofs for s in SUBFONTS.get(name, [ofs])] + [len(seg)]
        out = b"".join(fonts.rebuild(seg[a:b]) for a, b in zip(starts, starts[1:]))
        write(pack, "segs/" + name, out)
        n += 1
    # Japanese glyph pages are not used by the English build: blank, same size
    for name in ("fontjpnsingle", "fontjpnmulti"):
        if name in lay:
            write(pack, "segs/" + name, bytes(lay[name]["size"]))
    return n


# ------------------------------------------------------------------ audio

def build_audio(pack, sample_hook=None):
    for bank, ctlseg, tblseg in (("sfx", "sfxctl", "sfxtbl"), ("seq", "seqctl", "seqtbl")):
        spec = load(bank + "_bank.json")
        ctl = open(os.path.join(KEPT, "segs", ctlseg), "rb").read()
        c, t = pdaudio.regenerate(ctl, spec["tbl_size"], spec["waves"], sample_hook, seed_prefix=bank)
        write(pack, "segs/" + ctlseg, c)
        write(pack, "segs/" + tblseg, t)
    return 2


# ------------------------------------------------------------------ misc images

def build_copyright(pack):
    from games.pd import drawn
    lay = load("rom_layout.json")["segs"]
    img = drawn.boot_banner(["Copyright Rare Ltd. 2000", "Published by Rareware."])
    z = pdtex.rzip_deflate(drawn.rgba16_bytes(img))
    size = lay["copyright"]["size"]
    write(pack, "segs/copyright", z + bytes(max(0, size - len(z))))   # external segs may differ in size
    return 1


# ------------------------------------------------------------------ kept + voices

def build_kept(pack):
    lay = load("rom_layout.json")
    n = 0
    for seg in os.listdir(os.path.join(KEPT, "segs")):
        if seg.startswith("font") or seg.endswith("ctl"):
            continue
        shutil.copyfile(os.path.join(KEPT, "segs", seg), os.path.join(pack, "segs", seg))
        n += 1
    for f in lay["files"]:
        base = os.path.basename(f["name"])
        if base[:1] in "ACGP":
            continue
        dst = os.path.join(pack, "files", f["name"])
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(os.path.join(KEPT, "files", f["name"]), dst)
        n += 1
    open(os.path.join(pack, "filenames.lst"), "w", newline="\n").write(
        "\n".join(f["name"] for f in lay["files"]) + "\n")
    return n


def build_voices(pack):
    from games.pd import voices
    return voices.write_pack(pack)


# ------------------------------------------------------------------

def write(pack, rel, data):
    p = os.path.join(pack, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "wb").write(data)


def hooks():
    out = []
    try:
        from games.pd import drawn
        out.append(drawn.texture_hook)
    except ImportError:
        pass
    return out


def main(argv):
    pack = argv[0]
    only = argv[argv.index("--only") + 1].split(",") if "--only" in argv else \
        ["kept", "textures", "models", "fonts", "audio", "copyright", "voices"]
    os.makedirs(os.path.join(pack, "segs"), exist_ok=True)
    os.makedirs(os.path.join(pack, "files"), exist_ok=True)
    hk = hooks()
    steps = {"kept": lambda: build_kept(pack), "textures": lambda: build_textures(pack, hk),
             "models": lambda: build_models(pack, hk), "fonts": lambda: build_fonts(pack),
             "audio": lambda: build_audio(pack), "copyright": lambda: build_copyright(pack),
             "voices": lambda: build_voices(pack)}
    for s in only:
        t = time.time()
        print("%-10s %6s  %.0fs" % (s, steps[s](), time.time() - t), flush=True)


if __name__ == "__main__":
    main(sys.argv[1:])
