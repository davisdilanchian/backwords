import sys, json, subprocess, os, numpy as np
sys.path.insert(0, __import__('os').path.dirname(__file__) or '.')
from acoustic import render, mfcc, dtw_dist
from audio import phone_decode
import assemble_ref as A
from evaluate import target_for
from g2p import per

HERE = os.path.dirname(os.path.abspath(__file__))
lines = [l.strip() for l in open(os.path.join(HERE,'testset.txt')) if l.strip()][:20]
new = {l: ' '.join(A.assemble(target_for(l))) for l in lines}
# to compare against an older build, point BASELINE_JSON at {line: script}
old = json.load(open(os.environ['BASELINE_JSON'])) if os.environ.get('BASELINE_JSON') else None

V = "en-us"
rows=[]
for i, l in enumerate(lines):
    other = lines[(i+7) % len(lines)]
    ref   = render(l, voice=V, speed=150)
    same  = render(l, voice=V, speed=162)                     # same content, tiny variation
    a_new = render(new[l],    reverse=True, voice=V, speed=150)
    a_old = render(old[l], reverse=True, voice=V, speed=150) if old else None
    a_ch  = render(new[other],reverse=True, voice=V, speed=150)
    paths = dict(ref=ref, same=same, new=a_new, ch=a_ch)
    if a_old: paths['old'] = a_old
    M = {k: mfcc(p) for k,p in paths.items()}
    tgt = target_for(l)[::-1]                                  # forward phone target
    rows.append(dict(
        line=l,
        d_ceil=dtw_dist(M['ref'],M['same']), d_new=dtw_dist(M['ref'],M['new']),
        d_old =dtw_dist(M['ref'],M['old']) if a_old else float('nan'),
        d_ch  =dtw_dist(M['ref'],M['ch']),
        # what an acoustic phone recogniser actually hears
        p_fwd=per(tgt, phone_decode(ref)),
        p_new=per(tgt, phone_decode(a_new)),
        p_old=per(tgt, phone_decode(a_old)) if a_old else float('nan'),
        p_ch =per(tgt, phone_decode(a_ch)),
    ))
    print('.', end='', flush=True)
print()
m = lambda k: float(np.mean([r[k] for r in rows]))
c, n, ch = m('d_ceil'), m('d_new'), m('d_ch')
print("\n=== MFCC-DTW distance to the original audio (same voice; lower is better) ===")
print(f"  ceiling  same text, slight speed change : {c:.4f}")
print(f"  script   reversed                       : {n:.4f}")
if old: print(f"  baseline reversed                       : {m('d_old'):.4f}")
print(f"  chance   reversed, wrong phrase         : {ch:.4f}")
print(f"  normalised (1 = ceiling, 0 = chance)    : {1-(n-c)/(ch-c):.2f}")
if old:
    o = m('d_old')
    print(f"  baseline normalised                     : {1-(o-c)/(ch-c):.2f}")
    print(f"  closer than baseline on {sum(1 for r in rows if r['d_new']<r['d_old'])}/{len(rows)}")
print("\n=== phone recogniser on the reversed audio (PER vs the intended line) ===")
print(f"  forward speech (recogniser noise floor) : {m('p_fwd'):.3f}")
print(f"  script  reversed                        : {m('p_new'):.3f}")
if old: print(f"  baseline reversed                       : {m('p_old'):.3f}")
print(f"  chance                                  : {m('p_ch'):.3f}")
print("  (the recogniser barely beats its own noise floor on synthetic speech;")
print("   treat this block as a sanity check, not a measurement)")
json.dump(rows, open(os.path.join(HERE,'acoustic_rows.json'),'w'), indent=1)
