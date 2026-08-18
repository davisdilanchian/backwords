import sys, os, json, gzip
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(os.path.dirname(HERE), 'data')
sys.path.insert(0,'.')
from g2p import atomize

ALPHA = ['AA','AE','AH','AO','EH','IH','IY','UH','UW',
         'B','D','DH','F','G','HH','K','L','M','N','NG',
         'P','R','S','SH','T','TH','V','W','Y','Z','ZH']
CH = "abcdefghijklmnopqrstuvwxyzABCDE"
assert len(ALPHA) == len(CH) == 31
P2C = dict(zip(ALPHA, CH))

def enc(ph):
    try: return "".join(P2C[p] for p in ph)
    except KeyError: return None

# ---- input lexicon: word -> atomised phones -------------------------------
cmu = json.load(open(os.path.join(HERE, 'cmudict.json')))
lex = []
for w, ph in cmu.items():
    e = enc(atomize([p.rstrip('012') for p in ph]))
    if e: lex.append(f"{w}\t{e}")
lex_txt = "\n".join(sorted(lex))

# ---- output index: phone key -> ranked spellings --------------------------
idx = json.load(open(os.path.join(HERE, 'index.json')))
rows = []
for key, ents in idx.items():
    k = enc(key.split())
    if not k: continue
    seen, parts = set(), []
    for spell, cost in ents:
        if spell in seen: continue
        seen.add(spell)
        d = min(35, max(0, round(cost * 20)))
        parts.append(f"{'0123456789abcdefghijklmnopqrstuvwxyz'[d]}{spell}")
        if len(parts) == 3: break
    rows.append(f"{k}\t{'|'.join(parts)}")
idx_txt = "\n".join(sorted(rows))

open(os.path.join(DATA,'lex.txt'),'w').write(lex_txt)
open(os.path.join(DATA,'idx.txt'),'w').write(idx_txt)
for n, t in (('lex.txt', lex_txt), ('idx.txt', idx_txt)):
    raw = len(t.encode()); gz = len(gzip.compress(t.encode(), 9))
    print(f"  {n:10s} {raw/1e6:.2f} MB raw   {gz/1e6:.2f} MB gzipped")
print('  written to data/')
