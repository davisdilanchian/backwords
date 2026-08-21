import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import assemble_ref as A
from evaluate import target_for
from g2p import atomize, phones as espeak_phones, per
from readability import score

lines = [l.strip() for l in open('testset.txt') if l.strip()] + \
        [l.strip() for l in open('holdout.txt') if l.strip()]

base = dict(err_sub_near=1.0, err_sub_far=3.0, err_ins=1.6, err_del=2.2,
            w_err=2.5, chunk=0.25, maxlen=7, max_err=2, w_nonword=0.0)
def cfg(**kw):
    d = dict(base); d.update(kw); return type('C', (), d)

print(f"{'nonword':>8} {'maxlen':>6} | {'PER':>6} {'exact':>6} | {'%real':>6} {'zipf':>5} {'tok/line':>8}")
print("-" * 62)
rows = []
for w_nonword in (0.0, 1.0, 2.0, 3.0, 4.5, 6.0, 9.0):
    for maxlen in (7, 9):
        c = cfg(w_nonword=w_nonword, maxlen=maxlen)
        tot = ex = 0; toks = []
        for l in lines:
            t = target_for(l)
            out = A.assemble(t, c)
            toks.extend(out)
            p = per(t, atomize(espeak_phones(' '.join(out))))
            tot += p; ex += (p == 0)
        n = len(lines); s = score(toks)
        rows.append((w_nonword, maxlen, tot/n, ex, s))
        print(f"{w_nonword:8.1f} {maxlen:6d} | {tot/n:6.3f} {ex:6d} | "
              f"{100*s['real']:5.0f}% {s['zipf']:5.2f} {len(toks)/n:8.1f}")
