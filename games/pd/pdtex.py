"""Perfect Dark texture container: decode (dirty room, via the game's own
decompressor harness for non-zlib streams) and encode (clean room).

Stream = 1 header byte (hasloddata<<7 | iszlib<<6 | numlods) + body.
  non-zlib body: per image  format:4 w:8 h:8 method:4  pixels...
  zlib body:     format:8 ncol-1:8 palette[ncol]:16  per image  w:8 h:8 rzip(indices)
In-memory pixel layout after decompression on a little-endian host (what the
harness dumps): RGBA32/RGB24 native u32 (R<<24|G<<16|B<<8|A), RGBA16/RGB15 BE16
5551, IA16 native u16 (I<<8|A), IA8 I4A4, I8, IA4 I3A1 nibbles, I4 nibbles.
"""
import struct
import zlib

import numpy as np

RGBA32, RGBA16, RGB24, RGB15, IA16, IA8, IA4, I8, I4, CI8_RGBA, CI4_RGBA, CI8_IA, CI4_IA = range(13)
NAMES = ["rgba32", "rgba16", "rgb24", "rgb15", "ia16", "ia8", "ia4", "i8", "i4",
         "ci8_rgba", "ci4_rgba", "ci8_ia", "ci4_ia"]


def _c5(v):
    return (v << 3) | (v >> 2)


def decode_mem(mem, fmt, w, h):
    """In-memory (harness) pixels of the first image -> RGBA uint8 (h, w, 4)."""
    out = np.zeros((h, w, 4), np.uint8)
    b = np.frombuffer(bytes(mem), np.uint8)
    if fmt in (RGBA32, RGB24):
        st = ((w + 3) & ~3) * 4
        for y in range(h):
            row = b[y * st: y * st + w * 4].reshape(w, 4)
            out[y] = row[:, ::-1]  # LE u32 of R,G,B,A
    elif fmt in (RGBA16, RGB15):
        st = ((w + 3) & ~3) * 2
        for y in range(h):
            v = b[y * st: y * st + w * 2].reshape(w, 2).astype(np.uint16)
            v = (v[:, 0] << 8) | v[:, 1]
            out[y, :, 0] = _c5((v >> 11) & 31)
            out[y, :, 1] = _c5((v >> 6) & 31)
            out[y, :, 2] = _c5((v >> 1) & 31)
            out[y, :, 3] = np.where(v & 1, 255, 0)
    elif fmt == IA16:
        st = ((w + 3) & ~3) * 2
        for y in range(h):
            v = b[y * st: y * st + w * 2].reshape(w, 2)
            out[y, :, :3] = v[:, 1:2]
            out[y, :, 3] = v[:, 0]
    elif fmt == IA8:
        st = (w + 7) & ~7
        for y in range(h):
            v = b[y * st: y * st + w]
            out[y, :, :3] = ((v >> 4) * 17)[:, None]
            out[y, :, 3] = (v & 15) * 17
    elif fmt == I8:
        st = (w + 7) & ~7
        for y in range(h):
            v = b[y * st: y * st + w]
            out[y, :, :3] = v[:, None]
            out[y, :, 3] = v
    elif fmt in (IA4, I4):
        st = ((w + 15) & ~15) >> 1
        if fmt == IA4:
            st = (w + 15) & ~15  # the channel path advances a full byte per texel here
        for y in range(h):
            row = b[y * st: y * st + (w + 1) // 2]
            nib = np.empty(len(row) * 2, np.uint8)
            nib[0::2], nib[1::2] = row >> 4, row & 15
            nib = nib[:w]
            if fmt == IA4:
                i = ((nib >> 1) * 255 // 7).astype(np.uint8)
                out[y, :, :3] = i[:, None]
                out[y, :, 3] = np.where(nib & 1, 255, 0)
            else:
                out[y, :, :3] = (nib * 17)[:, None]
                out[y, :, 3] = nib * 17
    return out


def pal_rgba(pal, fmt):
    p = np.asarray(pal, np.uint16)
    out = np.zeros((len(p), 4), np.uint8)
    if fmt in (CI8_RGBA, CI4_RGBA):
        out[:, 0], out[:, 1], out[:, 2] = _c5((p >> 11) & 31), _c5((p >> 6) & 31), _c5((p >> 1) & 31)
        out[:, 3] = np.where(p & 1, 255, 0)
    else:
        out[:, :3] = (p >> 8)[:, None]
        out[:, 3] = p & 255
    return out


def rzip_inflate(buf, pos):
    assert buf[pos:pos + 2] == b"\x11\x73", "not 1173"
    d = zlib.decompressobj(-15)
    data = d.decompress(buf[pos + 5:])
    return data, len(buf) - len(d.unused_data)


def rzip_deflate(data):
    c = zlib.compressobj(9, zlib.DEFLATED, -15)
    return b"\x11\x73" + len(data).to_bytes(3, "big") + c.compress(data) + c.flush()


def decode_zlib(stream):
    """Full zlib (paletted) texture -> dict with fmt, w, h, palette, indices, rgba."""
    hasl, nl = stream[0] >> 7, stream[0] & 0x3f
    fmt, ncol = stream[1], stream[2] + 1
    pal = struct.unpack(">%dH" % ncol, stream[3:3 + 2 * ncol])
    pos = 3 + 2 * ncol
    w, h = stream[pos], stream[pos + 1]
    data, _ = rzip_inflate(stream, pos + 2)
    if fmt in (CI4_RGBA, CI4_IA):
        rb = (w + 1) // 2
        idx = np.zeros((h, w), np.uint8)
        for y in range(h):
            row = np.frombuffer(data[y * rb:(y + 1) * rb], np.uint8)
            nib = np.empty(rb * 2, np.uint8)
            nib[0::2], nib[1::2] = row >> 4, row & 15
            idx[y] = nib[:w]
    else:
        idx = np.frombuffer(data[:w * h], np.uint8).reshape(h, w)
    pr = pal_rgba(pal, fmt)
    rgba = pr[np.minimum(idx, ncol - 1)]
    return {"fmt": fmt, "w": w, "h": h, "ncol": ncol, "numlods": nl, "hasloddata": hasl, "rgba": rgba}


# ------------------------------------------------------------------ encoder

class Bits:
    def __init__(self):
        self.acc, self.n, self.out = 0, 0, bytearray()

    def put(self, v, bits):
        self.acc = (self.acc << bits) | (int(v) & ((1 << bits) - 1))
        self.n += bits
        while self.n >= 8:
            self.n -= 8
            self.out.append((self.acc >> self.n) & 0xff)
        self.acc &= (1 << self.n) - 1 if self.n else 0

    def end_image(self):
        # the reader skips one byte when no bits are pending, else drops the pending bits
        if self.n == 0:
            self.out.append(0)
        else:
            self.put(0, 8 - self.n)


def _q5(v):
    return (np.clip(v.astype(np.int32) + 4, 0, 255) >> 3).astype(np.int32)


def encode_direct(rgba, fmt, numlods):
    """Non-paletted texture -> uncompressed stream (hasloddata=0: the game makes the LODs)."""
    h, w = rgba.shape[:2]
    r, g, b, a = [rgba[..., i].astype(np.int32) for i in range(4)]
    i8 = ((r * 299 + g * 587 + b * 114) // 1000)
    bs = Bits()
    bs.out.append(0x00 | (numlods & 0x3f))
    bs.put(fmt, 4); bs.put(w, 8); bs.put(h, 8); bs.put(0, 4)
    if fmt == RGBA32:
        for y in range(h):
            for x in range(w):
                bs.put((r[y, x] << 24) | (g[y, x] << 16) | (b[y, x] << 8) | a[y, x], 32)
    elif fmt == RGB24:
        for y in range(h):
            for x in range(w):
                bs.put((r[y, x] << 16) | (g[y, x] << 8) | b[y, x], 24)
    elif fmt in (RGBA16, RGB15):
        v = (_q5(r) << 11) | (_q5(g) << 6) | (_q5(b) << 1) | (a >= 128)
        for y in range(h):
            for x in range(w):
                if fmt == RGBA16:
                    bs.put(v[y, x], 16)
                else:
                    bs.put(v[y, x] >> 1, 15)
    elif fmt == IA16:
        for y in range(h):
            for x in range(w):
                bs.put((i8[y, x] << 8) | a[y, x], 16)
    elif fmt in (IA8, I8):
        v = ((i8 >> 4) << 4) | (a >> 4) if fmt == IA8 else i8
        for y in range(h):
            for x in range(w):
                bs.put(v[y, x], 8)
    elif fmt in (IA4, I4):
        v = ((i8 >> 5) << 1) | (a >= 128) if fmt == IA4 else (i8 >> 4)
        for y in range(h):
            for x in range(0, w, 2):
                bs.put(v[y, x], 4)
                bs.put(v[y, x + 1] if x + 1 < w else 0, 4)
    else:
        raise ValueError(fmt)
    bs.end_image()
    return bytes(bs.out)


def quantize(rgba, ncol, ia=False):
    """Small k-means palette quantiser -> (palette rgba (n,4), indices (h,w))."""
    px = rgba.reshape(-1, 4).astype(np.float32)
    if ia:
        i = px[:, :3] @ np.array([0.299, 0.587, 0.114], np.float32)
        px = np.stack([i, i, i, px[:, 3]], 1)
    uniq = np.unique(px.round(), axis=0)
    if len(uniq) <= ncol:
        pal = uniq
    else:
        rng = np.random.default_rng(len(px))
        pal = uniq[rng.choice(len(uniq), ncol, replace=False)]
        for _ in range(8):
            d = ((px[:, None, :] - pal[None]) ** 2).sum(-1)
            lab = d.argmin(1)
            for k in range(ncol):
                m = lab == k
                if m.any():
                    pal[k] = px[m].mean(0)
    d = ((px[:, None, :] - pal[None]) ** 2).sum(-1)
    idx = d.argmin(1).astype(np.uint8).reshape(rgba.shape[:2])
    return np.clip(pal, 0, 255).astype(np.uint8), idx


def encode_ci(rgba, fmt, ncol, numlods):
    h, w = rgba.shape[:2]
    ia = fmt in (CI8_IA, CI4_IA)
    pal, idx = quantize(rgba, ncol, ia)
    n = len(pal)
    if ia:
        pv = [(int(p[0]) << 8) | int(p[3]) for p in pal]
    else:
        pv = [(int(p[0]) >> 3 << 11) | (int(p[1]) >> 3 << 6) | (int(p[2]) >> 3 << 1) | (p[3] >= 128) for p in pal]
    if fmt in (CI4_RGBA, CI4_IA):
        rows = bytearray()
        for y in range(h):
            r = idx[y].tolist() + [0]
            rows += bytes((r[x] << 4) | r[x + 1] for x in range(0, w, 2))
        data = bytes(rows)
    else:
        data = idx.tobytes()
    out = bytearray([0x40 | (numlods & 0x3f), fmt, n - 1])
    out += struct.pack(">%dH" % n, *pv)
    out += bytes([w, h]) + rzip_deflate(data)
    return bytes(out)


def encode(rgba, fmt, numlods, ncol=None):
    if fmt >= CI8_RGBA:
        return encode_ci(rgba, fmt, ncol or (256 if fmt in (CI8_RGBA, CI8_IA) else 16), numlods)
    return encode_direct(rgba, fmt, numlods)
