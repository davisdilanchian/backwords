"""What does each phone actually become when the audio is played backwards?

Each phone is put in a fixed carrier frame, the frame is synthesised, the
waveform is reversed, and the result is matched against forward renditions of
every phone in the same frame. If reversal preserved phones, every phone would
match itself.
"""
import sys, json, numpy as np
sys.path.insert(0, __import__('os').path.dirname(__file__) or '.')
from acoustic import render, mfcc, dtw_dist

IDX = json.load(open(__import__('os').path.join(__import__('os').path.dirname(__import__('os').path.abspath(__file__)),'index.json')))
CONS = "B D DH F G HH K L M N NG P R S SH T TH V W Y Z ZH".split()
VOW  = "AA AE AH AO EH IH IY UH UW".split()

def pick(key):
    e = IDX.get(key)
    return e[0][0] if e else None

frames = {}
for c in CONS:                       # ah + Cah  ->  AA C AA
    s = pick(f"{c} AA")
    if s: frames[c] = ("ah " + s, ["AA", c, "AA"])
for v in VOW:                        # bVb
    s = pick(f"B {v} B") or pick(f"D {v} D") or pick(f"B {v}")
    if s: frames[v] = (s, ["B", v, "B"])

print("carrier frames:")
for p,(s,_) in sorted(frames.items()): print(f"   {p:3s} {s}")

fwd = {p: mfcc(render(s, voice="en-us", speed=140)) for p,(s,_) in frames.items()}
rev = {p: mfcc(render(s, reverse=True, voice="en-us", speed=140)) for p,(s,_) in frames.items()}

groups = [("consonants", CONS), ("vowels", VOW)]
out = {}
for name, phones in groups:
    phones = [p for p in phones if p in frames]
    print(f"\n=== {name}: what a reversed phone matches best ===")
    kept = 0
    for p in phones:
        d = sorted(((dtw_dist(rev[p], fwd[q]), q) for q in phones))
        best = d[0][1]; selfd = next(x for x,q in d if q == p)
        rank = [q for _,q in d].index(p) + 1
        flag = "same" if best == p else f"-> {best}"
        print(f"   {p:3s} {flag:9s} (self ranks {rank}/{len(phones)}; "
              f"best {d[0][0]:.3f}, self {selfd:.3f}, runners-up "
              f"{', '.join(q for _,q in d[1:4])})")
        kept += (best == p)
        out[p] = dict(best=best, rank=rank, top=[q for _,q in d[:4]])
    print(f"   survives reversal intact: {kept}/{len(phones)}")
json.dump(out, open('reversal_matrix.json','w'), indent=1)
