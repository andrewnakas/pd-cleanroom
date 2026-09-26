"""DIRTY ROOM: head textures -> spec/faces.json (a coarse description only).

PD heads are 32x64 photo textures stored upside down (chin at the top row,
crown at the bottom). For each candidate we record:
  kind      front | side_l | side_r | back
  eye_y     row of the eye line (stored orientation), eye_dx half distance
  mouth_y   row of the mouth, brow_y, hair_y (first row where hair dominates)
  skin, hair, eye, lip   average colours of those regions (3 numbers each)
  beard     True if the chin/jaw area is hair-coloured
Everything drawn later comes from these few numbers (games/pd/faces.py).

    python -m games.pd.extract_faces <spec dir>
"""
import json
import os
import pickle
import sys

import numpy as np

DIRTY = "D:/n64work/pd/gen/texdirty.pkl"


def skin_mask(im):
    r, g, b = [im[..., i].astype(float) for i in range(3)]
    return (r > 90) & (g > 45) & (b > 25) & (r > g + 10) & (r > b + 18)


def candidates(res):
    out = []
    for k, v in sorted(res.items()):
        if not v:
            continue
        im = v["rgba"]
        if im.shape[:2] != (64, 32):
            continue
        s = skin_mask(im)
        if s.mean() > 0.15 and s[:30].mean() > 0.2:
            out.append(k)
    return out


def describe(im, kind=None):
    f = im[..., :3].astype(float)
    lum = f @ np.array([0.3, 0.59, 0.11])
    s = skin_mask(im)
    h, w = lum.shape
    sym = np.abs(lum - lum[:, ::-1]).mean() / (lum.std() + 1e-6)
    skin_cols = s.mean(0)
    left, right = skin_cols[:w // 2].mean(), skin_cols[w // 2:].mean()
    # hair line: first row (from the top = chin) below 30 where skin fraction drops under 0.35
    rows = s.mean(1)
    hair_y = next((y for y in range(24, h) if rows[y] < 0.3), h)
    d = {"skin": [int(v) for v in f[s].mean(0)] if s.any() else [200, 150, 120],
         "hair": [int(v) for v in f[56:].reshape(-1, 3).mean(0)],
         "hair_y": int(hair_y)}
    if kind == "back":
        d["kind"] = "back"
    elif kind == "front" or (kind is None and sym < 0.45 and s[:, 8:24].mean() > 0.35):
        d["kind"] = "front"
        # eyes: darkest symmetric pair in rows 26..46, columns 6..14 / 17..25
        band = lum[26:47]
        pair = band[:, 5:14].min(1) + band[:, 18:27].min(1)
        ey = 26 + int(np.argmin(pair))
        cols = lum[ey, 3:15]
        d["eye_y"] = ey
        d["eye_dx"] = int(16 - (3 + int(np.argmin(cols))))
        d["eye"] = [int(v) for v in f[ey, [16 - d["eye_dx"], 15 + d["eye_dx"]]].mean(0)]
        # mouth: reddest/darkest horizontal line in rows 6..22 near the centre
        red = f[6:23, 12:20, 0] - f[6:23, 12:20, 1]
        my = 6 + int(np.argmax(red.mean(1) - 0.3 * lum[6:23, 12:20].mean(1) / 10))
        d["mouth_y"] = my
        d["lip"] = [int(v) for v in f[my, 12:20].mean(0)]
        brow = lum[ey + 2:ey + 8, 6:26].mean(1)
        d["brow_y"] = ey + 2 + int(np.argmin(brow))
        jaw = s[0:8, 6:26].mean()
        d["beard"] = bool(jaw < 0.35)
    elif kind == "side" or abs(left - right) > 0.2:
        d["kind"] = "side_l" if left > right else "side_r"
    else:
        d["kind"] = "back" if s.mean() < 0.35 else "side_l"
    return d


def main(argv):
    spec = argv[0]
    res = pickle.load(open(DIRTY, "rb"))
    out = {}
    brief = json.load(open(os.path.join(os.path.dirname(__file__), "face_briefs.json")))
    kinds = {k: "front" for k in brief["front"]}
    kinds.update({k: "back" for k in brief["back"]})
    for k in candidates(res):
        key = "%04x" % k
        if key in brief["exclude"]:
            continue
        d = describe(res[k]["rgba"], kinds.get(key, "side"))
        if key in brief.get("traits", {}):
            d.update(brief["traits"][key])
        out[key] = d
    json.dump(out, open(os.path.join(spec, "faces.json"), "w"), indent=0)
    from collections import Counter
    print(len(out), Counter(v["kind"] for v in out.values()))


if __name__ == "__main__":
    main(sys.argv[1:])
