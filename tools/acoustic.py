import sys, os, tempfile, subprocess, numpy as np, librosa
sys.path.insert(0,'.')
from audio import tts, reverse_wav

def mfcc(path):
    y, sr = librosa.load(path, sr=16000)
    y, _ = librosa.effects.trim(y, top_db=35)
    m = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13, hop_length=160)
    m = (m - m.mean(axis=1, keepdims=True)) / (m.std(axis=1, keepdims=True) + 1e-8)
    return m.T

def dtw_dist(a, b):
    """length-normalised DTW distance between two MFCC sequences"""
    D, wp = librosa.sequence.dtw(X=a.T, Y=b.T, metric='cosine')
    return D[-1, -1] / len(wp)

def render(text, reverse=False, voice="en-us", speed=150):
    td = tempfile.mkdtemp()
    f = os.path.join(td, "a.wav")
    tts(text, f, voice=voice, speed=speed)
    if reverse:
        r = os.path.join(td, "b.wav"); reverse_wav(f, r); f = r
    return f

def compare(original_text, script, voice_script="en-us", speed=150):
    a = render(original_text, voice="en-us+f3", speed=150)   # reference rendition
    b = render(script, reverse=True, voice=voice_script, speed=speed)
    return dtw_dist(mfcc(a), mfcc(b))
