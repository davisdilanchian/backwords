"""Does the tiled script actually reverse into the line?

Scored the only way that means anything: speak the script, reverse the
waveform, and measure how close it lands to the line spoken normally. No
language model, no phone spelling, no opinion about notation.

  control  say the line forwards -- should NOT match its own reversal
  words    the searched-index speller
  sounds   the ear-based speller
  tiled    words chosen by measured reversed-acoustics
"""
import os, sys, subprocess, tempfile, wave
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tile import tile, feats, SR
import librosa

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

def audio(text, speed=150):
    with tempfile.TemporaryDirectory() as td:
        a, b = os.path.join(td, "a.wav"), os.path.join(td, "b.wav")
        subprocess.run(["espeak-ng", "-v", "en-us", "-s", str(speed), "-w", a, "--", text],
                       check=True, capture_output=True)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", a,
                        "-ar", str(SR), "-ac", "1", b], check=True)
        with wave.open(b, "rb") as w:
            y = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
    return y.astype(np.float32) / 32768.0

def dist(ya, yb):
    A, B = feats(ya), feats(yb)
    D, wp = librosa.sequence.dtw(X=A, Y=B, metric="cosine")
    return D[-1, -1] / len(wp)

def spellers(line):
    js = ('const S=require("%s/script.js");const fs=require("fs");'
          'S.load(fs.readFileSync("%s/data/lex.txt","utf8"),fs.readFileSync("%s/data/idx.txt","utf8"),'
          'fs.readFileSync("%s/data/style.json","utf8"));'
          'const a=S.make(process.argv[1]).parts.map(p=>p.spell).join(" ");'
          'const b=S.byEar(process.argv[1]).map(p=>p.spell).join(" ");'
          'process.stdout.write(JSON.stringify([a,b]));') % ((ROOT,) * 4)
    import json
    return json.loads(subprocess.run(["node", "-e", js, line],
                                     capture_output=True, text=True).stdout)

def main():
    lines = sys.argv[1:] or [l.strip() for l in open(os.path.join(HERE, "testset.txt")) if l.strip()][:10]
    tot = {"control": 0.0, "words": 0.0, "sounds": 0.0, "tiled": 0.0}
    for line in lines:
        tgt = audio(line)                       # the sound the reversed take must land on
        w, s = spellers(line)
        r = tile(line)
        t = " ".join(x for x, _ in r) if r else ""
        cand = {"control": line, "words": w, "sounds": s, "tiled": t}
        print(f"  {line}")
        for k, text in cand.items():
            if not text: continue
            d = dist(audio(text)[::-1].copy(), tgt)     # speak it, reverse it, compare
            tot[k] += d
            print(f"    {k:8s} {d:.3f}  {text[:58]}")
        print()
    n = len(lines)
    print("mean distance from the reversed take to the line (lower is better):")
    for k in ("control", "words", "sounds", "tiled"):
        print(f"  {k:8s} {tot[k]/n:.4f}")
    print("\ncontrol is the floor to beat: it is what you get by just saying the line.")

if __name__ == "__main__":
    main()
