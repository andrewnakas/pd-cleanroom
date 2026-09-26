"""Mission-select pictures (56x36 RGBA16, textures 0x385, 0x617-0x626, 0xb4f-0xb52):
rendered by the CLEAN web build itself (its own level geometry with our textures),
booted straight into each stage headless; the best frame is cropped and shrunk.

    python -m games.pd.pictures <site url> [tex,...]   -> games/pd/pictures/<tex>.png
(serve the clean site first: python ports/wasm/serve.py <site> <port>)
"""
import os
import subprocess
import sys

import numpy as np

from cleanroom.gfx import png

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "pictures")
ROOT = os.path.dirname(os.path.dirname(HERE))

# solo mission order = g_TexGeneralConfigs[13..33] (filemgr: texturenum = stage + 12)
MISSIONS = [("0385", 0x30), ("0617", 0x33), ("0618", 0x22), ("0619", 0x2c), ("061a", 0x1d), ("061b", 0x1e),
            ("061c", 0x2f), ("061d", 0x35), ("061e", 0x19), ("061f", 0x27), ("0620", 0x31), ("0621", 0x1c),
            ("0622", 0x21), ("0623", 0x38), ("0624", 0x2d), ("0625", 0x34), ("0626", 0x2a), ("0b4f", 0x37),
            ("0b52", 0x09), ("0b50", 0x16), ("0b51", 0x4f)]
SECS = [6, 9, 12, 15]


def shrink(img, w=56, h=36):
    H, W = img.shape[:2]
    # crop the centre to the slot aspect, box-filter down
    ar = w / h
    if W / H > ar:
        cw = int(H * ar)
        img = img[:, (W - cw) // 2:(W - cw) // 2 + cw]
    else:
        ch = int(W / ar)
        img = img[(H - ch) // 2:(H - ch) // 2 + ch]
    H, W = img.shape[:2]
    ys = (np.arange(h + 1) * H / h).astype(int)
    xs = (np.arange(w + 1) * W / w).astype(int)
    out = np.zeros((h, w, 3), np.float32)
    f = img[..., :3].astype(np.float32)
    for y in range(h):
        for x in range(w):
            out[y, x] = f[ys[y]:ys[y + 1], xs[x]:xs[x + 1]].reshape(-1, 3).mean(0)
    return np.clip(out * 1.15, 0, 255).astype(np.uint8)       # thumbnails read better slightly brighter


def score(img):
    g = img[..., :3].astype(np.float32).mean(-1)
    return g.std() + 0.3 * g.mean() - (100 if g.mean() < 12 else 0)


def capture(url, tex, stage):
    out = os.path.join("D:/n64work/pd/shots/pics", tex)
    subprocess.run([sys.executable, os.path.join(ROOT, "ports", "wasm", "headless_shot.py"), out,
                    "--base", url, "--secs", ",".join(map(str, SECS)), "--webgl",
                    "--query", "args=--boot-stage%%20%d" % stage], check=False,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    shots = [os.path.join(out, f) for f in sorted(os.listdir(out)) if f.startswith("shot_") and f.endswith(".png")] \
        if os.path.isdir(out) else []
    if not shots:
        return None
    best = max((png.read(p) for p in shots), key=score)
    return shrink(best)


def main(argv):
    url = argv[0]
    only = set(argv[1].split(",")) if len(argv) > 1 else None
    os.makedirs(OUT, exist_ok=True)
    for tex, stage in MISSIONS:
        if only and tex not in only:
            continue
        img = capture(url, tex, stage)
        if img is None:
            print(tex, "no frame")
            continue
        rgba = np.concatenate([img, np.full(img.shape[:2] + (1,), 255, np.uint8)], -1)
        png.write(os.path.join(OUT, tex + ".png"), rgba)
        print(tex, "ok", flush=True)


def hook(key, d):
    p = os.path.join(OUT, key + ".png")
    if not os.path.exists(p):
        return None
    img = png.read(p)
    if img.shape[1] != d["w"] or img.shape[0] != d["h"]:
        return None
    if img.shape[2] == 3:
        img = np.concatenate([img, np.full(img.shape[:2] + (1,), 255, np.uint8)], -1)
    return img


if __name__ == "__main__":
    main(sys.argv[1:])
