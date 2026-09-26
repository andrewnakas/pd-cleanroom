"""Voice practice pack + take cutter for Perfect Dark (the user records the lines).

build (DIRTY, personal use, written outside the repo, never published):
    python -m games.pd.practice build <dirty files/audio dir> <out dir>
  -> clips/NNN_<line>.wav, practice_<character>_call_and_response.wav, SCRIPT.txt
     track layout per character: clip, 0.3 s, 80 ms beep 880 Hz, gap (1.5 x clip + 1.5 s) to speak into.

cut (CLEAN, uses only the spec's line lengths to rebuild the layout):
    python -m games.pd.practice cut <your recording of one track> <character>
  -> games/pd/takes/<line>.wav (voices.py and generate.py prefer these over TTS)
"""
import json
import os
import sys
import wave

import numpy as np

from games.pd import voices

HZ = 22050
HERE = os.path.dirname(os.path.abspath(__file__))


def plan():
    L = voices.lines()
    tracks = {}
    for name, d in sorted(L.items()):
        who = voices.speaker(name)
        tracks.setdefault(who, []).append((name, d))
    return tracks


def wr(path, x):
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(HZ)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype("<i2").tobytes())


def build(src, out):
    from games.pd.extract_voices import load
    import librosa
    os.makedirs(os.path.join(out, "clips"), exist_ok=True)
    beep = (0.2 * np.sin(2 * np.pi * 880 * np.arange(int(0.08 * HZ)) / HZ)).astype(np.float32)
    script = ["Perfect Dark voice practice. One track per character: listen, speak after each beep, in character.",
              "Record each track as one file, then: python -m games.pd.practice cut <file> <character>", ""]
    i = 0
    for who, items in sorted(plan().items()):
        parts = []
        script.append("== %s  (practice_%s_call_and_response.wav)" % (who, who))
        for name, d in items:
            i += 1
            x16, _, _ = load(os.path.join(src, name))
            x = librosa.resample(x16, orig_sr=16000, target_sr=HZ).astype(np.float32)
            x = x[:int(d["secs"] * HZ)]
            wr(os.path.join(out, "clips", "%03d_%s.wav" % (i, name[:-4])), x)
            gap = np.zeros(int((d["secs"] * 1.5 + 1.5) * HZ), np.float32)
            parts += [x, np.zeros(int(0.3 * HZ), np.float32), beep, gap]
            script.append("%03d  %-14s max %.1fs  \"%s\"" % (i, name[:-4], d["secs"], d["text"]))
        wr(os.path.join(out, "practice_%s_call_and_response.wav" % who), np.concatenate(parts))
        script.append("")
    script.append("These clips come from your own ROM: practice only, do not share or commit them.")
    open(os.path.join(out, "SCRIPT.txt"), "w", encoding="utf8").write("\n".join(script))
    print("practice pack: %d lines, %d characters -> %s" % (i, len(plan()), out))


def cut(recording, who):
    from cleanroom.voice.takes import load_audio
    x = load_audio(recording)
    # recordings are expected at 22050 (load_audio returns the file's rate samples); resample if needed
    items = plan()[who]
    # rebuild the window layout: response window starts after clip + 0.3 s + beep
    t = 0.0
    os.makedirs(os.path.join(HERE, "takes"), exist_ok=True)
    n = 0
    for name, d in items:
        start = t + d["secs"] + 0.3 + 0.08
        end = start + d["secs"] * 1.5 + 1.5
        seg = x[int(start * HZ):int(end * HZ)]
        idx = np.nonzero(np.abs(seg) > 0.02)[0]
        if len(idx):
            take = seg[max(0, idx[0] - 400):idx[-1] + 400]
            take = take[:int(d["secs"] * HZ)]
            take = np.pad(take, (0, int(d["secs"] * HZ) - len(take)))
            peak = np.abs(take).max() or 1
            wr(os.path.join(HERE, "takes", name[:-4] + ".wav"), take / peak * 0.85)
            n += 1
        t = end
    print("cut %d/%d takes for %s" % (n, len(items), who))


if __name__ == "__main__":
    if sys.argv[1] == "build":
        build(sys.argv[2], sys.argv[3])
    elif sys.argv[1] == "cut":
        cut(sys.argv[2], sys.argv[3])
