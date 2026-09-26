"""Embedded textures in PD model files (props P*, chars C*, guns G*).

modeldef (BE, pointers 0x05xxxxxx = file offset): numtexconfigs @0x16 (s16),
texconfigs @0x18. textureconfig (12 bytes): ptr, w, h, level, fmt(G_IM_FMT),
siz(G_IM_SIZ), s, t, unk. Embedded texel data is raw N64 format with the TMEM
odd-row swizzle (pairs of 32-bit words swapped on odd rows).
"""
import struct

import numpy as np

from cleanroom.gfx import texfmt

FMT_NAMES = {0: "rgba", 1: "yuv", 2: "ci", 3: "ia", 4: "i"}


def texconfigs(buf):
    if len(buf) < 0x1c:
        return []
    n = struct.unpack(">h", buf[0x16:0x18])[0]
    p = struct.unpack(">I", buf[0x18:0x1c])[0]
    if not n or (p & 0xff000000) != 0x05000000:
        return []
    base = p & 0xffffff
    out = []
    for i in range(n):
        o = base + 12 * i
        if o + 12 > len(buf):
            break
        ptr, w, h, lvl, fmt, siz, s, t, u = struct.unpack(">I8B", buf[o:o + 12])
        if (ptr & 0x0f000000) == 0x05000000:
            out.append(dict(index=i, ofs=ptr & 0xffffff, w=w, h=h, fmt=fmt, siz=siz, cfg=o))
    return out


def row_bytes(w, siz):
    return {0: ((w + 15) & ~15) >> 1, 1: (w + 7) & ~7, 2: ((w + 3) & ~3) * 2, 3: ((w + 3) & ~3) * 4}[siz]


def swizzle(data, w, h, siz):
    """TMEM odd-row swizzle as texSwizzleInternal (self-inverse)."""
    b = bytearray(data)
    rb = row_bytes(w, siz)
    step, half = (16, 8) if siz == 3 else (8, 4)
    for y in range(1, h, 2):
        r = y * rb
        for x in range(0, rb - step + 1, step):
            a = r + x
            if a + step > len(b):
                break
            b[a:a + half], b[a + half:a + step] = b[a + half:a + step], b[a:a + half]
    return bytes(b)


def size_bytes(w, h, siz):
    return row_bytes(w, siz) * h


def _tight(raw, w, h, siz):
    rb, tb = row_bytes(w, siz), (w * (4 << siz) + 7) // 8
    return b"".join(raw[y * rb:y * rb + tb] for y in range(h))


def _padded(tight, w, h, siz):
    rb, tb = row_bytes(w, siz), (w * (4 << siz) + 7) // 8
    return b"".join(tight[y * tb:(y + 1) * tb] + bytes(rb - tb) for y in range(h))


def decode(buf, tc):
    n = size_bytes(tc["w"], tc["h"], tc["siz"])
    raw = buf[tc["ofs"]:tc["ofs"] + n]
    if len(raw) < n or tc["fmt"] == 2:
        return None
    raw = swizzle(raw, tc["w"], tc["h"], tc["siz"])
    return texfmt.decode(_tight(raw, tc["w"], tc["h"], tc["siz"]), tc["w"], tc["h"], tc["fmt"], tc["siz"])


def encode(rgba, tc):
    raw = _padded(texfmt.encode(rgba, tc["fmt"], tc["siz"]), tc["w"], tc["h"], tc["siz"])
    return swizzle(raw, tc["w"], tc["h"], tc["siz"])
