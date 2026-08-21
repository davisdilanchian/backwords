"""Which sound pieces are worth your time to record?

The app spells a line by cutting the reversed phone string into chunks and
looking each one up. A small number of chunks do most of the work, so ranking
them by how often they actually get emitted turns "record every phoneme" into
a session with a known length and a known payoff.

For each chunk we also print what to SAY: the chunk reversed, spelled the way
the current index spells it. Say that, flip it, and what you hear is the sound
the chunk needs a spelling for.
"""
import os, sys, json, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import assemble_ref as A
from assemble_ref import IDX
from evaluate import target_for
from wordfreq import top_n_list, zipf_frequency

HERE = os.path.dirname(os.path.abspath(__file__))

# realistic input: common words, plus the phrase sets, weighted by how often
# someone would actually type them
inputs = [(w, zipf_frequency(w, 'en')) for w in top_n_list('en', 4000) if w.isalpha()]
for f in ('testset.txt', 'holdout.txt'):
    for l in open(os.path.join(HERE, f)):
        if l.strip(): inputs.append((l.strip(), 5.0))

use = collections.Counter()
for text, z in inputs:
    try:
        t = target_for(text)
    except Exception:
        continue
    if not t: continue
    n = len(t); INF = float('inf')
    best = [INF]*(n+1); back = [None]*(n+1); best[0] = 0.0
    for i in range(n):
        if best[i] == INF: continue
        for j, spell, c in [(e[0], e[1], e[2]) for e in A.edges(t, i, A.Cfg)] or []:
            v = best[i] + c + A.Cfg.chunk
            if v < best[j]: best[j] = v; back[j] = (i, spell, " ".join(t[i:j]))
    if best[n] == INF: continue
    j = n
    while j > 0:
        i, spell, key = back[j]
        use[key] += max(1.0, 10 ** (z - 3))
        j = i
tot = sum(use.values())
ranked = use.most_common()
print(f"distinct chunks in use: {len(ranked)}")
run = 0.0
marks = {}
for i, (k, c) in enumerate(ranked, 1):
    run += c
    for target in (0.5, 0.6, 0.7, 0.8, 0.9):
        if target not in marks and run/tot >= target: marks[target] = i
for t in sorted(marks):
    print(f"  top {marks[t]:4d} chunks cover {t*100:.0f}% of everything the app emits")

def say_for(key):
    """what to read aloud so that flipping it gives the sound `key` needs"""
    rev = " ".join(key.split()[::-1])
    e = IDX.get(rev)
    return e[0][0] if e else None

rows = []
for k, c in ranked:
    s = say_for(k)
    if s: rows.append(dict(key=k, say=s, weight=round(c, 1),
                           now=IDX[k][0][0] if k in IDX else None))
json.dump(rows, open(os.path.join(HERE, 'units.json'), 'w'), indent=1)
print(f"\nwrote units.json ({len(rows)} recordable)")
print("\ntop 25 — 'say' is what you read aloud, 'now' is today's spelling of the flip:")
for r in rows[:25]:
    print(f"  {r['key']:<14s}  say {r['say']:<10s}  now {r['now']}")
