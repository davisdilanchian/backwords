import subprocess, re, functools

# espeak-ng IPA -> ARPAbet. Longest match first.
PAIRS = [
    ("tʃ","CH"),("dʒ","JH"),
    ("eɪ","EY"),("aɪ","AY"),("aʊ","AW"),("ɔɪ","OY"),("oʊ","OW"),("əʊ","OW"),
    ("iː","IY"),("uː","UW"),("ɑː","AA"),("ɔː","AO"),("ɜː","ER"),("ɛː","EH"),("ɪː","IY"),
    ("ɪə","IH"),("ɛə","EH"),("ʊə","UH"),
    ("oː","AO"),("ᵻ","IH"),("ɪ̈","IH"),("ʉ","UW"),("ɵ","OW"),
    ("ɚ","ER"),("ɝ","ER"),("ɜ","ER"),
    ("ɪ","IH"),("ɛ","EH"),("æ","AE"),("ɑ","AA"),("ɔ","AO"),("ʊ","UH"),("ʌ","AH"),
    ("ə","AH"),("ɐ","AH"),("ɒ","AA"),("ɘ","AH"),("ɵ","OW"),
    ("i","IY"),("u","UW"),("e","EY"),("o","OW"),("a","AA"),
    ("ʃ","SH"),("ʒ","ZH"),("θ","TH"),("ð","DH"),("ŋ","NG"),
    ("ɹ","R"),("ɻ","R"),("ɾ","T"),("ʔ","T"),("ɫ","L"),("ɡ","G"),("ɜ","ER"),
    ("j","Y"),("x","K"),("ʍ","W"),("ç","HH"),
    ("b","B"),("d","D"),("f","F"),("g","G"),("h","HH"),("k","K"),("l","L"),
    ("m","M"),("n","N"),("p","P"),("r","R"),("s","S"),("t","T"),("v","V"),
    ("w","W"),("z","Z"),("y","IY"),("c","K"),("q","K"),
]
DROP = set("ˈˌːˑ|‖.,;!?()'’‍̯̩̥͡ʰ̞̈-")

@functools.lru_cache(maxsize=200000)
def _espeak_ipa(text, voice="en-us"):
    r = subprocess.run(["espeak-ng","-q","--ipa","-v",voice,"--", text],
                       capture_output=True, text=True)
    return r.stdout.strip()

def ipa_to_arpa(ipa):
    out, unknown = [], []
    i = 0
    while i < len(ipa):
        ch = ipa[i]
        if ch in DROP or ch.isspace():
            i += 1; continue
        for sym, arp in PAIRS:
            if ipa.startswith(sym, i):
                out.append(arp); i += len(sym); break
        else:
            unknown.append(ch); i += 1
    return out, unknown

def phones(text, voice="en-us"):
    """ARPAbet phone list for arbitrary text, via espeak-ng's own G2P."""
    return ipa_to_arpa(_espeak_ipa(text, voice))[0]

# ---- acoustic atomisation -------------------------------------------------
# Time-reversing audio does not reverse a phoneme list; it reverses the signal.
# Phonemes that are internally dynamic must be split into their moving parts
# first, or the comparison is meaningless.
ATOM = {
    "AY": ["AA","IY"], "EY": ["EH","IY"], "OY": ["AO","IY"],
    "AW": ["AA","UW"], "OW": ["AO","UW"],
    "CH": ["T","SH"],  "JH": ["D","ZH"],
    "ER": ["AH","R"],
}
def atomize(ph):
    out = []
    for p in ph:
        out.extend(ATOM.get(p,[p]))
    return out

def lev(a, b):
    if not a: return len(b)
    if not b: return len(a)
    prev = list(range(len(b)+1))
    for i, x in enumerate(a, 1):
        cur = [i]
        for j, y in enumerate(b, 1):
            cur.append(min(prev[j]+1, cur[j-1]+1, prev[j-1]+(x!=y)))
        prev = cur
    return prev[-1]

def per(target, got):
    return lev(target, got)/max(1,len(target))
