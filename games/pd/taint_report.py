"""Taint report: every regenerated asset of the clean pack, decoded to its
expressive form (RGBA pixels, glyph bits, PCM), vs the same from the retail ROM.
Shared runs >= taint.FAIL_RUN bytes fail. Kept facts (geometry, setups, text,
animations, note sequences) are listed, not scanned.

    python -m games.pd.taint_report <rom.z64> <pack dir>   (dirty room tool; prints a summary)
"""
import json
import os
import subprocess
import sys
import tempfile

import numpy as np

from cleanroom import taint
from games.pd import pdtex, pdmodel, pdaudio, fonts
from games.pd.extract_kept import rom_files, unzip, SUBFONTS
from games.pd import dev_dump_pack as ddp

HARNESS = "D:/n64work/pd/gen/texharness.exe"
HERE = os.path.dirname(os.path.abspath(__file__))


def textures(data, lst):
    """Decoded RGBA of every texture in a texturesdata/textureslist pair."""
    from games.pd.extract_spec import decode_all
    offs = [int.from_bytes(lst[i * 8 + 1:i * 8 + 4], "big") for i in range(len(lst) // 8)]
    with tempfile.TemporaryDirectory() as td:
        os.makedirs(os.path.join(td, "textures"))
        for n in range(len(offs) - 1):
            open(os.path.join(td, "textures", "%04x.bin" % n), "wb").write(data[offs[n]:offs[n + 1]])
        dump = os.path.join(td, "dump.bin")
        with open(dump, "wb") as f:
            subprocess.run([HARNESS, os.path.join(td, "textures"), "0", str(len(offs) - 1)], stdout=f, check=True)
        res = decode_all(td, dump)
    return [("tex/%04x" % k, v["rgba"].tobytes()) for k, v in sorted(res.items()) if v]


def model_tex(files):
    out = []
    for name, raw in files:
        for tc in pdmodel.texconfigs(raw):
            im = pdmodel.decode(raw, tc)
            if im is not None:
                out.append(("mdl/%s#%d" % (name, tc["index"]), im.tobytes()))
    return out


def glyphs(segs):
    out = []
    for name, (seg, ofs) in segs.items():
        starts = [s - ofs for s in SUBFONTS.get(name, [ofs])] + [len(seg)]
        for a, b in zip(starts, starts[1:]):
            sub = seg[a:b]
            ms = fonts.metrics(sub)
            p0 = min(m["ptr"] for m in ms if m["ptr"])
            out.append(("font/%s@%x" % (name, a), sub[p0:]))
    return out


def pcm_bank(ctl, tbl, tag):
    out = []
    for wo, w in pdaudio.waves(ctl).items():
        from cleanroom.audio import vadpcm
        pcm = vadpcm.decode(tbl[w["base"]:w["base"] + w["len"]], pdaudio.book_of(ctl, w))
        out.append(("%s/%x" % (tag, wo), pcm.astype("<i2").tobytes()))
    return out


def mp3_pcm(blob):
    import io, av
    ct = av.open(io.BytesIO(blob))
    s = ct.streams.audio[0]
    chunks = []
    for pkt in ct.demux(s):
        try:
            for fr in pkt.decode():
                chunks.append(fr.to_ndarray().ravel())
        except av.error.InvalidDataError:
            pass
    x = np.concatenate(chunks) if chunks else np.zeros(0, np.float32)
    return (np.clip(x, -1, 1) * 32767).astype("<i2").tobytes()


def main(argv):
    rompath, pack = argv[:2]
    rom = open(rompath, "rb").read()
    romdata = os.path.join(HERE, "..", "..", "..", "pd", "pcport", "port", "src", "romdata.c")
    segs = {}
    lay = ddp.seg_list(romdata)
    for i, (name, ofs, size) in enumerate(lay):
        if ofs:
            size = size or ((lay[i + 1][1] if i + 1 < len(lay) else len(rom)) - ofs)
            segs[name] = (rom[ofs:ofs + size], ofs)
    P = lambda n: open(os.path.join(pack, "segs", n), "rb").read()
    rfiles = rom_files(rom)
    groups = {}
    groups["textures"] = (textures(segs["texturesdata"][0], segs["textureslist"][0]),
                          textures(P("texturesdata"), P("textureslist")))
    mdl_names = [n for n, b in rfiles if os.path.basename(n)[:1] in "CGP" and b[:2] == b"\x11\x73"]
    groups["model textures"] = (model_tex([(n, unzip(b)) for n, b in rfiles if n in mdl_names]),
                                model_tex([(n, unzip(open(os.path.join(pack, "files", n), "rb").read()))
                                           for n in mdl_names if os.path.exists(os.path.join(pack, "files", n))]))
    fsegs = [n for n in segs if n.startswith("font") and "jpn" not in n]
    groups["font glyphs"] = (glyphs({n: segs[n] for n in fsegs}), glyphs({n: (P(n), segs[n][1]) for n in fsegs}))
    groups["jpn glyphs"] = ([(n, segs[n][0]) for n in segs if "jpn" in n], [(n, P(n)) for n in segs if "jpn" in n])
    groups["banner"] = ([("copyright", pdtex.rzip_inflate(segs["copyright"][0], 0)[0])],
                        [("copyright", pdtex.rzip_inflate(P("copyright"), 0)[0])])
    for bank, c, t in (("sfx", "sfxctl", "sfxtbl"), ("seq", "seqctl", "seqtbl")):
        groups[bank + " samples"] = (pcm_bank(segs[c][0], segs[t][0], bank), pcm_bank(P(c), P(t), bank))
    voice = [(n, b) for n, b in rfiles if os.path.basename(n)[:1] == "A"]
    have = [(n, open(os.path.join(pack, "files", n), "rb").read()) for n, _ in voice
            if os.path.exists(os.path.join(pack, "files", n))]
    groups["voices"] = ([(n, mp3_pcm(b)) for n, b in voice], [(n, mp3_pcm(b)) for n, b in have])
    total_bad = 0
    for g, (dirty, clean) in groups.items():
        index = taint.build_index(s for _, s in dirty)
        hits = taint.scan(index, iter(clean))
        bad = sorted((h for h in hits if h[3] >= taint.FAIL_RUN), key=lambda h: -h[3])
        total_bad += len(bad)
        print("%-15s %5d clean / %5d retail  %4d short matches  %d FAILING%s" % (
            g, len(clean), len(dirty), len(hits), len(bad),
            "  e.g. " + ", ".join("%s(%dB)" % (b[0], b[3]) for b in bad[:4]) if bad else ""))
    print("taint: %d failing (run >= %d B)" % (total_bad, taint.FAIL_RUN))
    return 1 if total_bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
