"""Perfect Dark sample banks (sfx.ctl/tbl, seq.ctl/tbl): in-place regeneration.

The .ctl is kept byte-for-byte except the parts derived from sample audio:
VADPCM codebook coefficients and loop-start decoder states. Every wave keeps
its tbl base/len (same sample count), so bank and pool sizes are exactly retail.

ALWaveTable (BE): base u32, len u32, type u8, flags u8, pad u16, loop ptr u32, book ptr u32
ALADPCMloop: start u32, end u32, count u32, state[16] s16
ALADPCMBook: order s32, npred s32, book[order*npred*8] s16
"""
import struct

import numpy as np

from cleanroom.audio import albank, vadpcm, descriptor
from cleanroom.audio.pitch import median_f0


def waves(ctl):
    """Unique ADPCM waves: dict offset -> {base,len,loop_ofs,book_ofs,npred,order,loop}."""
    bf = albank.parse_bankfile(ctl)
    out = {}
    for b in bf["banks"]:
        if not b:
            continue
        rate = b["rate"]
        for ins in b["insts"] + [b["percussion"]]:
            if not ins:
                continue
            for s in ins["sounds"]:
                wo = int(s["wave"]["_id"].split("@")[1], 16)
                if wo in out:
                    continue
                base, ln, typ = struct.unpack_from(">IIB", ctl, wo)
                if typ != 0:
                    continue
                loop_ofs, book_ofs = struct.unpack_from(">II", ctl, wo + 12)
                order, npred = struct.unpack_from(">ii", ctl, book_ofs)
                loop = None
                if loop_ofs:
                    st, en, cnt = struct.unpack_from(">IIi", ctl, loop_ofs)
                    if cnt:
                        loop = (st, en, cnt)
                out[wo] = dict(base=base, len=ln, loop_ofs=loop_ofs, book_ofs=book_ofs, order=order,
                               npred=npred, loop=loop, rate=rate,
                               keybase=s["keymap"].get("keybase"), detune=s["keymap"].get("detune"))
    return out


def book_of(ctl, w):
    n = w["order"] * w["npred"] * 8
    vals = struct.unpack_from(">%dh" % n, ctl, w["book_ofs"] + 8)
    return {"order": w["order"], "npred": w["npred"], "book": list(vals)}


def fact(ctl, tbl, w):
    """DIRTY: coarse facts of one wave."""
    pcm = vadpcm.decode(tbl[w["base"]:w["base"] + w["len"]], book_of(ctl, w))
    n = len(pcm)
    d = {"base": w["base"], "len": w["len"], "nframes": n, "rate": w["rate"], "npred": w["npred"],
         "order": w["order"], "desc": descriptor.describe(pcm.astype(np.float64), w["rate"])}
    if w["loop"]:
        d["loop"] = list(w["loop"])
    f0 = median_f0((pcm / 32768).astype(np.float32), w["rate"])
    if f0:
        d["f0"] = round(float(f0), 1)
    return d


def fit_predictors(x, k):
    """k 2-pole predictors fitted to our own waveform (k-means of per-frame LPC)."""
    fits = []
    for s in range(2, len(x) - 16, 16):
        y, p1, p2 = x[s:s + 16], x[s - 1:s + 15], x[s - 2:s + 14]
        if (y ** 2).sum() < 1e3:
            continue
        a, *_ = np.linalg.lstsq(np.stack([p1, p2], 1), y, rcond=None)
        fits.append(a)
    base = [(0.0, 0.0), (1.0, 0.0), (1.8, -0.82), (1.95, -0.96), (0.5, 0.0), (1.5, -0.6), (1.2, -0.3), (1.9, -0.92)]
    if len(fits) < k * 2:
        return base[:k]
    f = np.clip(np.asarray(fits), [-1.95, -0.98], [1.95, 0.98])
    order = np.argsort(f[:, 0])
    c = f[order[np.linspace(0, len(f) - 1, k).astype(int)]].copy()
    for _ in range(10):
        lab = np.argmin(((f[:, None, :] - c[None]) ** 2).sum(-1), 1)
        for j in range(k):
            if (lab == j).any():
                c[j] = f[lab == j].mean(0)
    out = []
    for a1, a2 in c:
        a2 = float(np.clip(a2, -0.98, 0.98))
        out.append((float(np.clip(a1, -(1 - a2) + 0.02, (1 - a2) - 0.02)), a2))
    return out


def regenerate(ctl, tbl_size, spec, sample_hook=None, seed_prefix="pd"):
    """CLEAN: spec (offset -> fact) -> (new ctl bytes, new tbl bytes)."""
    import hashlib
    ctl = bytearray(ctl)
    tbl = bytearray(tbl_size)
    for key, d in spec.items():
        wo = int(key, 16)
        n = d["nframes"]
        seed = int.from_bytes(hashlib.sha1(("%s/%s" % (seed_prefix, key)).encode()).digest()[:4], "little")
        x = sample_hook(key, d) if sample_hook else None
        if x is None:
            x = descriptor.synthesize(d["desc"], n, d["rate"], seed=seed)
        x = np.asarray(x, np.float32)[:n]
        x = np.pad(x, (0, n - len(x)))
        lp = d.get("loop")
        if lp and lp[1] > lp[0]:
            x = descriptor.make_loop_seamless(x, lp[0], min(lp[1], n))
        dither = np.random.default_rng(seed).integers(-1, 2, n)
        pcm = np.clip(np.round(np.clip(x, -1, 1) * 30000) + dither, -32768, 32767).astype(np.int16)
        preds = fit_predictors(pcm.astype(np.float64), d["npred"])
        book = vadpcm.make_book(preds)
        if d["order"] != 2:
            raise ValueError("order %d" % d["order"])
        data, _, dec = vadpcm.encode(pcm, book)
        data = data[:d["len"]] + bytes(max(0, d["len"] - len(data)))
        tbl[d["base"]:d["base"] + d["len"]] = data
        # codebook + loop state in place
        loop_ofs, book_ofs = struct.unpack_from(">II", ctl, wo + 12)
        struct.pack_into(">%dh" % len(book["book"]), ctl, book_ofs + 8, *book["book"])
        if lp and loop_ofs:
            st = vadpcm.loop_state(dec, lp[0])
            struct.pack_into(">16h", ctl, loop_ofs + 12, *st)
    return bytes(ctl), bytes(tbl)
