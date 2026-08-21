"""Learn a person's reversed-speech orthography from their answers.

Each answer pairs a phone chunk with how that person wrote it. Aligning the two
recovers which letters they use for each phone, and in which position. That
generalises: the same rules can respell the whole index, not just the chunks
they happened to be asked about.

The alignment is EM. Start from a rough guess at what letters a phone might
take, find the best split of each spelling under that guess, re-count, repeat.
"""
import os, sys, json, math, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
HERE = os.path.dirname(os.path.abspath(__file__))

SEED = {
 "AA":["aw","ah","a","o","aa"], "AE":["ah","a","av"], "AH":["uh","u","a","e"],
 "AO":["aw","ow","o","au"], "EH":["e","eh","a"], "IH":["i","ee","ih","y"],
 "IY":["ee","e","ea","y"], "UH":["oo","u"], "UW":["oo","ew","ou","u"],
 "B":["b","bb"], "D":["d","th","dd"], "DH":["th","v","the"],
 "F":["f","ff"], "G":["g","gh"], "HH":["h"], "K":["kh","k","ck","c"],
 "L":["l","ll","le"], "M":["m","mm"], "N":["n","nn","gn"], "NG":["n","ng","gn"],
 "P":["p","ph"], "R":["r","rr","er"], "S":["s","ss","c"], "SH":["sh"],
 "T":["th","t","sth","tt"], "TH":["th","kht"], "V":["v","vv"], "W":["w","u","wu"],
 "Y":["y","i"], "Z":["z","s","zz"], "ZH":["zh","g"],
}
MAXLET = 4
VOWELS = set("AA AE AH AO EH IH IY UH UW".split())

def ctx_of(ph, i):
    """where this phone sits: first in the piece, and what follows it.

    Enough to carry the two rules single sounds could never show. A close vowel
    running into another vowel is written as a glide; a vowel run gets squashed,
    which shows up as one of the pair emitting nothing at all.
    """
    return ('I' if i == 0 else 'M') + ('V' if i + 1 < len(ph) and ph[i+1] in VOWELS else 'C')

def load(path):
    d = json.load(open(path))
    a = d.get('answers', d)
    return [(k.split(), v['spell'].strip().lower(), v.get('say'))
            for k, v in a.items() if isinstance(v, dict) and v.get('spell')]

def load_lines(skip=None):
    """word-level pairs from lines somebody spelled by hand.

    Worth more than the single-sound answers: glides, squashed vowel runs and
    dropped breaths only happen at word length, so this is where those rules
    come from. `skip` holds a line out so it can be scored honestly.
    """
    from lexicon import word_phones
    out = []
    d = os.path.join(HERE, 'calibration')
    for f in sorted(os.listdir(d)) if os.path.isdir(d) else []:
        if not f.startswith('lines'): continue
        for r in json.load(open(os.path.join(d, f))).get('lines', []):
            if skip and r['line'] == skip: continue
            ws, ts = r['line'].split(), r['mine'].lower().split()
            if len(ws) != len(ts): continue
            for w, t in zip(reversed(ws), ts):
                ph = word_phones(w)[::-1]
                if ph: out.append((ph, t, w))
    return out

def strip_head(phones, word):
    """peel the breathy onset reversed speech puts in front of a chunk"""
    if word.startswith('h') and phones and phones[0] != 'HH' and len(word) > 1:
        return 'h', word[1:]
    return '', word

def best_split(phones, word, logp, head_lp):
    """split `word` across `phones`, after the onset has been peeled off"""
    n, L = len(phones), len(word)
    NEG = -1e9
    best = [[NEG]*(L+1) for _ in range(n+1)]
    back = [[None]*(L+1) for _ in range(n+1)]
    best[0][0] = 0.0
    for i in range(n):
        for j in range(L+1):
            if best[i][j] == NEG: continue
            for k in range(0, min(MAXLET, L-j)+1):
                s = best[i][j] + logp((phones[i], ctx_of(phones, i)), word[j:j+k])
                if s > best[i+1][j+k]:
                    best[i+1][j+k] = s; back[i+1][j+k] = (j, k)
    if best[n][L] == NEG: return None, NEG
    out, i, j = [], n, L
    while i > 0:
        pj, k = back[i][j]
        out.append((phones[i-1], word[pj:pj+k])); i -= 1; j = pj
    out.reverse()
    return out, best[n][L]

def train(pairs, rounds=8):
    cnt = collections.defaultdict(collections.Counter)
    for p, opts in SEED.items():
        for i, o in enumerate(opts):
            if o.startswith('h') and p != 'HH': continue
            cnt[p][o] += 6 - min(4, i)
    head = collections.Counter({"h": 8, "": 8})
    for _ in range(rounds):
        def logp(pc, g):
            p, _ = pc
            # only /h/ may be written with a leading h; anything else forces the
            # breathy onset out into the head, where it belongs as a rule
            if g.startswith('h') and p != 'HH': return -1e9
            c = cnt.get(pc) or cnt.get(p) or collections.Counter()
            back = cnt.get(p) or collections.Counter()
            tot = sum(c.values()) + sum(back.values()) + 40
            n = c.get(g, 0) + 0.4 * back.get(g, 0)
            return math.log((n + (0.7 if g else 0.25)) / tot)
        def head_lp(g):
            tot = sum(head.values()) + 6
            return math.log((head.get(g, 0) + 0.3) / tot)
        nc = collections.defaultdict(collections.Counter); nh = collections.Counter()
        for phones, word, _ in pairs:
            h, rest = strip_head(phones, word)
            nh[(h, phones[0] if phones else '')] += 1     # the onset depends on what follows
            nh[h] += 1
            al, sc = best_split(phones, rest, logp, head_lp)
            if not al: continue
            for i, (p, g) in enumerate(al):
                nc[(p, ctx_of(phones, i))][g] += 1
                nc[p][g] += 1
        for p, opts in SEED.items():
            for i, o in enumerate(opts):
                if o.startswith('h') and p != 'HH': continue
                nc[p][o] += 2 - min(1, i)
        nh["h"] += 2; nh[""] += 2
        cnt, head = nc, nh
    return cnt, head

def build(skip=None):
    pairs = load(os.path.join(HERE, 'calibration', 'davis.json')) + load_lines(skip)
    return train(pairs), pairs
def report(cnt, head, pairs):
  print(f"learned from {len(pairs)} pairs\n")
  print("chunk-initial flourish:", dict(head.most_common(5)))
  print("\nletters this person uses for each phone (most used first):")
  for p in sorted((k for k in cnt if not isinstance(k, tuple)),
                  key=lambda x: -sum(cnt[x].values())):
    tops = [g for g, c in cnt[p].most_common(4) if c > 0]
    if tops: print(f"  {p:<4s} {', '.join(repr(t) for t in tops)}")
  print("\ncontext changes it — same phone, different company:")
  for p in ("UW", "IY", "AO", "K", "AA"):
    for c in ("IV", "IC", "MV", "MC"):
      e = cnt.get((p, c))
      if e: print(f"  {p:<3s} {c}  {', '.join(repr(g) for g, n in e.most_common(2))}")
  save(cnt, head)
  print("\nwrote calibration/style.json")

def save(cnt, head, path=None):
  phone, byctx = {}, {}
  for k, c in cnt.items():
    if isinstance(k, tuple):
      byctx[f"{k[0]}|{k[1]}"] = c.most_common(3)
    else:
      phone[k] = c.most_common(6)
  onset = {}
  for k, n in head.items():
    if isinstance(k, tuple) and k[1]:
      onset.setdefault(k[1], {})[k[0] or '-'] = n
  json.dump({"phone": phone, "ctx": byctx, "onset": onset,
             "head": [(k, v) for k, v in head.items() if not isinstance(k, tuple)]},
            open(path or os.path.join(HERE, 'calibration', 'style.json'), 'w'), indent=1)

if __name__ == '__main__':
    (cnt, head), pairs = build()
    report(cnt, head, pairs)
