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
