"""DIRTY ROOM: retail extraction -> games/pd/spec (coarse facts only).

    python -m games.pd.extract_spec <dirty assets dir> <texdump.bin> <spec dir> [--sheet out.png]

textures.json: per texture num: fmt, w, h, numlods, hasloddata, zlib, ncol,
grid (4x4, 16x16 when >= 128 px), alpha2 (2-bit alpha outline) when alpha varies.
The dirty RGBA is only held in memory (and in an optional local contact sheet).
"""
import json
import os
import struct
import sys

import numpy as np

from cleanroom.decomp.spec import grid, alpha2
from games.pd import pdtex


def read_dump(path):
    buf = open(path, "rb").read()
    pos, out = 0, {}
    while pos + 12 <= len(buf):
        rec = buf[pos:pos + 12]
        num = rec[0] | rec[1] << 8
        pos += 12
        if rec[2] == 0:
            out[num] = None
            continue
        nb = struct.unpack("<I", buf[pos:pos + 4])[0]
        pos += 4
        out[num] = dict(ok=rec[2], fmt=rec[3], w=rec[4], h=rec[5], numlods=rec[6], hasl=rec[7],
                        mem=buf[pos:pos + nb])
        pos += nb
    return out


def decode_all(assets, dump):
    texdir = os.path.join(assets, "textures")
    dumped = read_dump(dump)
    res = {}
    for fn in sorted(os.listdir(texdir)):
        num = int(fn[:4], 16)
        s = open(os.path.join(texdir, fn), "rb").read()
        if not s:
            res[num] = None
            continue
        if s[0] & 0x40:
            d = pdtex.decode_zlib(s)
            res[num] = dict(fmt=d["fmt"], w=d["w"], h=d["h"], numlods=d["numlods"], hasl=d["hasloddata"],
                            zlib=1, ncol=d["ncol"], rgba=d["rgba"], method=-1)
            continue
        d = dumped.get(num)
        if not d:
            res[num] = None
            continue
        method = s[3] & 15
        fmt = d["fmt"]
        mem = d["mem"]
        if fmt == pdtex.IA4 and method in (0, 1):
            fmt_dec = pdtex.I4  # same stride as I4 for the uncompressed path
            rgba = pdtex.decode_mem(mem, pdtex.I4, d["w"], d["h"])
            nib = rgba[..., 3] // 17
            rgba[..., :3] = ((nib >> 1) * 255 // 7)[..., None]
            rgba[..., 3] = np.where(nib & 1, 255, 0)
        else:
            rgba = pdtex.decode_mem(mem, fmt, d["w"], d["h"])
        res[num] = dict(fmt=fmt, w=d["w"], h=d["h"], numlods=d["numlods"], hasl=d["hasl"], zlib=0, ncol=0,
                        rgba=rgba, method=method)
    return res


def fact(t):
    rgba = t["rgba"]
    h, w = rgba.shape[:2]
    n = 16 if max(w, h) >= 128 else 4
    d = {"fmt": pdtex.NAMES[t["fmt"]], "w": w, "h": h, "numlods": t["numlods"], "hasloddata": t["hasl"],
         "zlib": t["zlib"], "grid": grid(rgba.astype(np.float32), n)}
    if t["ncol"]:
        d["ncol"] = t["ncol"]
    if (rgba[..., 3] < 250).any():
        d["alpha2"] = alpha2(rgba[..., 3])
    return d


def sheet(res, out, cell=40, cols=64):
    from cleanroom.gfx import png
    nums = sorted(k for k, v in res.items() if v)
    rows = (max(nums) + cols) // cols
    img = np.zeros((rows * cell, cols * cell, 3), np.uint8)
    img[..., :] = (60, 0, 60)
    for n in nums:
        rgba = res[n]["rgba"]
        h, w = rgba.shape[:2]
        s = max(1, max(w, h) // (cell - 2) + (max(w, h) % (cell - 2) > 0))
        t = rgba[::s, ::s]
        a = t[..., 3:4].astype(np.float32) / 255
        chk = np.where(((np.indices(t.shape[:2]).sum(0) // 4) % 2)[..., None], 90, 150)
        t = (t[..., :3] * a + chk * (1 - a)).astype(np.uint8)
        y, x = (n // cols) * cell + 1, (n % cols) * cell + 1
        img[y:y + t.shape[0], x:x + t.shape[1]] = t
    png.write(out, img)


def main(argv):
    assets, dump, spec = argv[:3]
    res = decode_all(assets, dump)
    os.makedirs(spec, exist_ok=True)
    facts = {"%04x" % k: (fact(v) if v else None) for k, v in sorted(res.items())}
    json.dump(facts, open(os.path.join(spec, "textures.json"), "w"), separators=(",", ":"))
    from collections import Counter
    c = Counter((pdtex.NAMES[v["fmt"]], v["zlib"], v["method"]) for v in res.values() if v)
    print("textures: %d decoded, %d empty" % (sum(1 for v in res.values() if v), sum(1 for v in res.values() if not v)))
    for k, n in sorted(c.items()):
        print("  %-9s zlib=%d method=%2d  %d" % (k + (n,)))
    if "--sheet" in argv:
        sheet(res, argv[argv.index("--sheet") + 1])
    if "--pickle" in argv:  # dirty cache for local sheets only
        import pickle
        pickle.dump(res, open(argv[argv.index("--pickle") + 1], "wb"))


if __name__ == "__main__":
    main(sys.argv[1:])
