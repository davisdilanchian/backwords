"""Settle the open question with a real voice, on a machine that can reach one.

Every measurement in this project has espeak-ng on at least one side, and espeak
is a formant synthesiser: its stop bursts are not a person's stop bursts. That
is not a footnote. It is why an experiment here concluded pre-aspiration does
not help, which a human ear then overturned, and it is why the two spellings the
page now shows cannot be compared from inside this repo.

A neural voice plus a real recogniser closes that. Run this where the network
allows api.elevenlabs.io:

    export ELEVEN_API_KEY=...            # never commit it
    python3 eleven_test.py               # uses testset.txt
    python3 eleven_test.py "some line"   # or your own

For each line it speaks three things, reverses the audio, and scores it two
ways: by transcript, and by acoustic distance to the sound the reader is
actually trying to make.

    forward   the line said normally  -> the control, should NOT match
    words     the readable spelling
    sounds    the ear-based spelling

WHAT A FIRST RUN OF THIS ALREADY SHOWED, on one line and one voice:

  - Scribe transcribes forward nonsense perfectly. Asked to read
    "puh vig ruh venn" it came back "puh vig ruh venn", so it is a fair judge
    of whether a voice said what the script asked for.
  - Reversing that same audio transcribed as nothing at all.
  - Reversing the line itself transcribed as "A figure of eight" at 0.95
    confidence, which looks like a result and is not one: speaking
    "A figure of eight" and reversing THAT transcribes as nothing. The
    recogniser is snapping reversed noise onto plausible English rather than
    reporting what is there, so a transcript of reversed audio cannot be
    trusted and cannot be used to generate scripts.
  - By acoustic distance, which does not involve a language model, the spread
    was small: the script scored 0.69 against the sound it is meant to
    reproduce and simply saying the line forwards scored 0.75. A script that
    worked should be far below its own control.

So the transcript half of this is a diagnostic, not the verdict, and `dtw` is
the number to watch. One line is not a result — run it over the whole set.
"""
import os, sys, json, io, wave, array, subprocess, tempfile, urllib.request, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
KEY = os.environ.get("ELEVEN_API_KEY")
API = "https://api.elevenlabs.io/v1"
TTS_MODEL = "eleven_multilingual_v2"
STT_MODEL = "scribe_v1"

def call(path, data=None, headers=None, method=None, raw=False):
    req = urllib.request.Request(API + path, data=data, method=method)
    req.add_header("xi-api-key", KEY)
    for k, v in (headers or {}).items(): req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.read() if raw else json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit(f"{path} -> {e.code} {e.read()[:400].decode(errors='replace')}")

def pick_voice():
    if os.environ.get("ELEVEN_VOICE"): return os.environ["ELEVEN_VOICE"]
    vs = call("/voices")["voices"]
    return vs[0]["voice_id"]

def say(text, voice, path):
    body = json.dumps({"text": text, "model_id": TTS_MODEL}).encode()
    mp3 = call(f"/text-to-speech/{voice}", body, {"Content-Type": "application/json"}, raw=True)
    p = path + ".mp3"
    open(p, "wb").write(mp3)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", p,
                    "-ar", "16000", "-ac", "1", path], check=True)

def reverse(src, dst):
    with wave.open(src, "rb") as w:
        p = w.getparams(); frames = w.readframes(w.getnframes())
    a = array.array("h"); a.frombytes(frames); a.reverse()
    with wave.open(dst, "wb") as w:
        w.setparams(p); w.writeframes(a.tobytes())

def hear(path):
    """multipart upload, hand-rolled so this needs nothing but the stdlib"""
    b = b"----backwords"
    body = io.BytesIO()
    def field(name, value):
        body.write(b"--" + b + b"\r\n")
        body.write(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode())
        body.write(value.encode() + b"\r\n")
    field("model_id", STT_MODEL)
    body.write(b"--" + b + b"\r\n")
    body.write(b'Content-Disposition: form-data; name="file"; filename="a.wav"\r\n')
    body.write(b"Content-Type: audio/wav\r\n\r\n")
    body.write(open(path, "rb").read() + b"\r\n")
    body.write(b"--" + b + b"--\r\n")
    r = call("/speech-to-text", body.getvalue(),
             {"Content-Type": "multipart/form-data; boundary=" + b.decode()})
    return (r.get("text") or "").strip()

def dist(a, b):
    """acoustic distance, no language model involved"""
    import numpy as np, librosa
    def feats(p):
        y, sr = librosa.load(p, sr=16000)
        y, _ = librosa.effects.trim(y, top_db=32)
        m = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13, hop_length=160)
        X = np.vstack([m, librosa.feature.delta(m)])
        return ((X - X.mean(1, keepdims=True)) / (X.std(1, keepdims=True) + 1e-8)).T
    D, wp = librosa.sequence.dtw(X=feats(a).T, Y=feats(b).T, metric="cosine")
    return D[-1, -1] / len(wp)

def wer(ref, hyp):
    a, b = ref.lower().split(), "".join(c for c in hyp.lower() if c.isalnum() or c.isspace()).split()
    if not a: return 1.0
    prev = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        cur = [i]
        for j, y in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (x != y)))
        prev = cur
    return prev[-1] / len(a)

def main():
    if not KEY: sys.exit("set ELEVEN_API_KEY first")
    for tool in ("ffmpeg",):
        if not subprocess.run(["which", tool], capture_output=True).returncode == 0:
            sys.exit(f"needs {tool}")
    from render_style import script_for, load_style
    style = load_style()

    lines = sys.argv[1:] or [l.strip() for l in open(os.path.join(HERE, "testset.txt")) if l.strip()][:8]
    voice = pick_voice()
    print(f"voice {voice}, {len(lines)} lines\n")
    tot = {"forward": 0.0, "words": 0.0, "sounds": 0.0}
    dtot = {"forward": 0.0, "words": 0.0, "sounds": 0.0}

    from subprocess import run as _run
    def words_script(line):
        js = ('const S=require("%s/script.js");const fs=require("fs");'
              'S.load(fs.readFileSync("%s/data/lex.txt","utf8"),fs.readFileSync("%s/data/idx.txt","utf8"),'
              'fs.readFileSync("%s/data/style.json","utf8"));'
              'process.stdout.write(S.make(process.argv[1]).parts.map(p=>p.spell).join(" "));'
              ) % ((os.path.dirname(HERE),) * 4)
        return _run(["node", "-e", js, line], capture_output=True, text=True).stdout

    with tempfile.TemporaryDirectory() as td:
        for line in lines:
            cand = {"forward": line, "words": words_script(line), "sounds": script_for(line, style)}
            print(f"  {line}")
            # the sound a correct script must reproduce: the line, backwards
            tgt = os.path.join(td, "t.wav"); tgt_rev = os.path.join(td, "trev.wav")
            say(line, voice, tgt); reverse(tgt, tgt_rev)
            for kind, text in cand.items():
                f = os.path.join(td, "a.wav"); r = os.path.join(td, "b.wav")
                say(text, voice, f); reverse(f, r)
                heard = hear(r)
                e = wer(line, heard); tot[kind] += e
                dd = dist(tgt_rev, f); dtot[kind] += dd   # speaking it vs the target sound
                print(f"    {kind:8s} said {text[:52]:<52s}")
                print(f"    {'':8s} dtw {dd:.3f}   heard {heard[:44]!r}  WER {e:.2f}")
            print()

    n = len(lines)
    print(f"{'':8s} {'dtw':>7}  {'WER':>7}")
    for k in ("forward", "words", "sounds"):
        print(f"  {k:8s} {dtot[k]/n:7.3f}  {tot[k]/n:7.3f}")
    print("\ndtw is the one to trust: it compares what the reader would actually")
    print("produce against the sound they are trying to make, with no language")
    print("model in the way. forward is the control. A speller that works puts")
    print("words or sounds clearly below it; a small spread means it does not.")
    print("WER is a diagnostic only — reversed speech is out of distribution for")
    print("the recogniser, which invents plausible English rather than reporting")
    print("what is there.")

if __name__ == "__main__":
    main()
