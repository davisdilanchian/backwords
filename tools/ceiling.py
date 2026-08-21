"""How well could anything match this person?

Before asking someone for more data, check whether more data can help. If the
same sound gets spelled two different ways on two different days, no model can
match both, and the gap between those spellings is the ceiling — not a fault in
the renderer and not something another recording session fixes.
"""
import os, sys, json, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lexicon import word_phones

HERE = os.path.dirname(os.path.abspath(__file__))

def collect():
    seen = collections.defaultdict(list)   # phone chunk -> spellings given for it
    return seen

seen = collections.defaultdict(list)     # phone chunk -> spellings given for it

for r in json.load(open(os.path.join(HERE, 'calibration', 'lines-davis.json')))['lines']:
    ws, ts = r['line'].split(), r['mine'].lower().split()
    if len(ws) != len(ts): continue
    for w, t in zip(reversed(ws), ts):
        ph = word_phones(w)[::-1]
        if ph: seen[' '.join(ph)].append((t, w, 'line'))

cal = json.load(open(os.path.join(HERE, 'calibration', 'davis.json')))['answers']
for k, v in cal.items():
    if isinstance(v, dict) and v.get('spell'):
        seen[k].append((v['spell'].strip().lower(), v.get('say'), 'chunk'))

rep = {k: v for k, v in seen.items() if len(v) > 1}
agree = sum(1 for v in rep.values() if len({s for s, _, _ in v}) == 1)
print(f"chunks spelled more than once: {len(rep)}")
print(f"  spelled the same way every time: {agree}/{len(rep)}"
      f"  ({100*agree/max(1,len(rep)):.0f}%)\n")
print("where the same sound got two different spellings:")
for k, v in sorted(rep.items(), key=lambda x: -len({s for s, _, _ in x[1]})):
    sp = {s for s, _, _ in v}
    if len(sp) == 1: continue
    src = ', '.join(f"{s} ({w})" for s, w, _ in v)
    print(f"  {k:<20s} {src}")

# how close are those variants to each other, by the same yardstick used to
# score the renderer?
def close(a, b): return a == b or a[:3] == b[:3] or a[-3:] == b[-3:]
pairs = tot = 0
for v in rep.values():
    sp = sorted({s for s, _, _ in v})
    for i in range(len(sp)):
        for j in range(i+1, len(sp)):
            tot += 1; pairs += close(sp[i], sp[j])
if tot:
    print(f"\nself-agreement on the renderer's own yardstick: {pairs}/{tot}"
          f" = {100*pairs/tot:.0f}% 'within reach'")
    print("that is the number to beat, not 100%")

def self_agreement():
    """percentage, on the same yardstick evaluate.py uses"""
    if not tot: return None
    return 100 * pairs / tot
