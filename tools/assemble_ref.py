import sys, json, os
sys.path.insert(0,'.')

IDX = json.load(open(os.path.join(os.path.dirname(__file__) or '.', 'index.json')))

ALL = ("AA AE AH AO EH ER IH IY UH UW B CH D DH F G HH JH K L M N NG "
       "P R S SH T TH V W Y Z ZH").split()
# phones that survive a reversal as each other, so a swap costs little
NEARSET = [set(x.split()) for x in [
  "AA AH","AA AE","AA AO","AE EH","AH AE","IH IY","UH UW","AH ER","AH IH",
  "EH EY","W UW","Y IY","T D","P B","K G","S Z","F V","TH DH","SH ZH",
  "M N","N NG","L R","HH AH","ER R",
]]
NEAR = {}
for p in ALL:
    NEAR[p] = [q for q in ALL if q != p and any({p,q} <= g for g in NEARSET)]
# phones that turn up as epenthesis between awkward clusters
EPEN = "AH IH UH IY UW EH AA ER W Y R HH".split()

class Cfg:
    err_sub_near = 1.0     # swap for an acoustically close phone
    err_sub_far  = 3.0
    err_ins      = 1.6     # script says a phone the target does not have
    err_del      = 2.2     # target phone the script never says
    w_err        = 3.4     # how much one phone error is worth
    chunk        = 0.55    # bias toward fewer, longer pieces
    maxlen       = 7
    max_err      = 2

def _variants(want, cfg):
    """(index-key, error-cost, n-errors) within one or two edits of `want`."""
    out = [(" ".join(want), 0.0, 0)]
    L = len(want)
    for k in range(L):
        for alt in NEAR[want[k]]:
            out.append((" ".join(want[:k]+[alt]+want[k+1:]), cfg.err_sub_near, 1))
        if L > 1:
            out.append((" ".join(want[:k]+want[k+1:]), cfg.err_del, 1))   # phone dropped
    for k in range(L+1):
        for e in EPEN:
            out.append((" ".join(want[:k]+[e]+want[k:]), cfg.err_ins, 1))
    return out

def edges(target, i, cfg):
    out = []
    hi = min(i+cfg.maxlen, len(target))
    for j in range(i+1, hi+1):
        want = target[i:j]
        for key, ecost, ne in _variants(want, cfg):
            ent = IDX.get(key)
            if not ent: continue
            for spell, c in ent[:3]:
                out.append((j, spell, c + cfg.w_err*ecost))
    return out

def assemble(target, cfg=Cfg):
    n = len(target); INF = float('inf')
    best = [INF]*(n+1); back = [None]*(n+1); best[0] = 0.0
    for i in range(n):
        if best[i] == INF: continue
        cand = edges(target, i, cfg) or [(i+1, "uh", cfg.w_err*4)]
        for j, spell, c in cand:
            v = best[i] + c + cfg.chunk
            if v < best[j]:
                best[j] = v; back[j] = (i, spell)
    parts, j = [], n
    while j > 0:
        i, spell = back[j]; parts.append(spell); j = i
    return list(reversed(parts))
