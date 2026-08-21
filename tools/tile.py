"""Spell a line by tiling its sound with words measured backwards.

reverse(a ++ b) is reverse(b) ++ reverse(a), so if the script is w1 w2 ... wk
then the reversed take is reverse(wk) first and reverse(w1) last. Tile the
target sound left to right with measured reversed-word signatures, then read
the matched words out back to front and that is the script.

Nothing is spelled. Every piece is a real English word, chosen because its
measured reversal fits the sound at that point.
"""
import os, sys, subprocess, tempfile, wave
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

HERE = os.path.dirname(os.path.abspath(__file__))
SR, NFRAME, NCEP, HOP = 16000, 16, 13, 160

_ix = None
def index():
    global _ix
    if _ix is None:
        z = np.load(os.path.join(HERE, "revindex.npz"))
        S = z["sig"].reshape(len(z["words"]), -1)          # flat, for one matmul
        S = S / (np.linalg.norm(S, axis=1, keepdims=True) + 1e-8)
        _ix = dict(words=z["words"], flat=S, dur=z["dur"], zipf=z["zipf"])
    return _ix

def feats_of_text(text, speed=150):
    with tempfile.TemporaryDirectory() as td:
        raw, w16 = os.path.join(td, "a.wav"), os.path.join(td, "b.wav")
        subprocess.run(["espeak-ng", "-v", "en-us", "-s", str(speed), "-w", raw, "--", text],
                       check=True, capture_output=True)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", raw,
                        "-ar", str(SR), "-ac", "1", w16], check=True)
        with wave.open(w16, "rb") as w:
            y = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
    return feats(y.astype(np.float32) / 32768.0)

def feats(y):
    import librosa
    y, _ = librosa.effects.trim(y, top_db=32)
    m = librosa.feature.mfcc(y=y, sr=SR, n_mfcc=NCEP, hop_length=HOP)
    return ((m - m.mean(1, keepdims=True)) / (m.std(1, keepdims=True) + 1e-8)).astype(np.float32)

def resample(seg):
    idx = np.linspace(0, seg.shape[1] - 1, NFRAME)
    return np.stack([np.interp(idx, np.arange(seg.shape[1]), seg[k]) for k in range(NCEP)])

def tile(target_text, min_f=8, max_f=70, chunk_pen=0.35, rare_pen=0.06, topk=1):
    ix = index()
    F = feats_of_text(target_text)
    T = F.shape[1]
    INF = 1e18
    best = np.full(T + 1, INF); best[0] = 0.0
    back = [None] * (T + 1)
    for t in range(1, T + 1):
        lo = max(0, t - max_f)
        for s in range(lo, max(0, t - min_f) + 1):
            if best[s] >= INF: continue
            seg = resample(F[:, s:t]).reshape(-1)
            seg = seg / (np.linalg.norm(seg) + 1e-8)
            d = 1.0 - ix["flat"] @ seg                       # cosine distance, all words at once
            # a word whose own length is near the segment's fits better
            dur_gap = np.abs(ix["dur"] - (t - s) * HOP / SR)
            score = d + 0.55 * dur_gap + rare_pen * np.maximum(0, 5.0 - ix["zipf"])
            j = int(np.argmin(score))
            v = best[s] + float(score[j]) + chunk_pen
            if v < best[t]:
                best[t] = v; back[t] = (s, int(j), float(d[j]))
    if best[T] >= INF: return None
    out, t = [], T
    while t > 0:
        s, j, d = back[t]
        out.append((str(ix["words"][j]), d))
        t = s
    # tiled left to right; the script is those words back to front
    return out            # already reversed by walking the backpointers

if __name__ == "__main__":
    for line in (sys.argv[1:] or ["never give up", "hello my name is dan"]):
        r = tile(line)
        print(f"  {line}")
        print(f"    -> {' '.join(w for w, _ in r)}")
        print(f"       (fit per word: {', '.join(f'{d:.2f}' for _, d in r)})")
