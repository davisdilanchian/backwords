"""What every English word ACTUALLY sounds like backwards. Measured, not assumed.

The speller this replaces assumed that reversing a recording reverses the list
of phonemes in it. reversal_matrix.py measured that assumption and found only
9 of 20 consonants survive reversal at all, so every spelling built on it was
built on something known to be false.

Nothing here is assumed. Each word is spoken, the waveform is reversed, and the
result is stored as what it is. To spell a line, tile the sound of that line
with these signatures and read the words back to front — the pieces are real
English because they were only ever real English, and they are right because
they were measured rather than derived.

    python3 build_reverse_index.py [n_words]     ->  revindex.npz
"""
import os, sys, json, subprocess, tempfile, wave, array
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

HERE = os.path.dirname(os.path.abspath(__file__))
SR = 16000
NFRAME = 16          # every signature resampled to this, so all comparisons are one matmul
NCEP = 13

def vocab(n):
    from wordfreq import top_n_list, zipf_frequency
    out = []
    for w in top_n_list('en', n * 3):
        if not w.isalpha() or not (1 <= len(w) <= 9): continue
        out.append((w, zipf_frequency(w, 'en')))
        if len(out) >= n: break
    return out

def say_many(words, wav_dir):
    """espeak writes one file per word; batched so the process cost amortises"""
    made = []
    for i, w in enumerate(words):
        p = os.path.join(wav_dir, f"{i}.wav")
        subprocess.run(["espeak-ng", "-v", "en-us", "-s", "150", "-w", p, "--", w],
                       check=True, capture_output=True)
        made.append(p)
        if i % 2000 == 0: print(f"   spoke {i}", flush=True)
    return made

def load_rev(path):
    """read, downsample to 16k mono, reverse — the reversal is the whole point"""
    out = path + ".16k.wav"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", path,
                    "-ar", str(SR), "-ac", "1", out], check=True)
    with wave.open(out, "rb") as w:
        n = w.getnframes(); raw = w.readframes(n)
    os.remove(out)
    a = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    return a[::-1].copy()

def sig(y):
    """fixed-size acoustic signature of a reversed word"""
    import librosa
    if len(y) < 400: return None
    y, _ = librosa.effects.trim(y, top_db=32)
    if len(y) < 400: return None
    m = librosa.feature.mfcc(y=y, sr=SR, n_mfcc=NCEP, hop_length=160)
    m = (m - m.mean(1, keepdims=True)) / (m.std(1, keepdims=True) + 1e-8)
    # resample the time axis so every word is comparable in one matrix multiply
    idx = np.linspace(0, m.shape[1] - 1, NFRAME)
    r = np.stack([np.interp(idx, np.arange(m.shape[1]), m[k]) for k in range(NCEP)])
    return r.astype(np.float32), len(y) / SR

def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 4000
    words = vocab(n)
    print(f"vocabulary: {len(words)} words")
    with tempfile.TemporaryDirectory() as td:
        paths = say_many([w for w, _ in words], td)
        keep, sigs, durs, zs = [], [], [], []
        for (w, z), p in zip(words, paths):
            try:
                s = sig(load_rev(p))
            except Exception:
                s = None
            if s is None: continue
            keep.append(w); sigs.append(s[0]); durs.append(s[1]); zs.append(z)
            if len(keep) % 2000 == 0: print(f"   signed {len(keep)}", flush=True)
    S = np.stack(sigs)
    np.savez_compressed(os.path.join(HERE, "revindex.npz"),
                        words=np.array(keep), sig=S,
                        dur=np.array(durs, dtype=np.float32),
                        zipf=np.array(zs, dtype=np.float32))
    print(f"\nwrote revindex.npz: {len(keep)} words, signatures {S.shape}")
    print(f"durations {np.min(durs):.2f}–{np.max(durs):.2f}s, median {np.median(durs):.2f}s")

if __name__ == "__main__":
    main()
