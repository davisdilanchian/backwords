"""Does reading-friendly spelling actually cost anything in the audio?

Phone error rate counts a swap like eess -> ease as a whole error. Reversal
destroys voicing cues anyway, so that swap may be nearly free in the only place
it matters. Score both ways and see which story the audio tells.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import assemble_ref as A
from evaluate import target_for
from g2p import atomize, phones as espeak_phones, per
from readability import score
from obj import score_script

lines = [l.strip() for l in open('testset.txt') if l.strip()][:25]
base = dict(err_sub_near=1.0, err_sub_far=3.0, err_ins=1.6, err_del=2.2,
            w_err=2.5, chunk=0.25, maxlen=7, max_err=2, w_nonword=0.0)
def cfg(**kw):
    d = dict(base); d.update(kw); return type('C', (), d)

print(f"{'nonword':>8} | {'phone PER':>9} | {'acoustic':>8} | {'%real':>6} {'zipf':>5}")
print("-" * 52)
for w in (0.0, 2.0, 3.0, 4.5, 6.0, 9.0):
    c = cfg(w_nonword=w)
    pe = ac = 0.0; toks = []
    for l in lines:
        t = target_for(l)
        out = A.assemble(t, c); s = ' '.join(out)
        toks.extend(out)
        pe += per(t, atomize(espeak_phones(s)))
        ac += score_script(l, s)
    n = len(lines); sc = score(toks)
    print(f"{w:8.1f} | {pe/n:9.3f} | {ac/n:8.4f} | {100*sc['real']:5.0f}% {sc['zipf']:5.2f}")
