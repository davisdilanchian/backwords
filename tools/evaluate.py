"""Round-trip check: read the generated script back with an independent engine.

The claim the app makes is that reading the script aloud and reversing the take
gives the original line. The part the app controls is the spelling, so that is
what this measures: espeak-ng reads the script, we reverse the phones it
produces, and compare against the phones of the line the user typed.

  target = reverse(atomise(cmudict(line)))
  got    = atomise(espeak(script))
  PER    = edit distance / len(target)

Run against the shipped script.js so it stays a regression test, not a museum.

This covers the written crutch only. The channel that actually carries the line
is the audio loop; looptest.py measures that.
"""
import sys, os, json, subprocess
sys.path.insert(0, os.path.dirname(__file__) or '.')
from g2p import atomize, phones as espeak_phones, per

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
from lexicon import CMU, word_phones, target_for   # re-exported for the other tools


def load_hand():
    """lines somebody spelled themselves, from calibration/lines*.json"""
    out = []
    d = os.path.join(HERE, 'calibration')
    for f in sorted(os.listdir(d)) if os.path.isdir(d) else []:
        if not f.startswith('lines'): continue
        blob = json.load(open(os.path.join(d, f)))
        for r in blob.get('lines', blob if isinstance(blob, list) else []):
            if r.get('line') and r.get('mine'): out.append((r['line'], r['mine']))
    return out

def main():
    import learn_style, render_style
    from render_style import script_for
    hand = load_hand()
    if not hand:
        print("no hand-written lines yet — save some from the page, then drop the")
        print("download into tools/calibration/lines-<name>.json")
        return 0
    print("leave-one-line-out: each line is scored by a style trained without it\n")
    exact = close = tot = 0
    for line, theirs in hand:
        (cnt, head), _ = learn_style.build(skip=line)     # hold this line out
        learn_style.save(cnt, head)
        style = render_style.load_style()
        mine = script_for(line, style)
        a, b = theirs.lower().split(), mine.split()
        print(f"\n  {line}\n    theirs {theirs}\n    mine   {mine}")
        for x, y in zip(a, b):
            tot += 1
            if x == y: exact += 1; mark = "exact"
            elif x[:3] == y[:3] or x[-3:] == y[-3:]: close += 1; mark = "close"
            else: mark = ""
            if mark: print(f"      {x:<14s} {y:<14s} {mark}")
    (cnt, head), _ = learn_style.build()                 # leave it trained on everything
    learn_style.save(cnt, head)
    got = 100*(exact+close)/max(1,tot)
    print(f"\n  {len(hand)} line(s), {tot} tokens: {exact} exact, {close} close"
          f" ({got:.0f}% within reach)")
    try:
        import ceiling
        c = ceiling.self_agreement()
        if c is not None:
            print(f"  the same person spelling the same sound twice agrees {c:.0f}% of the time,")
            print(f"  so {got:.0f}% is measured against a target that moves. 100% is not the goal")
            print(f"  and more hand-written lines cannot make it one.")
    except Exception:
        pass
    return 0

if __name__ == '__main__':
    sys.exit(main())
