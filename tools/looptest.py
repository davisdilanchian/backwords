"""End-to-end test of the record → reverse → imitate → reverse loop.

Drives the real page in Chromium with a synthetic microphone, so the whole
chain runs: capture, trim, reverse, MFCC, DTW, verdict. Four scenarios go in
and the scores have to come out in the right order, which is the only way to
know the feedback the app gives a user is not noise.

    python3 looptest.py

Needs: playwright (pip), a chromium build, espeak-ng, ffmpeg.
"""
import os, sys, shutil, subprocess, threading, http.server, socketserver, functools
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from obj import wav_of
import assemble_ref as A
from evaluate import target_for

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FEED = os.path.join(ROOT, "_t")
PORT = 8815
LINE = "hello my name is dan"
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")

def make_audio():
    os.makedirs(FEED, exist_ok=True)
    script = " ".join(p for p in A.assemble(target_for(LINE)))
    shutil.copy(wav_of(LINE),                f"{FEED}/forward.wav")  # step 1
    shutil.copy(wav_of(LINE, reverse=True),  f"{FEED}/ideal.wav")    # a faithful imitation
    shutil.copy(wav_of(script),              f"{FEED}/read.wav")     # reading the spelling
    shutil.copy(wav_of("the quick brown fox"), f"{FEED}/wrong.wav")  # unrelated

class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass

def serve():
    h = functools.partial(Quiet, directory=ROOT)
    socketserver.TCPServer.allow_reuse_address = True
    srv = socketserver.TCPServer(("", PORT), h)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv

def main():
    from playwright.sync_api import sync_playwright
    make_audio()
    srv = serve()
    stub = open(os.path.join(HERE, "stub.js")).read()
    fails = []
    try:
        with sync_playwright() as p:
            b = p.chromium.launch(executable_path=CHROME, args=[
                "--use-fake-ui-for-media-stream", "--autoplay-policy=no-user-gesture-required"])
            pg = b.new_page(); errs = []
            pg.on("pageerror", lambda e: errs.append(str(e)))
            pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
            pg.add_init_script(stub)
            pg.goto(f"http://localhost:{PORT}/", wait_until="networkidle")
            pg.wait_for_function(
                "document.getElementById('status').textContent.includes('words')", timeout=60000)

            def rec(feed, btn):
                pg.evaluate(f"window.__feed = {feed!r}")
                pg.click(btn); pg.wait_for_timeout(400)
                pg.wait_for_timeout(int(pg.evaluate("window.__feedMs || 2000")) + 350)
                pg.click(btn); pg.wait_for_timeout(1600)

            pg.fill("#input", LINE); pg.click("#go"); pg.wait_for_timeout(300)
            if not pg.evaluate("document.getElementById('rec2').disabled"):
                fails.append("step 3 was live before step 1 had been recorded")
            rec("/_t/forward.wav", "#rec1")
            if pg.locator("#targetwrap").is_hidden():
                fails.append("no target produced from the first take")

            got = {}
            for name, f in [("ideal", "/_t/ideal.wav"), ("read", "/_t/read.wav"),
                            ("wrong", "/_t/wrong.wav")]:
                rec(f, "#rec2")
                got[name] = pg.evaluate("BW.similarity(S.result, S.forward)")
                print(f"  {name:6s} {got[name]*100:5.1f}%   {pg.inner_text('#verdict')}")
                pg.click("#again"); pg.wait_for_timeout(250)

            if errs: fails.append(f"console errors: {errs}")
            if got["ideal"] < 0.75: fails.append(f"a faithful imitation only scored {got['ideal']:.2f}")
            if got["wrong"] > 0.25: fails.append(f"an unrelated line scored {got['wrong']:.2f}")
            if not (got["ideal"] > got["read"] > got["wrong"]):
                fails.append(f"scores out of order: {got}")
            b.close()
    finally:
        srv.shutdown(); shutil.rmtree(FEED, ignore_errors=True)

    print()
    for f in fails: print("  FAIL:", f)
    print("  all checks passed" if not fails else f"  {len(fails)} failure(s)")
    return 1 if fails else 0

if __name__ == "__main__":
    sys.exit(main())
