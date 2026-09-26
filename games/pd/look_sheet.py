"""DIRTY ROOM (local only): labelled contact sheets of decoded retail textures
for transcription (tex_labels.json) and face briefs. Output never published.

    python -m games.pd.look_sheet text <out.png> [N]        top-N text-like textures
    python -m games.pd.look_sheet keys <out.png> k1,k2,...  given texture keys (hex, or model#i)
    python -m games.pd.look_sheet range <out.png> a-b       texture numbers a..b (hex)
"""
import pickle
import sys

import numpy as np

from cleanroom.find_text import text_score
from cleanroom.gfx import png, strokefont

DIRTY = "D:/n64work/pd/gen/texdirty.pkl"


def label(img, text, x, y, h=9):
    m = strokefont.render_line(text, h, thickness=0.8)
    hh, ww = m.shape
    ww = min(ww, img.shape[1] - x)
    hh = min(hh, img.shape[0] - y)
    img[y:y + hh, x:x + ww] = np.maximum(img[y:y + hh, x:x + ww], (m[:hh, :ww, None] * 255).astype(np.uint8))


def sheet(items, out, scale=3, width=1800):
    x = y = rowh = 0
    tiles = []
    for key, im in items:
        s = scale if max(im.shape[:2]) * scale <= 256 else max(1, 256 // max(im.shape[:2]))
        big = np.repeat(np.repeat(im, s, 0), s, 1)
        hh, ww = big.shape[:2]
        ww2 = max(ww, 8 * len(key))
        if x and x + ww2 > width:
            x, y, rowh = 0, y + rowh + 14, 0
        tiles.append((x, y, big, key))
        x += ww2 + 8
        rowh = max(rowh, hh)
    img = np.zeros((y + rowh + 14, width, 3), np.uint8)
    img[...] = (0, 50, 80)
    for x0, y0, big, key in tiles:
        hh, ww = big.shape[:2]
        a = big[..., 3:4].astype(np.float32) / 255
        chk = np.where(((np.indices((hh, ww)).sum(0) // 6) % 2)[..., None], 70, 110)
        img[y0:y0 + hh, x0:x0 + ww] = (big[..., :3] * a + chk * (1 - a)).astype(np.uint8)
        label(img, key, x0, y0 + hh + 2)
    png.write(out, img)


def models():
    import json, os
    from games.pd import pdmodel
    root = "D:/n64work/pd/dirty/src/assets/ntsc-final/files"
    out = {}
    for sub in ("chrs", "props", "guns"):
        for f in sorted(os.listdir(os.path.join(root, sub))):
            b = open(os.path.join(root, sub, f), "rb").read()
            for t in pdmodel.texconfigs(b):
                im = pdmodel.decode(b, t)
                if im is not None:
                    out["%s/%s#%d" % (sub, f[:-4], t["index"])] = im
    return out


def main(argv):
    mode, out = argv[:2]
    res = pickle.load(open(DIRTY, "rb"))
    tex = {"%04x" % k: v["rgba"] for k, v in res.items() if v}
    if mode == "text":
        n = int(argv[2]) if len(argv) > 2 else 200
        ranked = sorted(tex.items(), key=lambda kv: -text_score(kv[1]))[:n]
        sheet(sorted(ranked), out)
    elif mode == "keys":
        allt = dict(tex)
        if "#" in argv[2]:
            allt.update(models())
        sheet([(k, allt[k]) for k in argv[2].split(",") if k in allt], out)
    elif mode == "range":
        a, b = [int(x, 16) for x in argv[2].split("-")]
        sheet([(k, v) for k, v in sorted(tex.items()) if a <= int(k, 16) <= b], out)
    elif mode == "models":
        sheet(sorted(models().items()), out, scale=2)


if __name__ == "__main__":
    main(sys.argv[1:])
