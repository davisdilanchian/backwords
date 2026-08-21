"""What rules are hiding in a person's spellings?

46 answers is not 46 facts, it is a handful of rules applied 46 times. Aligning
each phone chunk against how it was actually written recovers them, and rules
generalise to the other 74,000 entries in a way a lookup table never could.
"""
import os, sys, json, collections, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

HERE = os.path.dirname(os.path.abspath(__file__))
d = json.load(open(os.path.join(HERE, 'calibration', 'davis.json')))
ans = d['answers']

rows = sorted(((v['at'], k, v['say'], v['spell']) for k, v in ans.items()))
print(f"{len(rows)} answers\n")
print("in the order they were given:")
for at, k, say, sp in rows:
    print(f"  {at[11:19]}  said {say:<8s}  chunk {k:<10s}  wrote {sp}")

# the most obvious thing first: how many begin with an h that the chunk does not?
lead_h = [r for r in rows if r[3].startswith('h') and not r[1].split()[0] == 'HH']
print(f"\nspellings starting with 'h' where the chunk has no /h/: {len(lead_h)}/{len(rows)}")
early = [r for r in rows[:len(rows)//2] if r[3].startswith('h')]
late  = [r for r in rows[len(rows)//2:] if r[3].startswith('h')]
print(f"  first half {len(early)}/{len(rows)//2}   second half {len(late)}/{len(rows)-len(rows)//2}"
      "   (the convention settles as the session goes on)")

# which letters show up for chunks containing each phone
byphone = collections.defaultdict(collections.Counter)
for at, k, say, sp in rows:
    for p in k.split():
        byphone[p][sp] += 1
print("\nhow chunks containing each phone got written:")
for p in sorted(byphone, key=lambda x: -sum(byphone[x].values())):
    if sum(byphone[p].values()) < 2: continue
    print(f"  {p:<4s} {', '.join(s for s, _ in byphone[p].most_common(7))}")
