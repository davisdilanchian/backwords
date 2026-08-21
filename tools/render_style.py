"""Spell a line backwards in one person's own orthography.

Learned from someone saying words, hearing them reversed, and writing what they
would have to read to make that sound. Two things came out of it.

The letters: reversed /t/ arrives fricated and gets written th or sth, reversed
/k/ becomes kh, most pieces open on a breath. Those spellings are compensating
rather than describing — saying a fricated "sth" forward reverses into a clean
/t| and saying "t" does not, because the burst-then-aspiration order that marks
a stop is exactly what reversal destroys.

The structure, from lines they wrote by hand: one token per input word, in
reverse order, which keeps word-sized gaps in the take.
"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lexicon import word_phones

HERE = os.path.dirname(os.path.abspath(__file__))
VOWELS = set("AA AE AH AO EH IH IY UH UW".split())

# Vowel runs get written short, not phone by phone: "hello" reversed is
# UW AO L AH HH and comes out "holla", not "hooawluhh".
PAIR = {
 ("UW","AO"):"o", ("AO","UW"):"o", ("UW","AA"):"aw", ("AA","UW"):"ow",
 ("AO","AA"):"aw", ("AA","AO"):"aw", ("EH","IY"):"ay", ("IY","EH"):"ye",
 ("AH","IY"):"uy", ("IY","AH"):"ya", ("AA","IH"):"ai", ("IH","AA"):"ya",
}
HEAD_BEFORE = set("aeioulr")
CTX_W, BACK_W = 1.0, 0.45

def load_style(name='davis'):
    st = json.load(open(os.path.join(HERE, 'calibration', 'style.json')))
    exact = {}
    cal = json.load(open(os.path.join(HERE, 'calibration', f'{name}.json')))
    for k, v in cal.get('answers', {}).items():
        if isinstance(v, dict) and v.get('spell'):
            exact[k] = v['spell'].strip().lower()
    return dict(phone=st['phone'], ctx=st.get('ctx', {}),
                onset=st.get('onset', {}), exact=exact)

def ctx_of(ph, i):
    return ('I' if i == 0 else 'M') + ('V' if i + 1 < len(ph) and ph[i+1] in VOWELS else 'C')

def letters(p, c, style, use_ctx):
    """Best letters for this phone. Position matters, but with few examples a
    single sighting must not outvote the phone's overall habit."""
    score = {}
    if use_ctx:
        for g, n in style['ctx'].get(f"{p}|{c}", []): score[g] = score.get(g, 0) + CTX_W * n
    for g, n in style['phone'].get(p, []): score[g] = score.get(g, 0) + BACK_W * n
    return max(score, key=score.get) if score else "?"

def spell_chunk(ph, style, use_head=True, use_ctx=False):
    key = ' '.join(ph)
    if key in style['exact']:
        return style['exact'][key]
    ph = list(ph)
    # a breath at the end of a piece has no English spelling, and they drop it
    while len(ph) > 1 and ph[-1] == "HH":
        ph.pop()
    out, i = [], 0
    while i < len(ph):
        p, nxt = ph[i], (ph[i+1] if i+1 < len(ph) else None)
        if not use_ctx and p in VOWELS and nxt in VOWELS:
            pair = PAIR.get((p, nxt))
            if pair: out.append(pair); i += 2; continue
            # a close vowel running into another is a glide, not two vowels
            if i == 0 and p in ("IY", "IH"): out.append("y"); i += 1; continue
            if i == 0 and p in ("UW", "UH"): out.append("w"); i += 1; continue
        out.append(letters(p, ctx_of(ph, i), style, use_ctx)); i += 1
    body = ''.join(out)
    lead = 'h' if (use_head and body[:1] in HEAD_BEFORE) else ''
    return lead + body

def script_for(text, style=None, use_head=True, use_ctx=False):
    style = style or load_style()
    words = [w for w in text.split() if any(c.isalpha() for c in w)]
    out = []
    for w in reversed(words):                       # last word is said first
        rev = word_phones(w)[::-1]
        if rev: out.append(spell_chunk(rev, style, use_head, use_ctx))
    return ' '.join(out)

if __name__ == '__main__':
    style = load_style()
    for t in (sys.argv[1:] or ["hello i have made something cool for you"]):
        print(f"  {t}\n    -> {script_for(t, style)}")
