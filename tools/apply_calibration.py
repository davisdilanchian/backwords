"""Fold your spellings into the index, at the top of the pile.

    python3 build_index.py
    python3 apply_calibration.py backwords-spellings.json
    python3 pack.py

The index normally ranks spellings by how espeak-ng reads them back. espeak
reads invented syllables perfectly, so it cannot tell a readable script from an
unreadable one. Where you have given an answer, yours wins outright — you are
the one who has to read it, which makes your spelling correct by definition.

Pass --preview to see what changes before committing to it.
"""
import os, sys, json, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from g2p import atomize, phones as espeak_phones, per

HERE = os.path.dirname(os.path.abspath(__file__))
IDXF = os.path.join(HERE, 'index.json')

def load_answers(path):
    d = json.load(open(path))
    a = d.get('answers', d)
    return {k: v['spell'] if isinstance(v, dict) else v for k, v in a.items() if (v or {})}

def main():
    args = [x for x in sys.argv[1:] if not x.startswith('-')]
    preview = '--preview' in sys.argv
    if not args:
        print(__doc__); return 2
    answers = load_answers(args[0])
    idx = json.load(open(IDXF))
    units = {r['key']: r for r in json.load(open(os.path.join(HERE, 'units.json')))}

    applied = new_key = 0
    disagree = []
    for key, spell in answers.items():
        spell = (spell or '').strip().lower()
        if not spell: continue
        # informational only: what espeak thinks your spelling says
        got = atomize(espeak_phones(spell))
        want = key.split()
        d = per(want, got)
        if d > 0.34:
            disagree.append((d, key, spell, ' '.join(got), units.get(key, {}).get('say')))
        if key not in idx: idx[key] = []; new_key += 1
        idx[key] = [[spell, 0.02, 1]] + [e for e in idx[key] if e[0] != spell]
        applied += 1

    print(f"spellings applied : {applied}   (keys the index did not have before: {new_key})")
    if units:
        tot = sum(r['weight'] for r in units.values())
        cov = sum(units[k]['weight'] for k in answers if k in units)
        print(f"covers            : {100*cov/tot:.0f}% of everything the app emits")
    print(f"\nespeak reads these differently than the chunk asks for ({len(disagree)}).")
    print("That is expected where your ear and a synthesiser disagree — yours ships anyway:")
    for d, key, spell, got, say in sorted(disagree, reverse=True)[:12]:
        print(f"   said {str(say):<10s} -> you wrote {spell:<12s} chunk wants {key:<14s} espeak hears {got}")

    if preview:
        print("\n--preview: nothing written")
        return 0
    json.dump(idx, open(IDXF, 'w'))
    print(f"\nwrote index.json — now run: python3 pack.py")
    return 0

if __name__ == '__main__':
    sys.exit(main())
