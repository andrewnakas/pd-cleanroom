"""Perfect Dark fonts: keep the layout (kerning table, per-glyph box and
baseline, pixel offsets: all numbers), redraw every glyph with the project's
stroke font.

Segment = s32 kerning[13*13] + 94 x {u8 index, s8 baseline, u8 height, u8 width,
s32 kerningindex, u32 pixeldata} + pixel data. Glyph pixels are CI4, 16 texels
per row (8 bytes), drawn with an IA16 TLUT whose indices 0-8 are transparent
and 9-15 ramp up: index = 8 + coverage * 7. Char i is ASCII 0x21 + i.
"""
import struct

import numpy as np

from cleanroom.gfx import strokefont

HDR = 13 * 13 * 4
NCHARS = 94


def metrics(seg):
    out = []
    for i in range(NCHARS):
        idx, base, h, w, kern, ptr = struct.unpack(">BbBBiI", seg[HDR + 12 * i:HDR + 12 * i + 12])
        out.append(dict(ch=chr(0x21 + i), base=base, h=h, w=w, ptr=ptr))
    return out


def _line_metrics(ms):
    caps = [m for m in ms if m["ch"].isupper() and m["ptr"] and m["h"]]
    if not caps:
        caps = [m for m in ms if m["ptr"] and m["h"]]
    top = float(np.median([m["base"] for m in caps]))
    base = float(np.median([m["base"] + m["h"] for m in caps]))
    return top, base


def glyph_mask(m, top, base, bold=1.0, smallcaps=False):
    """Coverage (h, 16) for one glyph box, drawn in line coordinates."""
    h, w = m["h"], m["w"]
    out = np.zeros((h, 16), np.float32)
    ch = m["ch"]
    cap = max(1.0, base - top)
    if smallcaps and ch.islower():
        ch = ch.upper()  # small-caps font: lowercase slots hold capitals
    lines = strokefont.glyph(ch)
    if not lines or h == 0 or w == 0:
        return out
    sy = cap / 6.0
    th = max(0.45, min(cap * 0.085 * bold, 1.6))
    xs = [x for ln in lines for x, _ in ln]
    x0, x1 = min(xs), max(xs)
    span = x1 - x0
    room = max(0.5, w - 2 * th - 0.2)
    sx = min(sy * 0.95, room / span) if span > 0 else sy
    left = (w - span * sx) / 2 - x0 * sx
    # line coordinates -> glyph box rows: box row r is line y = m.base + r
    canvas = np.zeros((h, 16), np.float32)
    if ch.isalnum():
        strokefont._stroke(canvas, lines, left, top - m["base"], sx, sy, th)
    else:
        # punctuation: fit the design's own vertical extent into the box
        ys = [y for ln in lines for _, y in ln]
        y0, y1 = min(ys), max(ys)
        vs = min(sy, (h - 2 * th) / (y1 - y0)) if y1 > y0 else sy
        vs = max(vs, 0.01)
        oy = (h - (y1 - y0) * vs) / 2 - y0 * vs
        if span > 0:
            sx = min(sx, vs * 1.2) if y1 > y0 else sx
            left = (w - span * sx) / 2 - x0 * sx
        strokefont._stroke(canvas, lines, left, oy, sx, vs, th)
    out[:, :] = canvas
    out[:, w + 1:] = 0
    return out


def to_ci4(cov):
    c = np.clip(cov, 0, 1)
    idx = np.where(c < 0.08, 0, 8 + np.ceil(c * 7)).astype(np.uint8)
    return np.minimum(idx, 15)


def rebuild(seg):
    """Regenerated font segment of the same size and layout."""
    ms = metrics(seg)
    top, base = _line_metrics(ms)
    a = ms[ord("a") - 0x21]
    smallcaps = a["h"] >= 0.9 * (base - top)
    ptrs = sorted(m["ptr"] for m in ms if m["ptr"])
    pix0 = ptrs[0] if ptrs else len(seg)
    out = bytearray(seg[:pix0]) + bytearray(len(seg) - pix0)
    for m in ms:
        if not m["ptr"]:
            continue
        idx = to_ci4(glyph_mask(m, top, base, smallcaps=smallcaps))
        b = ((idx[:, 0::2] << 4) | idx[:, 1::2]).astype(np.uint8).tobytes()
        out[m["ptr"]:m["ptr"] + len(b)] = b
    return bytes(out)


def preview(seg, scale=2):
    """Grey preview of all glyphs laid out on their baselines (for sheets)."""
    ms = metrics(seg)
    rows = max(m["base"] + m["h"] for m in ms) + 2
    x, cols = 0, []
    for m in ms:
        if not m["ptr"]:
            continue
        cell = np.zeros((rows, m["w"] + 2), np.uint8)
        d = np.frombuffer(seg[m["ptr"]:m["ptr"] + 8 * m["h"]], np.uint8)
        nib = np.empty(len(d) * 2, np.uint8)
        nib[0::2], nib[1::2] = d >> 4, d & 15
        g = nib.reshape(-1, 16)[:, :m["w"] + 1]
        a = np.clip((g.astype(int) - 8) * 36, 0, 255).astype(np.uint8)
        y = max(0, m["base"])
        cell[y:y + a.shape[0], :a.shape[1]] = a[:rows - y, :cell.shape[1]]
        cols.append(cell)
    img = np.hstack(cols)
    return np.repeat(np.repeat(img, scale, 0), scale, 1)
