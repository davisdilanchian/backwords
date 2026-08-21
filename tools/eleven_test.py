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

For each line it speaks three things, reverses the audio, transcribes it, and
scores the transcript against the line that was meant:

    forward   the line said normally, reversed and transcribed  -> the floor,
              since a reversed recording of the line should NOT be intelligible
    words     the readable spelling, reversed  -> should say the line
    sounds    the ear-based spelling, reversed -> should say the line

Whichever of words/sounds transcribes closer to the original wins, and that is
the answer nobody in this repo can currently give.
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
            for kind, text in cand.items():
                f = os.path.join(td, "a.wav"); r = os.path.join(td, "b.wav")
                say(text, voice, f); reverse(f, r)
                heard = hear(r)
                e = wer(line, heard)
                tot[kind] += e
                print(f"    {kind:8s} said {text[:52]:<52s}")
                print(f"    {'':8s} heard {heard[:60]!r}  WER {e:.2f}")
            print()

    n = len(lines)
    print("mean word error against the intended line (lower is better):")
    for k in ("forward", "words", "sounds"):
        print(f"  {k:8s} {tot[k]/n:.3f}")
    print("\nforward is the control — a reversed recording of the line itself should")
    print("score badly. If words or sounds beats it clearly, the speller works, and")
    print("whichever of the two is lower is the one to keep.")

if __name__ == "__main__":
    main()
