// Backwords — the loop.
//
// Say the line forwards. We flip it. What you hear is what you have to say:
// a real target, in your own voice, instead of a spelling you have to decode.
// Say that back, we flip your take, and you hear whether it landed.
//
// The written script is a crutch for the same target. Use whichever helps.

const $ = (id) => document.getElementById(id);
const show = (id, on = true) => { const e = $(id); if (e) e.hidden = !on; };

const S = {
  text: "",
  forward: null,     // the line, said normally
  target: null,      // that recording, flipped — the thing to imitate
  attempt: null,     // the user saying the flipped thing
  result: null,      // their attempt, flipped back
  rate: 1,
  recording: null,
};

// ---- waveform ------------------------------------------------------------

function draw(canvas, buf, tint) {
  if (!canvas || !buf) return;
  const dpr = window.devicePixelRatio || 1;
  const w = canvas.clientWidth, h = canvas.clientHeight;
  canvas.width = w * dpr; canvas.height = h * dpr;
  const g = canvas.getContext("2d");
  g.scale(dpr, dpr);
  g.clearRect(0, 0, w, h);
  const d = buf.getChannelData(0), step = Math.max(1, Math.floor(d.length / w));
  g.fillStyle = tint || getComputedStyle(document.body).getPropertyValue("--ink");
  for (let x = 0; x < w; x++) {
    let peak = 0;
    for (let i = x * step, e = Math.min(d.length, i + step); i < e; i++) {
      peak = Math.max(peak, Math.abs(d[i]));
    }
    const bar = Math.max(1, peak * h * 0.92);
    g.fillRect(x, (h - bar) / 2, 1, bar);
  }
}

// ---- steps ---------------------------------------------------------------

// `now` is where the attention is; `avail` is how far the user may go.
function setStep(now, avail = now) {
  for (const k of [1, 2, 3]) {
    const el = $(`step${k}`);
    el.classList.toggle("on", k <= avail);
    el.classList.toggle("now", k === now);
  }
}

function renderScript() {
  if (!SCRIPTER.pieces || !S.text) return;
  const { parts, unknown, accuracy } = SCRIPTER.make(S.text);
  const el = $("script");
  el.textContent = "";
  parts.forEach((p, i) => {
    const s = document.createElement("span");
    s.className = "bit" + (p.off ? " approx" : "");
    s.textContent = p.spell;
    el.appendChild(s);
    if (i < parts.length - 1) el.appendChild(document.createTextNode(" "));
  });
  $("meter").textContent = `${Math.round(accuracy * 100)}% of the sounds are spelled exactly`
    + (unknown.length ? ` · sounded out by rule: ${unknown.join(", ")}` : "");
}

async function recordInto(which, btn) {
  if (S.recording) { S.recording.stop(); return; }
  if (which === "attempt" && !S.forward) return;
  btn.disabled = true;
  btn.textContent = "Getting ready…";
  let rec;
  try {
    rec = BW.record();
    await rec.ready;                    // only claim to be recording once we are
  } catch (e) { micFail(e); btn.disabled = false; btn.textContent = btn.dataset.label; return; }
  S.recording = rec;
  btn.disabled = false;
  btn.classList.add("rec");
  btn.textContent = "Stop";
  let buf;
  try {
    buf = BW.trim(await rec.done);
  } catch (e) {
    micFail(e); S.recording = null; btn.classList.remove("rec");
    btn.disabled = false; btn.textContent = btn.dataset.label; return;
  }
  S.recording = null;
  btn.classList.remove("rec");
  btn.textContent = btn.dataset.label;

  if (which === "forward") {
    S.forward = buf;
    S.target = BW.reverse(buf);
    draw($("wave1"), S.forward);
    draw($("wave2"), S.target);
    show("targetwrap");
    setStep(2, 3);
    gate();
    BW.play(S.target, S.rate);
  } else {
    S.attempt = buf;
    S.result = BW.reverse(buf);
    draw($("wave3"), S.result);
    show("resultwrap");
    const sim = BW.similarity(S.result, S.forward);
    const pct = Math.round(sim * 100);
    $("bar").style.width = `${Math.max(3, pct)}%`;
    $("verdict").textContent =
      sim >= 0.6 ? `That lands. ${pct}% match to your original.`
      : sim >= 0.38 ? `Close — recognisable but soft. ${pct}% match.`
      : sim >= 0.2 ? `Some of it is there. ${pct}% match. Try slower and flatter.`
      : `Not there yet. ${pct}% match. Play the target again and copy it sound for sound.`;
    BW.play(S.result, 1);
  }
}

// nothing downstream of a recording is meaningful until that recording exists
function gate() {
  $("rec2").disabled = !S.forward;
  $("playForward").disabled = !S.forward;
  $("playTarget").disabled = !S.target;
}

function micFail(e) {
  show("micwarn");
  $("micwarn").textContent =
    "No microphone available (" + (e && e.name ? e.name : "blocked") +
    "). The written script below still works — record and reverse in any audio app.";
}

// ---- wiring --------------------------------------------------------------

function start() {
  const t = $("input").value.trim();
  if (!t) return;
  if (t === S.text && S.forward) return;      // same line, keep the take
  S.text = t;
  S.forward = S.target = S.attempt = S.result = null;
  show("targetwrap", false);
  show("resultwrap", false);
  show("work");
  renderScript();
  setStep(1);
  $("say").textContent = t;
  gate();
  BW.warm();                            // this click is our chance to open the audio graph
  $("work").scrollIntoView({ behavior: "smooth", block: "start" });
}

$("go").addEventListener("click", start);
$("input").addEventListener("keydown", (e) => {
  if ((e.metaKey || e.ctrlKey) && e.key === "Enter") start();
});

for (const [id, which] of [["rec1", "forward"], ["rec2", "attempt"]]) {
  const b = $(id);
  b.dataset.label = b.textContent;
  b.addEventListener("click", () => recordInto(which, b));
}

$("playTarget").addEventListener("click", () => S.target && BW.play(S.target, S.rate));
$("playResult").addEventListener("click", () => S.result && BW.play(S.result, 1));
$("playForward").addEventListener("click", () => S.forward && BW.play(S.forward, 1));

for (const b of document.querySelectorAll("[data-rate]")) {
  b.addEventListener("click", () => {
    S.rate = parseFloat(b.dataset.rate);
    for (const o of document.querySelectorAll("[data-rate]")) o.classList.toggle("sel", o === b);
    if (S.target) BW.play(S.target, S.rate);
  });
}

$("again").addEventListener("click", () => {
  show("resultwrap", false);
  setStep(2, 3);
  if (S.target) BW.play(S.target, S.rate);
});

$("save").addEventListener("click", () => {
  if (!S.result) return;
  const a = document.createElement("a");
  a.href = URL.createObjectURL(BW.toWav(S.result));
  a.download = "backwords.wav";
  a.click();
});

$("copy").addEventListener("click", async () => {
  const t = [...$("script").querySelectorAll(".bit")].map((s) => s.textContent).join(" ");
  await navigator.clipboard.writeText(t);
  $("copy").textContent = "Copied";
  setTimeout(() => ($("copy").textContent = "Copy script"), 1200);
});

Promise.all([
  fetch("data/lex.txt").then((r) => r.text()),
  fetch("data/idx.txt").then((r) => r.text()),
]).then(([lex, idx]) => {
  SCRIPTER.load(lex, idx);
  $("status").textContent =
    `${SCRIPTER.words.toLocaleString()} words, ${SCRIPTER.pieces.toLocaleString()} checked sound pieces. Everything runs in your browser; nothing is uploaded.`;
  if (S.text) renderScript();
}).catch(() => {
  $("status").textContent = "Couldn’t load the spelling data — the audio loop still works.";
});

window.addEventListener("resize", () => {
  draw($("wave1"), S.forward); draw($("wave2"), S.target); draw($("wave3"), S.result);
});
