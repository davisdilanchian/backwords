"""The real objective. The user reads S; we reverse the take; it must sound like T.
   reverse(audio(S)) ~= audio(T)   <=>   audio(S) ~= reverse(audio(T))
So the thing the reader must imitate is REV_T = reverse(audio(T)).
We score any candidate script S by how close its FORWARD audio is to REV_T."""
import sys, os, tempfile, numpy as np, librosa
sys.path.insert(0, __import__('os').path.dirname(__file__) or '.')
from audio import tts, reverse_wav

def wav_of(text, reverse=False, voice="en-us", speed=150):
    td = tempfile.mkdtemp()
    f = os.path.join(td, "a.wav"); tts(text, f, voice=voice, speed=speed)
    if reverse:
        r = os.path.join(td, "b.wav"); reverse_wav(f, r); f = r
    return f

def feats(path):
    y, sr = librosa.load(path, sr=16000)
    y, _ = librosa.effects.trim(y, top_db=32)
    m = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13, hop_length=160)
    d = librosa.feature.delta(m)
    X = np.vstack([m, d])
    X = (X - X.mean(1, keepdims=True)) / (X.std(1, keepdims=True) + 1e-8)
    return X.T

def dist(a, b):
    D, wp = librosa.sequence.dtw(X=a.T, Y=b.T, metric="cosine")
    return D[-1, -1] / len(wp)

def score_script(target_text, script, voice="en-us"):
    """lower = the reversed take sounds more like the target"""
    rev_t = feats(wav_of(target_text, reverse=True, voice=voice))
    fwd_s = feats(wav_of(script,      reverse=False, voice=voice))
    return dist(rev_t, fwd_s)
