import subprocess, wave, array, os, tempfile, functools

SR = 16000
def tts(text, wav, voice="en-us", speed=150, pitch=50, gap=0):
    subprocess.run(["espeak-ng","-v",voice,"-s",str(speed),"-p",str(pitch),
                    "-g",str(gap),"-w",wav,"--", text],
                   check=True, capture_output=True)
    # force 16k mono 16-bit for the decoder
    out = wav + ".16k.wav"
    subprocess.run(["ffmpeg","-y","-loglevel","error","-i",wav,
                    "-ar",str(SR),"-ac","1","-sample_fmt","s16",out], check=True)
    os.replace(out, wav)

def reverse_wav(src, dst):
    with wave.open(src,'rb') as w:
        p = w.getparams(); frames = w.readframes(w.getnframes())
    a = array.array('h'); a.frombytes(frames); a.reverse()
    with wave.open(dst,'wb') as w:
        w.setparams(p); w.writeframes(a.tobytes())

_dec = None
def _decoder():
    global _dec
    if _dec is None:
        from pocketsphinx import Decoder, get_model_path
        mp = get_model_path()
        c = Decoder.default_config()
        c.set_string('-hmm', os.path.join(mp,'en-us','en-us'))
        c.set_string('-lm',  os.path.join(mp,'en-us','en-us.lm.bin'))
        c.set_string('-dict',os.path.join(mp,'en-us','cmudict-en-us.dict'))
        c.set_string('-logfn', os.devnull)
        _dec = Decoder(c)
    return _dec

def asr(wav):
    d = _decoder()
    with wave.open(wav,'rb') as w:
        data = w.readframes(w.getnframes())
    d.start_utt(); d.process_raw(data, False, True); d.end_utt()
    h = d.hyp()
    return (h.hypstr if h else "").strip()

def speak_reverse_hear(text, voice="en-us", speed=150, gap=0):
    with tempfile.TemporaryDirectory() as td:
        f = os.path.join(td,"a.wav"); r = os.path.join(td,"b.wav")
        tts(text, f, voice=voice, speed=speed, gap=gap)
        reverse_wav(f, r)
        return asr(r)

def speak_hear(text, voice="en-us", speed=150):
    with tempfile.TemporaryDirectory() as td:
        f = os.path.join(td,"a.wav")
        tts(text, f, voice=voice, speed=speed)
        return asr(f)

# ---- phone-level (allphone) decoding -------------------------------------
_ap = None
def _allphone():
    global _ap
    if _ap is None:
        from pocketsphinx import Decoder, get_model_path
        mp = get_model_path()
        c = Decoder.default_config()
        c.set_string('-lm', None)
        c.set_string('-dict', None)
        c.set_string('-hmm', os.path.join(mp,'en-us','en-us'))
        c.set_string('-allphone', os.path.join(mp,'en-us','en-us-phone.lm.bin'))
        c.set_boolean('-allphone_ci', True)
        c.set_float('-lw', 2.0); c.set_float('-pip', 0.3); c.set_float('-beam', 1e-10)
        c.set_float('-pbeam', 1e-10); c.set_float('-lpbeam', 1e-10)
        c.set_string('-logfn', os.devnull)
        _ap = Decoder(c)
    return _ap

def phone_decode(wav):
    d = _allphone()
    with wave.open(wav,'rb') as w:
        data = w.readframes(w.getnframes())
    d.start_utt(); d.process_raw(data, False, True); d.end_utt()
    return [s.word for s in d.seg() if s.word not in ("SIL","+NSN+","<sil>","(NULL)")]

def hear_phones(text, reverse=False, voice="en-us", speed=150, gap=0):
    with tempfile.TemporaryDirectory() as td:
        f = os.path.join(td,"a.wav"); r = os.path.join(td,"b.wav")
        tts(text, f, voice=voice, speed=speed, gap=gap)
        if reverse:
            reverse_wav(f, r); f = r
        return phone_decode(f)
