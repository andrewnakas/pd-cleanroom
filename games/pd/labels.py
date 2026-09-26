"""Re-typeset text-bearing textures (tex_labels.json) with the stroke font."""
import numpy as np

from cleanroom.decomp.gen import from_digest
from cleanroom.gfx import strokefont


def _fit(text, w, h):
    lines = text.split("|")
    lh = max(5, (h - 2) // len(lines))
    out = np.zeros((h, w), np.float32)
    y = (h - lh * len(lines)) // 2
    for ln in lines:
        th = max(0.7, lh * 0.11)
        m = strokefont.render_line(ln, lh, thickness=th)
        if m.shape[1] > w - 2:   # squeeze horizontally to fit
            xs = np.linspace(0, m.shape[1] - 1, w - 2).astype(int)
            m = m[:, xs]
        x = (w - m.shape[1]) // 2
        out[y:y + lh, x:x + m.shape[1]] = np.maximum(out[y:y + lh, x:x + m.shape[1]], m[:lh])
        y += lh
    return out


def render(lab, d):
    w, h = d["w"], d["h"]
    m = _fit(lab["text"], w, h)
    ink = np.asarray(lab.get("ink", [255, 255, 255]), np.float32)
    if lab.get("bg") is None:
        img = np.zeros((h, w, 4), np.float32)
        img[..., :3] = ink
        img[..., 3] = m * 255
    else:
        img = from_digest("label", d).astype(np.float32)
        img[..., :3] = np.asarray(lab["bg"], np.float32) * 0.8 + img[..., :3] * 0.2
        img[..., 3] = 255
        if lab.get("band"):
            img[:3, :, :3] = lab["band"]
            img[-3:, :, :3] = lab["band"]
        img[..., :3] = img[..., :3] * (1 - m[..., None]) + ink * m[..., None]
    img = np.clip(img, 0, 255).astype(np.uint8)
    return img[::-1].copy() if lab.get("flip_v") else img
