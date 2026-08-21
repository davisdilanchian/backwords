"""Ship the style to the browser: what the page needs, and nothing else."""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render_style import load_style, PAIR, VOWELS, HEAD_BEFORE, letters

HERE = os.path.dirname(os.path.abspath(__file__))
st = load_style()
out = {
  "who": "davis",
  # one best spelling per phone, already blended with position the same way
  "phone": {p: letters(p, "MC", st, False) for p in st['phone']},
  "pair": {f"{a} {b}": v for (a, b), v in PAIR.items()},
  "vowels": sorted(VOWELS),
  "headBefore": ''.join(sorted(HEAD_BEFORE)),
  "exact": st['exact'],
}
p = os.path.join(os.path.dirname(HERE), 'data', 'style.json')
json.dump(out, open(p, 'w'))
print(f"data/style.json  {len(json.dumps(out))} bytes, {len(out['exact'])} hand-written overrides")
