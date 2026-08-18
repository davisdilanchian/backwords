import os, sys, json, collections
_p = lambda n: os.path.join(os.path.dirname(os.path.abspath(__file__)), n)
sys.path.insert(0, __import__('os').path.dirname(__file__) or '.')
from g2p import atomize
from wordfreq import zipf_frequency

esp = json.load(open(_p('espeak_lex.json')))
syl = json.load(open(_p('syllabary.json')))

# key: "P H O N E S" (atomised) -> list of [spelling, cost]
idx = collections.defaultdict(list)

BAD = set("""a i o e u ng sh th ch mm hm zz ss ll nn tt pp bb dd ff gg rr vv""".split())
for w, ph in esp.items():
    if len(w) < 2 or w in BAD: continue
    z = zipf_frequency(w, 'en')
    if z < 2.6: continue                       # keep it to words people read on sight
    key = " ".join(atomize(ph))
    n = len(key.split())
    if n > 8: continue
    # cheaper for commoner words; real words beat invented spellings
    cost = max(0.05, 0.75 - 0.09*(z - 2.6))
    idx[key].append([w, round(cost,3)])

nreal = sum(len(v) for v in idx.values())
for rawkey, spells in syl.items():
    key = " ".join(atomize(rawkey.split()))
    for s in sorted(spells, key=len)[:2]:
        idx[key].append([s, 1.05 + 0.03*len(s)])

for k in idx:
    idx[k].sort(key=lambda x: x[1])
    idx[k] = idx[k][:6]

print('index keys:', len(idx), ' real-word entries:', nreal,
      ' total entries:', sum(len(v) for v in idx.values()))
json.dump(idx, open(_p('index.json'),'w'))
sz = len(json.dumps(idx))
print(f'index size: {sz/1e6:.2f} MB')
for probe in ["S K AA F","HH EH L AO UW","M AA IY","K AE T","N AA R B"]:
    print(f'  {probe:16s} -> {idx.get(probe, [])[:4]}')
