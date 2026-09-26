"""Procedural head textures for Perfect Dark (32x64, stored upside down).

Drawn only from spec/faces.json (kind, a few feature rows, average colours) and
face_briefs.json traits. Painted upright, then flipped to the stored orientation.
"""
import json
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
_F = None


def _faces():
    global _F
    if _F is None:
        p = os.path.join(HERE, "spec", "faces.json")
        _F = json.load(open(p)) if os.path.exists(p) else {}
    return _F


def _ell(yy, xx, cy, cx, ry, rx):
    d = ((yy - cy) / ry) ** 2 + ((xx - cx) / rx) ** 2
    return np.clip(1.5 - d, 0, 1)   # soft-edged ellipse coverage


def _blend(img, m, col):
    m = m[..., None]
    img[..., :3] = img[..., :3] * (1 - m) + np.asarray(col, np.float32) * m


def _noise(seed, h, w, amt):
    rng = np.random.default_rng(seed)
    n = rng.standard_normal((h // 2 + 2, w // 2 + 2)).astype(np.float32)
    n = np.repeat(np.repeat(n, 2, 0), 2, 1)[:h, :w]
    return 1 + amt * n


def _hair_strands(seed, h, w):
    rng = np.random.default_rng(seed)
    v = rng.standard_normal(w).astype(np.float32)
    v = np.convolve(v, [0.25, 0.5, 0.25], "same")
    return 1 + 0.12 * v[None, :] * np.ones((h, 1), np.float32)


def render(key, d_tex):
    f = _faces().get(key)
    if not f:
        return None
    h, w = 64, 32
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32) + 0.5
    skin = np.asarray(f["skin"], np.float32)
    hair = np.asarray(f["hair"], np.float32)
    img = np.zeros((h, w, 4), np.float32)
    img[..., 3] = 255
    img[..., :3] = skin
    seed = int(key, 16)
    # head wraps round the model: darken toward the texture edges
    wrap = 1 - 0.28 * (np.abs(xx - w / 2) / (w / 2)) ** 2
    hy = f.get("hair_y", 52)
    hl = float(np.clip(63 - (hy if hy < 60 else 53), 7, 18))   # upright hairline row
    kind = f["kind"]
    if kind == "back":
        img[..., :3] = hair * _hair_strands(seed, h, w)[..., None]
        nape = np.clip((yy - 54) / 8, 0, 1)
        _blend(img, nape * 0.7, skin * 0.85)
    elif kind.startswith("side"):
        face_left = kind == "side_l"
        # hair over the crown and the back half
        back = (xx / w) if face_left else (1 - xx / w)
        hair_m = np.clip((hl + 12 - yy) / 3, 0, 1) + np.clip((back - 0.45) * 5, 0, 1) * np.clip((46 - yy) / 5, 0, 1)
        _blend(img, np.clip(hair_m, 0, 1), hair * 0.95)
        ex = w * (0.62 if face_left else 0.38)
        ey = 33.0
        ear = _ell(yy, xx, ey, ex, 6.5, 3.6)
        _blend(img, ear, skin * np.array([1.0, 0.86, 0.84]))
        inner = _ell(yy, xx, ey + 0.5, ex, 4.0, 1.6)
        _blend(img, inner * 0.6, skin * 0.62)
        # jaw line toward the face side
        jaw = np.clip(1 - np.abs(yy - (48 + (xx if face_left else w - xx) * 0.1)) / 1.5, 0, 1) * np.clip((0.5 - back) * 3, 0, 1)
        _blend(img, jaw * 0.35, skin * 0.7)
    else:
        ey, my = 63 - f["eye_y"], 63 - f["mouth_y"]
        by = 63 - f.get("brow_y", f["eye_y"] + 4)
        dx = float(np.clip(f.get("eye_dx", 7) - 1, 5.5, 7.5))
        # hair: crown plus sides down past the temples
        top = np.clip((hl - yy) / 2.5, 0, 1)
        sides = np.clip((np.abs(xx - w / 2) - (w / 2 - 3.5)) / 1.5, 0, 1) * np.clip((ey + 2 - yy) / 4, 0, 1)
        hair_m = np.clip(top + sides, 0, 1)
        _blend(img, hair_m, hair)
        # eye sockets
        for sx in (-1, 1):
            cx = w / 2 + sx * dx
            _blend(img, _ell(yy, xx, ey, cx, 2.6, 3.8) * 0.35, skin * 0.72)
        # brows
        brow_col = np.minimum(hair, skin) * 0.8
        for sx in (-1, 1):
            cx = w / 2 + sx * dx
            m = np.clip(1 - np.abs(yy - (by + 0.08 * (xx - cx) ** 2 * 0.3)) / 0.9, 0, 1) * (np.abs(xx - cx) < 3.6)
            _blend(img, m * 0.85, brow_col)
        # eyes: sclera, iris, pupil, lid
        eye_col = np.asarray(f.get("eye", [80, 60, 45]), np.float32)
        if eye_col.mean() < 50:
            eye_col = np.array([90, 65, 45], np.float32)
        for sx in (-1, 1):
            cx = w / 2 + sx * dx
            _blend(img, _ell(yy, xx, ey, cx, 1.5, 3.0), (225, 220, 212))
            _blend(img, _ell(yy, xx, ey, cx, 1.5, 1.5), eye_col * 0.8)
            _blend(img, _ell(yy, xx, ey, cx, 0.8, 0.8), (12, 10, 10))
            lid = np.clip(1 - np.abs(yy - (ey - 1.6)) / 0.8, 0, 1) * (np.abs(xx - cx) < 3.3)
            _blend(img, lid * 0.9, skin * 0.3)
            under = np.clip(1 - np.abs(yy - (ey + 1.8)) / 0.8, 0, 1) * (np.abs(xx - cx) < 2.6)
            _blend(img, under * 0.25, skin * 0.6)
        # nose: bridge shade, tip, nostrils
        ny = ey + (my - ey) * 0.62
        bridge = np.clip(1 - np.abs(xx - (w / 2 + 1.2)) / 0.8, 0, 1) * ((yy > ey + 1) & (yy < ny))
        _blend(img, bridge * 0.35, skin * 0.7)
        _blend(img, _ell(yy, xx, ny - 1, w / 2, 3.0, 1.6) * 0.35, np.minimum(skin * 1.18, 255))
        _blend(img, _ell(yy, xx, ny + 0.4, w / 2, 1.3, 2.6) * 0.3, skin * 0.8)
        for sx in (-1, 1):
            _blend(img, _ell(yy, xx, ny + 1.1, w / 2 + sx * 1.4, 0.45, 0.7) * 0.8, skin * 0.45)
        # mouth
        lip = np.asarray(f.get("lip", skin * [0.85, 0.6, 0.6]), np.float32)
        lip = skin * 0.4 + lip * 0.6
        lip = lip * np.array([1.05, 0.8, 0.8], np.float32)
        _blend(img, _ell(yy, xx, my - 0.6, w / 2, 1.0, 4.6), lip * 0.9)
        _blend(img, _ell(yy, xx, my + 0.9, w / 2, 1.2, 4.0), lip)
        if f.get("mouth") == "open":
            _blend(img, _ell(yy, xx, my, w / 2, 0.9, 3.0), (40, 20, 20))
        else:
            line = np.clip(1 - np.abs(yy - my) / 0.6, 0, 1) * (np.abs(xx - w / 2) < 4.6)
            _blend(img, line * 0.85, lip * 0.4)
        # chin and jaw shading
        _blend(img, _ell(yy, xx, my + 5.5, w / 2, 1.2, 4.5) * 0.25, skin * 0.75)
        if f.get("beard") and key in _briefs_traits():
            beard = np.clip((yy - (my - 3)) / 2, 0, 1) * np.clip((np.abs(xx - w / 2) - 1) / 1, 0.3, 1)
            _blend(img, beard * 0.8, hair * 0.9)
        if f.get("moustache"):
            _blend(img, _ell(yy, xx, my - 1.8, w / 2, 0.9, 4.0) * 0.9, hair * 0.9)
    img[..., :3] *= (wrap * _noise(seed, h, w, 0.035))[..., None]
    out = np.clip(img, 0, 255).astype(np.uint8)
    return out[::-1].copy()     # stored upside down


_T = None


def _briefs_traits():
    global _T
    if _T is None:
        _T = json.load(open(os.path.join(HERE, "face_briefs.json"))).get("traits", {})
    return _T
