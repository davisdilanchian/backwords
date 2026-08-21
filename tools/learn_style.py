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

def load(path):
    d = json.load(open(path))
    a = d.get('answers', d)
    return [(k.split(), v['spell'].strip().lower(), v.get('say'))
            for k, v in a.items() if isinstance(v, dict) and v.get('spell')]

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
                s = best[i][j] + logp(phones[i], word[j:j+k])
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
        def logp(p, g):
            # only /h/ may be written with a leading h; anything else forces the
            # breathy onset out into the head, where it belongs as a rule
            if g.startswith('h') and p != 'HH': return -1e9
            c = cnt[p]; tot = sum(c.values()) + 40
            return math.log((c.get(g, 0) + (0.7 if g else 0.25)) / tot)
        def head_lp(g):
            tot = sum(head.values()) + 6
            return math.log((head.get(g, 0) + 0.3) / tot)
        nc = collections.defaultdict(collections.Counter); nh = collections.Counter()
        for phones, word, _ in pairs:
            h, rest = strip_head(phones, word)
            nh[h] += 1
            al, sc = best_split(phones, rest, logp, head_lp)
            if not al: continue
            for p, g in al: nc[p][g] += 1
        for p, opts in SEED.items():
            for i, o in enumerate(opts): nc[p][o] += 2 - min(1, i)
        nh["h"] += 2; nh[""] += 2
        cnt, head = nc, nh
    return cnt, head

pairs = load(os.path.join(HERE, 'calibration', 'davis.json'))
cnt, head = train(pairs)
print(f"learned from {len(pairs)} answers\n")
print("chunk-initial flourish:", dict(head.most_common(5)))
print("\nletters this person uses for each phone (most used first):")
for p in sorted(cnt, key=lambda x: -sum(cnt[x].values())):
    tops = [g for g, c in cnt[p].most_common(4) if c > 0]
    if tops: print(f"  {p:<4s} {', '.join(repr(t) for t in tops)}")
json.dump({"phone": {p: cnt[p].most_common(6) for p in cnt},
           "head": head.most_common(4)},
          open(os.path.join(HERE, 'calibration', 'style.json'), 'w'), indent=1)
print("\nwrote calibration/style.json")
