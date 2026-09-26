"""Drawn images for Perfect Dark: boot banner, text-bearing textures (re-typeset
from tex_labels.json), faces (face_briefs.json via facepaint) and HUD/menu icons.
Every hook returns RGBA uint8 at the slot size, or None to fall back to the
colour grid.
"""
import json
import os

import numpy as np

from cleanroom.gfx import strokefont

HERE = os.path.dirname(os.path.abspath(__file__))


def rgba16_bytes(img):
    r, g, b, a = [img[..., i].astype(np.uint16) for i in range(4)]
    v = ((r >> 3) << 11) | ((g >> 3) << 6) | ((b >> 3) << 1) | (a >= 128)
    return v.astype(">u2").tobytes()


def boot_banner(lines, w=507, h=48):
    """Boot/copyright strip: a plain rule, a generic emblem box and the words."""
    img = np.zeros((h, w, 4), np.uint8)
    img[..., 3] = 255
    col = np.array([110, 110, 235], np.float32)
    img[2:4, :, :3] = (70, 70, 170)
    # emblem: an outlined rounded square with a stylised "PD" monogram (our own)
    box = np.zeros((h, 34), np.float32)
    box[8:44, 2:32] = 1
    box[10:42, 4:30] = 0
    mono = strokefont.render_line("PD", 18, thickness=1.4)
    mh, mw = mono.shape
    box[17:17 + mh, 17 - mw // 2:17 - mw // 2 + mw] = np.maximum(box[17:17 + mh, 17 - mw // 2:17 - mw // 2 + mw], mono[:, :min(mw, 34)])
    img[:, 4:38, :3] = np.clip(box[..., None] * 230, 0, 255).astype(np.uint8)
    y = 8
    for i, text in enumerate(lines):
        th = 20 if i == 0 else 14
        m = strokefont.render_line(text, th, thickness=1.3 if i == 0 else 1.0)
        m = m[:, :w - 44]
        img[y:y + m.shape[0], 40:40 + m.shape[1], :3] = np.maximum(
            img[y:y + m.shape[0], 40:40 + m.shape[1], :3], (m[..., None] * col).astype(np.uint8))
        y += th + 2
    return img


# --------------------------------------------------------------- texture hook

_labels = None


def _load():
    global _labels
    if _labels is None:
        p = os.path.join(HERE, "tex_labels.json")
        _labels = {k: v for k, v in json.load(open(p)).items() if not k.startswith("_")} if os.path.exists(p) else {}
    return _labels


def texture_hook(key, d):
    from games.pd import pictures
    img = pictures.hook(key, d)
    if img is None:
        img = pad_hook(key, d)
    if img is not None:
        return img
    lab = _load().get(key)
    if lab:
        from games.pd import labels
        return labels.render(lab, d)
    try:
        from games.pd import faces
        img = faces.render(key, d)
        if img is not None:
            return img
    except ImportError:
        pass
    return None


# --------------------------------------------------------------- controller diagram
# Control-setup screen: a 64x64 pad drawing split into four 32x32 RGBA32 textures.
# Silhouette = kept alpha outline; buttons drawn here (positions written from one look).
PAD_KEYS = {"0da0": (0, 0), "0da1": (0, 32), "0da2": (32, 0), "0da3": (32, 32)}


def _disc(img, cy, cx, r, col, shade=True):
    yy, xx = np.mgrid[0:img.shape[0], 0:img.shape[1]].astype(np.float32) + 0.5
    d = np.hypot(yy - cy, xx - cx)
    m = np.clip(r + 0.5 - d, 0, 1)
    c = np.asarray(col, np.float32)
    if shade:
        hl = np.clip(1 - np.hypot(yy - (cy - r * 0.4), xx - (cx - r * 0.4)) / r, 0, 1)
        c = c[None, None] * (0.8 + 0.5 * hl[..., None])
    img[..., :3] = img[..., :3] * (1 - m[..., None]) + c * m[..., None]
    img[..., 3] = np.maximum(img[..., 3], m * 255)


def _pad(spec):
    from cleanroom.decomp.gen import from_digest
    img = np.zeros((64, 64, 4), np.float32)
    for k, (y, x) in PAD_KEYS.items():
        img[y:y + 32, x:x + 32] = from_digest("pad/" + k, spec[k])
    body = img[..., 3] > 40
    img[..., :3] = np.where(body[..., None], img[..., :3] * 0.35 + np.array([30, 70, 85]) * 0.65, img[..., :3])
    # outline: body pixels next to the outside
    edge = body & ~(np.roll(body, 1, 0) & np.roll(body, -1, 0) & np.roll(body, 1, 1) & np.roll(body, -1, 1))
    img[edge, :3] = (60, 190, 200)
    img[edge, 3] = 255
    # d-pad
    for dy, dx, h, w in ((12, 12, 7, 2), (12, 12, 2, 7)):
        img[dy - h // 2:dy - h // 2 + h + 1, dx - w // 2:dx - w // 2 + w + 1, :3] = (120, 120, 130)
    _disc(img, 1.5, 30.5, 2.2, (200, 200, 205))        # stick
    _disc(img, 8, 31, 2.0, (220, 30, 30))              # start
    _disc(img, 4, 48, 2.2, (30, 40, 220))              # A
    _disc(img, 9.5, 43.5, 2.0, (30, 190, 40))          # B
    for cy, cx in ((8.5, 53), (12, 49.5), (12, 56.5), (15.5, 53)):
        _disc(img, cy, cx, 1.6, (240, 220, 20))        # C buttons
    img[21:24, 26:39, :3] = (50, 120, 140)             # centre grip slot
    img[21:24, 26:39, 3] = 255
    _disc(img, 62.5, 30.5, 2.0, (200, 200, 205))       # Z trigger (underside)
    return np.clip(img, 0, 255).astype(np.uint8)


_PAD = {}


def pad_hook(key, d):
    if key not in PAD_KEYS:
        return None
    if "img" not in _PAD:
        spec = json.load(open(os.path.join(HERE, "spec", "textures.json")))
        _PAD["img"] = _pad(spec)
    y, x = PAD_KEYS[key]
    return _PAD["img"][y:y + 32, x:x + 32].copy()
