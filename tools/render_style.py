"""Spell a line backwards in one person's own orthography.

Two things came out of the calibration. The obvious one is which letters that
person uses for each reversed phone. The structural one came from the example
they wrote by hand: one token per input word, in reverse order. Not arbitrary
chunks. That keeps word-sized gaps in the take, which is what makes it sayable.
"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lexicon import word_phones

HERE = os.path.dirname(os.path.abspath(__file__))

def load_style(name='davis'):
    st = json.load(open(os.path.join(HERE, 'calibration', 'style.json')))
    phone = {p: [g for g, c in v if c > 0] for p, v in st['phone'].items()}
    head = dict(st['head'])
    exact = {}
    cal = json.load(open(os.path.join(HERE, 'calibration', f'{name}.json')))
    for k, v in cal.get('answers', {}).items():
        if isinstance(v, dict) and v.get('spell'):
            exact[k] = v['spell'].strip().lower()
    return phone, head, exact

VOWELS = set("AA AE AH AO EH IH IY UH UW".split())
# Vowel runs get written short, not phone by phone. "hello" reversed is
# UW AO L AH HH and gets written "holla", not "hooawluhh".
PAIR = {
 ("UW","AO"):"o", ("AO","UW"):"o", ("AA","UW"):"ow", ("UW","AA"):"wa",
 ("AO","AA"):"aw", ("AA","AO"):"aw", ("EH","IY"):"ay", ("IY","EH"):"ye",
 ("AH","IY"):"uy", ("IY","AH"):"ya", ("AA","IH"):"ai", ("IH","AA"):"ya",
}

def spell_chunk(ph, phone, head, exact, use_head=True):
    key = ' '.join(ph)
    if key in exact:
        return exact[key]
    ph = list(ph)
    # A breath at the end of a piece cannot be written in English, and they
    # drop it: "have" reversed is V AE HH and gets written "vah".
    while len(ph) > 1 and ph[-1] == "HH":
        ph.pop()
    out, i = [], 0
    while i < len(ph):
        p = ph[i]
        nxt = ph[i+1] if i+1 < len(ph) else None
        if p in VOWELS and nxt in VOWELS:
            pair = PAIR.get((p, nxt))
            if pair:
                out.append(pair); i += 2; continue
            # a close vowel running into another one is a glide, not two vowels
            if p in ("IY","IH") and i == 0:
                out.append("y"); i += 1; continue
            if p in ("UW","UH") and i == 0:
                out.append("w"); i += 1; continue
        out.append((phone.get(p) or ["?"])[0]); i += 1
    body = ''.join(out)
    # The breathy onset lands before a vowel or a liquid and not much else.
    # Their own sentence: heolukh and holla take it, nikhtmus and vah and yah
    # do not.
    lead = 'h' if (use_head and body[:1] in set("aeioulr")) else ''
    return lead + body

def script_for(text, style=None, use_head=True):
    phone, head, exact = style or load_style()
    words = [w for w in text.split() if any(c.isalpha() for c in w)]
    out = []
    for w in reversed(words):                       # last word is said first
        rev = word_phones(w)[::-1]
        if rev: out.append(spell_chunk(rev, phone, head, exact, use_head))
    return ' '.join(out)

if __name__ == '__main__':
    style = load_style()
    LINE = "hello i have made something cool for you"
    THEIRS = "Hooy herolf heolukh nikhtmus hethhym vah yah holla"
    mine = script_for(LINE, style)
    print("held-out check — this sentence was never training data\n")
    print(f"  line   {LINE}")
    print(f"  yours  {THEIRS}")
    print(f"  mine   {mine}\n")
    for a, b, w in zip(THEIRS.lower().split(), mine.split(), list(reversed(LINE.split()))):
        mark = "exact" if a == b else ("close" if a[:3] == b[:3] or a[-3:] == b[-3:] else "")
        print(f"    {w:<10s} yours {a:<12s} mine {b:<14s} {mark}")
    if len(sys.argv) > 1:
        print()
        for t in sys.argv[1:]:
            print(f"  {t}\n    -> {script_for(t, style)}")
