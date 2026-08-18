"""espeak-ng's own pronunciation for every word in CMUdict.

The output side of Backwords is only trustworthy if something other than the
author reads the spellings back. espeak-ng is that second reader: it is a real
letter-to-sound engine, it has never seen this project, and it generalises to
spellings that are not words. Everything downstream is checked against it.
"""
import sys, json, subprocess, collections
sys.path.insert(0, __import__('os').path.dirname(__file__) or '.')
from g2p import ipa_to_arpa

words = sorted(w for w in json.load(open('cmudict.json')) if w.isalpha())
print('words:', len(words))

def batch(ws):
    r = subprocess.run(["espeak-ng","-q","--ipa","-v","en-us"],
                       input="\n".join(ws), capture_output=True, text=True)
    toks = r.stdout.split()
    return toks if len(toks) == len(ws) else None

out, unk = {}, collections.Counter()
for i in range(0, len(words), 500):
    chunk = words[i:i+500]
    toks = batch(chunk)
    if toks is None:                       # a line espeak expanded; redo one by one
        toks = [(batch([w]) or [""])[0] for w in chunk]
    for w, ipa in zip(chunk, toks):
        ph, u = ipa_to_arpa(ipa)
        for c in u: unk[c] += 1
        if ph: out[w] = ph
    if i % 20000 == 0: print(' ', i, flush=True)

print('mapped:', len(out), ' unmapped IPA chars:', unk.most_common(8))
json.dump(out, open('espeak_lex.json','w'))
