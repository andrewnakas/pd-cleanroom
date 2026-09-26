"""Placeholder voices for Perfect Dark's 548 MP3 lines: Piper TTS (offline, stock
voices, no cloning), one voice per character code, fitted to the line length,
encoded as MPEG-2 Layer III 22.05 kHz mono (what the game streams).

Inputs are facts only: spec/voices.json (words from speech recognition, length,
rate, one median pitch). Recorded takes in games/pd/takes/<line>.wav win over TTS
(see practice pack in the STATUS "for the morning" list).

    python -m games.pd.voices build [names...]   -> games/pd/voices/<line>.wav (cache)
    (generate.py 'voices' step encodes the cache into files/<A-name> MP3s)
"""
import io
import json
import os
import re
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "voices")
TAKES = os.path.join(HERE, "takes")
PIPER_DIR = os.environ.get("PIPER_VOICES", "C:/Users/andre/n64work/piper_voices")

# character code (from the line name) -> (Piper model, semitones)
CAST = {
    "jo": ("en_US-kristin-medium", 1.0), "joexec": ("en_US-kristin-medium", 1.0), "joinst": ("en_US-kristin-medium", 1.0),
    "jorep": ("en_US-kristin-medium", 1.0), "jorpld": ("en_US-kristin-medium", 1.0), "josci": ("en_US-kristin-medium", 1.0),
    "trjo": ("en_US-kristin-medium", 1.0), "a51jo": ("en_US-kristin-medium", 1.0), "af1jo": ("en_US-kristin-medium", 1.0),
    "ca": ("en_US-ryan-high", -2.5), "carr": ("en_US-ryan-high", -2.5), "cicarr": ("en_US-ryan-high", -2.5),
    "trcarr": ("en_US-ryan-high", -2.5), "invcar": ("en_US-ryan-high", -2.5), "carrbye": ("en_US-ryan-high", -2.5),
    "m3l2carr": ("en_US-ryan-high", -2.5),
    "el": ("en_US-joe-medium", 3.5), "elv": ("en_US-joe-medium", 3.5), "a51elv": ("en_US-joe-medium", 3.5),
    "elvcet": ("en_US-joe-medium", 3.5), "pelelv": ("en_US-joe-medium", 3.5), "cetael": ("en_US-joe-medium", 3.5),
    "assael": ("en_US-joe-medium", 3.5),
    "dv": ("en_US-amy-medium", -1.0), "devr": ("en_US-amy-medium", -1.0),
    "tr": ("en_US-joe-medium", -1.0), "af1tr": ("en_US-joe-medium", -1.0),
    "pr": ("en_US-ryan-high", -1.0), "af1pr": ("en_US-ryan-high", -1.0),
    "dr": ("en_US-joe-medium", 1.5), "chdroid": ("en_US-joe-medium", 2.0),
    "bl": ("en_US-joe-medium", -3.0),
    "jn": ("en_US-ryan-high", 0.5), "a51jon": ("en_US-ryan-high", 0.5),
    "su": ("en_US-hfc_female-medium", -2.0),
    "gd": ("en_US-joe-medium", -2.0),
    "cifema": ("en_US-amy-medium", 1.5), "invfema": ("en_US-amy-medium", 1.5), "recep": ("en_US-hfc_female-medium", 1.0),
    "labacc": ("en_US-hfc_female-medium", 0.0), "cifost": ("en_US-joe-medium", -1.5), "trfost": ("en_US-joe-medium", -1.5),
    "invfost": ("en_US-joe-medium", -1.5), "cigrim": ("en_US-ryan-high", 2.0), "trgrim": ("en_US-ryan-high", 2.0),
    "invgrim": ("en_US-ryan-high", 2.0), "vilgrim": ("en_US-ryan-high", 2.0), "cihopk": ("en_US-joe-medium", 1.0),
    "invhopk": ("en_US-joe-medium", 1.0), "holohopk": ("en_US-joe-medium", 1.0),
    "cifarr": ("en_US-hfc_female-medium", -1.0), "invfarr": ("en_US-hfc_female-medium", -1.0),
    "ciroge": ("en_US-ryan-high", -0.5), "trroge": ("en_US-ryan-high", -0.5),
}
FEMALE_DEFAULT = ("en_US-amy-medium", 0.5)
MALE_DEFAULTS = [("en_US-joe-medium", -1.0), ("en_US-ryan-high", -1.5), ("en_US-joe-medium", 0.5), ("en_US-ryan-high", 1.0)]


def speaker(name):
    base = name[:-4] if name.endswith(".mp3") else name
    m = re.match(r"p\d+_\d+_([a-z]+)$", base)
    if m:
        return m.group(1)
    return re.sub(r"\d+$", "", base).rstrip("_")


def cast(name, f0):
    who = speaker(name)
    if who in CAST:
        return CAST[who]
    for k, v in CAST.items():
        if who.endswith(k) and len(k) >= 3:
            return v
    if f0 and f0 > 165:
        return FEMALE_DEFAULT
    return MALE_DEFAULTS[sum(map(ord, who)) % len(MALE_DEFAULTS)]


GROUPS = [("joanna", ("jo",)), ("carrington", ("ca", "carr", "car")), ("elvis", ("el", "elv", "ael")),
          ("cassandra", ("dv", "devr")), ("trent", ("tr",)), ("president", ("pr",)), ("jonathan", ("jn", "jon")),
          ("drcaroll", ("dr", "droid")), ("blonde", ("bl",))]


def group(name, f0=None):
    """Recording group (main character, else extras by voice register) for the practice pack."""
    who = speaker(name)
    for g, codes in GROUPS:
        if who in codes or any(who.endswith(c) and len(c) >= 2 and who != "sci" for c in codes if len(c) >= 3):
            return g
        if who.startswith(("a51", "af1", "ci", "inv", "tr", "pel", "joexec", "joinst", "jorep", "jorpld", "josci")):
            base = who[3:] if who.startswith(("a51", "af1", "pel", "inv")) else who[2:] if who.startswith(("ci", "tr")) else who
            if base in codes or who.startswith("jo"):
                return "joanna" if who.startswith("jo") else g
    return "extras_female" if (f0 or 0) > 165 else "extras_male"


def lines():
    return json.load(open(os.path.join(HERE, "spec", "voices.json")))


_V = {}


def piper(model, text, length):
    from piper import PiperVoice, SynthesisConfig
    if model not in _V:
        _V[model] = PiperVoice.load(os.path.join(PIPER_DIR, model + ".onnx"))
    v = _V[model]
    cfg = SynthesisConfig(length_scale=length, noise_scale=0.7, noise_w_scale=0.8)
    x = np.concatenate([c.audio_float_array for c in v.synthesize(text, syn_config=cfg)]).astype(np.float32)
    return x, v.config.sample_rate


def trim(x, thr=0.006):
    idx = np.nonzero(np.abs(x) > thr)[0]
    return x[max(0, idx[0] - 300):idx[-1] + 300] if len(idx) else x[:0]


def speak(name, d):
    """One placeholder take fitted to the slot: float32 at d['rate']."""
    import librosa
    rate, secs = d["rate"], d["secs"]
    text = d["text"].strip() or "..."
    model, semis = cast(name, d.get("f0"))
    f = 2 ** (semis / 12)
    length = 1.0 * f
    for _ in range(4):
        x, sr = piper(model, text, length)
        x = trim(x)
        y = librosa.resample(x, orig_sr=sr * f, target_sr=rate).astype(np.float32)
        if len(y) <= secs * rate * 1.02 or length < 0.55 * f:
            break
        length *= max(0.55, secs * rate / len(y) * 0.98)
    n = int(secs * rate)
    y = y[:n]
    pad = max(0, (n - len(y)) // 6)
    y = np.pad(y, (pad, max(0, n - len(y) - pad)))
    peak = np.abs(y).max() or 1
    return (y / peak * 0.85).astype(np.float32)


def wav_write(path, x, rate):
    import wave
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype("<i2").tobytes())


def wav_read(path):
    import wave
    with wave.open(path) as w:
        return np.frombuffer(w.readframes(w.getnframes()), "<i2").astype(np.float32) / 32768, w.getframerate()


def mp3_bytes(x, rate, kbps=32):
    import av
    buf = io.BytesIO()
    ct = av.open(buf, "w", format="mp3", options={"id3v2_version": "0", "write_xing": "0"})
    st = ct.add_stream("libmp3lame", rate=rate, layout="mono")
    st.bit_rate = kbps * 1000
    pcm = (np.clip(x, -1, 1) * 32767).astype(np.int16)[None, :]
    fr = av.AudioFrame.from_ndarray(pcm, format="s16", layout="mono")
    fr.sample_rate = rate
    for p in st.encode(fr):
        ct.mux(p)
    for p in st.encode(None):
        ct.mux(p)
    ct.close()
    return buf.getvalue()


def build(only=None):
    os.makedirs(CACHE, exist_ok=True)
    L = lines()
    n = 0
    for name, d in sorted(L.items()):
        if only and name not in only:
            continue
        out = os.path.join(CACHE, name[:-4] + ".wav")
        if os.path.exists(out) and not only:
            continue
        wav_write(out, speak(name, d), d["rate"])
        n += 1
        if n % 50 == 0:
            print(n, name, flush=True)
    print("voices built:", n)


def write_pack(pack):
    """Encode cached/recorded lines into files/<name> (the A-file names from the layout)."""
    lay = json.load(open(os.path.join(HERE, "spec", "rom_layout.json")))
    L = lines()
    n = 0
    for f in lay["files"]:
        base = os.path.basename(f["name"])
        if base[:1] != "A":
            continue
        line = [k for k in L if k[:-4] == base[1:-1]]
        if not line:
            continue
        key = line[0]
        take = os.path.join(TAKES, key[:-4] + ".wav")
        src = take if os.path.exists(take) else os.path.join(CACHE, key[:-4] + ".wav")
        if not os.path.exists(src):
            continue
        x, rate = wav_read(src)
        p = os.path.join(pack, "files", f["name"])
        os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, "wb").write(mp3_bytes(x, L[key]["rate"] if rate == L[key]["rate"] else rate))
        n += 1
    return n


if __name__ == "__main__":
    if sys.argv[1] == "build":
        build(set(sys.argv[2:]) or None)
