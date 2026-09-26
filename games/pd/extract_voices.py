"""DIRTY ROOM: voice MP3s -> spec/voices.json (facts only: the words, the
duration, the sample rate and one median pitch per line). The audio itself is
never copied; the words come from speech recognition of the line.

    python -m games.pd.extract_voices <dirty files/audio dir> <spec dir>
"""
import json
import os
import sys

import av
import numpy as np

from cleanroom.audio.pitch import median_f0


def load(path):
    ct = av.open(path)
    s = ct.streams.audio[0]
    rate = s.rate
    res = av.AudioResampler(format="flt", layout="mono", rate=16000)
    chunks, n = [], 0
    for pkt in ct.demux(s):
        try:
            frames = pkt.decode()
        except av.error.InvalidDataError:
            continue
        for fr in frames:
            n += fr.samples
            for r in res.resample(fr):
                chunks.append(r.to_ndarray().ravel())
    for r in res.resample(None):
        chunks.append(r.to_ndarray().ravel())
    return np.concatenate(chunks) if chunks else np.zeros(0, np.float32), rate, n


def main(argv):
    src, spec = argv[:2]
    from faster_whisper import WhisperModel
    model = WhisperModel("small.en", device="cpu", compute_type="int8", cpu_threads=8)
    out = {}
    names = sorted(os.listdir(src))
    for i, fn in enumerate(names):
        x, rate, n = load(os.path.join(src, fn))
        segs, _ = model.transcribe(x, language="en", beam_size=5, vad_filter=False)
        text = " ".join(s.text.strip() for s in segs).strip()
        f0 = median_f0(x.astype(np.float32), 16000)
        out[fn] = {"secs": round(n / rate, 3), "rate": rate, "text": text, "f0": round(float(f0), 1) if f0 else None}
        if i % 50 == 0:
            print(i, fn, out[fn], flush=True)
    json.dump(out, open(os.path.join(spec, "voices.json"), "w"), indent=0)
    print("voices:", len(out), "total secs", round(sum(v["secs"] for v in out.values())))


if __name__ == "__main__":
    main(sys.argv[1:])
