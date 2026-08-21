"""How readable is the script, as opposed to how accurate?

espeak-ng reads invented syllables perfectly, so phone error rate cannot see
the difference between "moss is a dour tissue" and "slesh eess sless eesh".
A person can. These are the numbers that track what a person has to do.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wordfreq import zipf_frequency

def is_word(tok, floor=3.0):
    return zipf_frequency(tok, 'en') >= floor

def score(tokens):
    """fraction that are real words, how common they are, how many pieces"""
    if not tokens: return dict(real=0.0, zipf=0.0, n=0)
    return dict(
        real=sum(1 for t in tokens if is_word(t)) / len(tokens),
        zipf=sum(zipf_frequency(t, 'en') for t in tokens) / len(tokens),
        n=len(tokens),
    )
