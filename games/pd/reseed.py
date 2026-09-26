"""Taint veto loop for textures: re-roll the grain/palette-jitter seed of every texture the
scan flags, until the scan passes. Dirty-room tool (reads the ROM through the taint scan only).

    python -m games.pd.reseed <rom.z64> <pack> [rounds]
"""
import json
import os
import pickle
import sys

from cleanroom import taint
from games.pd import taint_report as tr, generate


def main(argv):
    rompath, pack = argv[:2]
    rounds = int(argv[2]) if len(argv) > 2 else 5
    rom = open(rompath, "rb").read()
    d = tr.textures(rom[0x1d65f40:0x1ff7ca0], rom[0x1ff7ca0:0x1ffea20])
    index = taint.build_index(s for _, s in d)
    P = lambda n: open(os.path.join(pack, "segs", n), "rb").read()
    rs = json.load(open(generate.RESEED)) if os.path.exists(generate.RESEED) else {}
    from games.pd.extract_kept import rom_files, unzip
    mf = [(n, b) for n, b in rom_files(rom) if os.path.basename(n)[:1] in "CGP" and b[:2] == b"s"]
    mindex = taint.build_index(s for _, s in tr.model_tex([(n, unzip(b)) for n, b in mf]))
    for r in range(rounds):
        c = tr.textures(P("texturesdata"), P("textureslist"))
        bad = [h[0][4:] for h in taint.scan(index, iter(c)) if h[3] >= taint.FAIL_RUN]
        mc = tr.model_tex([(n, unzip(open(os.path.join(pack, "files", n), "rb").read())) for n, _ in mf])
        bad += [h[0][4:] for h in taint.scan(mindex, iter(mc)) if h[3] >= taint.FAIL_RUN]
        print("round %d: %d failing" % (r, len(bad)), flush=True)
        if not bad:
            break
        for k in bad:
            rs[k] = rs.get(k, 0) + 1
        json.dump(rs, open(generate.RESEED, "w"), indent=0, sort_keys=True)
        generate.build_textures(pack, generate.hooks())
        generate.build_models(pack, generate.hooks())


if __name__ == "__main__":
    main(sys.argv[1:])
