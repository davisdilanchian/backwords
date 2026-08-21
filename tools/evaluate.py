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
CMU = json.load(open(os.path.join(HERE, 'cmudict.json')))

BRIDGE = r'''
const fs = require('fs');
const SCRIPTER = require(process.argv[2]);
SCRIPTER.load(fs.readFileSync(process.argv[3], 'utf8'),
              fs.readFileSync(process.argv[4], 'utf8'));
const lines = fs.readFileSync(0, 'utf8').split('\n').filter(Boolean);
process.stdout.write(JSON.stringify(lines.map(l => {
  const r = SCRIPTER.make(l);
  return { line: l, script: r.parts.map(p => p.spell).join(' '), accuracy: r.accuracy };
})));
'''

def target_for(text):
    out = []
    for w in text.lower().split():
        w = ''.join(c for c in w if c.isalpha() or c == "'")
        if not w: continue
        p = CMU.get(w) or CMU.get(w.replace("'", ""))
        out.extend([x.rstrip('012') for x in p] if p else espeak_phones(w))
    return atomize(out)[::-1]

def run(lines):
    bp = os.path.join(HERE, '_bridge.js')
    open(bp, 'w').write(BRIDGE)
    try:
        r = subprocess.run(['node', bp, os.path.join(ROOT, 'script.js'),
                            os.path.join(ROOT, 'data/lex.txt'),
                            os.path.join(ROOT, 'data/idx.txt')],
                           input='\n'.join(lines), capture_output=True, text=True)
        if r.returncode: raise SystemExit(r.stderr)
        return json.loads(r.stdout)
    finally:
        os.remove(bp)

def report(name, path):
    lines = [l.strip() for l in open(os.path.join(HERE, path)) if l.strip()]
    rows, tot, exact, good = run(lines), 0.0, 0, 0
    worst = []
    for row in rows:
        want = target_for(row['line'])
        got = atomize(espeak_phones(row['script']))
        p = per(want, got)
        tot += p; exact += (p == 0); good += (p <= 0.20)
        worst.append((p, row['line'], row['script'], ' '.join(want), ' '.join(got)))
    n = len(rows)
    print(f"{name:9s} n={n:3d}  mean PER {tot/n:.4f}   exact {exact}/{n}"
          f"   PER<=0.20 {good}/{n} ({100*good/n:.0f}%)")
    return sorted(worst, reverse=True)

if __name__ == '__main__':
    w = report('testset', 'testset.txt')
    report('holdout', 'holdout.txt')
    if '-v' in sys.argv:
        print("\nworst cases:")
        for p, l, s, want, got in w[:8]:
            print(f"  PER {p:.2f}  {l}\n     script {s}\n     want   {want}\n     got    {got}")
