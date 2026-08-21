"""Phones for the line somebody typed.

Shared by the renderer and by every measurement script, so neither has to
import the other. CMUdict decides how the input is pronounced; espeak-ng only
fills in for words it has never heard of.
"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from g2p import atomize, phones as espeak_phones

HERE = os.path.dirname(os.path.abspath(__file__))
CMU = json.load(open(os.path.join(HERE, 'cmudict.json')))

def word_phones(w):
    """atomised phones for one word"""
    w = ''.join(c for c in w.lower() if c.isalpha() or c == "'")
    if not w: return []
    p = CMU.get(w) or CMU.get(w.replace("'", ""))
    return atomize([x.rstrip('012') for x in p]) if p else atomize(espeak_phones(w))

def target_for(text):
    """what the reversed take has to sound like, as atomised phones"""
    out = []
    for w in text.lower().split():
        out.extend(word_phones(w))
    return out[::-1]
