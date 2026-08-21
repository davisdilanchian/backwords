// Collecting your spellings for the reversed sounds.
//
// The shipped index was verified with espeak-ng, which reads invented syllables
// perfectly and so cannot tell "moss is a dour tissue" from "slesh eess sless
// eesh". You can. This walks the sound pieces the app leans on most, plays each
// one back to you in your own voice reversed, and records how you would spell
// what you hear. Your answer is authoritative: you are the one who reads it.

const $ = (id) => document.getElementById(id);
const KEY = "backwords-calibration-v1";

let units = [];
let i = 0;
let answers = {};
let take = null;      // the reversed audio of the current prompt
let rec = null;
let rate = 1;

function load() {
  try { answers = JSON.parse(localStorage.getItem(KEY) || "{}"); } catch (e) { answers = {}; }
}
function persist() {
  try { localStorage.setItem(KEY, JSON.stringify(answers)); } catch (e) {}
}

function firstUnanswered(from = 0) {
  for (let k = from; k < units.length; k++) if (!answers[units[k].key]) return k;
  return units.length;
}

function draw(buf) {
  const c = $("wave");
  const dpr = window.devicePixelRatio || 1, w = c.clientWidth, h = c.clientHeight;
  c.width = w * dpr; c.height = h * dpr;
  const g = c.getContext("2d"); g.scale(dpr, dpr); g.clearRect(0, 0, w, h);
  if (!buf) return;
  const d = buf.getChannelData(0), step = Math.max(1, Math.floor(d.length / w));
  g.fillStyle = getComputedStyle(document.body).getPropertyValue("--ink");
  for (let x = 0; x < w; x++) {
    let peak = 0;
    for (let k = x * step, e = Math.min(d.length, k + step); k < e; k++) peak = Math.max(peak, Math.abs(d[k]));
    const bar = Math.max(1, peak * h * 0.92);
    g.fillRect(x, (h - bar) / 2, 1, bar);
  }
}

function render() {
  const done = Object.keys(answers).length;
  if (i >= units.length) {
    $("card").hidden = true;
    $("donewrap").hidden = false; $("doneinner").hidden = false;
    $("status").textContent = `${done} spellings collected. Nothing leaves this browser until you download.`;
    return;
  }
  const u = units[i];
  $("card").hidden = false;
  $("say").textContent = u.say;
  $("progress").textContent =
    `${done} answered · piece ${i + 1} of ${units.length} · these cover about ${Math.round(u.cum * 100)}% of everything you'll type`;
  $("bar").style.width = `${Math.max(2, 100 * done / units.length)}%`;
  $("answer").hidden = true;
  $("spell").value = "";
  take = null; draw(null);
  $("rec").textContent = "Record";
  $("donewrap").hidden = done === 0; $("doneinner").hidden = done === 0;
  $("status").textContent = `${done} saved in this browser.`;
}

async function record() {
  if (rec) { rec.stop(); return; }
  $("rec").disabled = true; $("rec").textContent = "Getting ready…";
  let r;
  try {
    r = BW.record();
    await r.ready;
  } catch (e) {
    $("micwarn").hidden = false;
    $("micwarn").textContent = "No microphone available (" + (e && e.name ? e.name : "blocked") + ").";
    $("rec").disabled = false; $("rec").textContent = "Record"; return;
  }
  rec = r;
  $("rec").disabled = false; $("rec").classList.add("rec"); $("rec").textContent = "Stop";
  let buf;
  try { buf = BW.trim(await r.done); }
  catch (e) { rec = null; $("rec").classList.remove("rec"); $("rec").textContent = "Record"; return; }
  rec = null;
  $("rec").classList.remove("rec"); $("rec").textContent = "Re-record";
  take = BW.reverse(buf);
  draw(take);
  $("answer").hidden = false;
  await BW.play(take, rate);
  $("spell").focus();
}

function save() {
  const v = $("spell").value.trim().toLowerCase();
  if (!v) return;
  answers[units[i].key] = { say: units[i].say, spell: v, at: new Date().toISOString() };
  persist();
  i = firstUnanswered(i + 1);
  render();
}

$("rec").addEventListener("click", record);
$("redo").addEventListener("click", record);
$("save").addEventListener("click", save);
$("again").addEventListener("click", () => take && BW.play(take, rate));
$("slow").addEventListener("click", () => {
  rate = rate === 1 ? 0.5 : 1;
  $("slow").textContent = rate === 1 ? "0.5×" : "1×";
  if (take) BW.play(take, rate);
});
$("skip").addEventListener("click", () => { i = firstUnanswered(i + 1); render(); });

$("spell").addEventListener("keydown", (e) => {
  if (e.key === "Enter") { e.preventDefault(); save(); }
});
document.addEventListener("keydown", (e) => {
  if (e.code === "Space" && e.target.tagName !== "INPUT") { e.preventDefault(); record(); }
});

$("export").addEventListener("click", () => {
  const out = { version: 1, saved: new Date().toISOString(), answers };
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([JSON.stringify(out, null, 1)], { type: "application/json" }));
  a.download = "backwords-spellings.json";
  a.click();
});
$("reset").addEventListener("click", () => {
  if (!confirm("Delete every spelling you have recorded so far?")) return;
  answers = {}; persist(); i = 0; render();
});

document.body.addEventListener("click", () => BW.warm(), { once: true });

fetch("data/units.json").then((r) => r.json()).then((u) => {
  units = u;
  load();
  i = firstUnanswered(0);
  render();
}).catch(() => { $("status").textContent = "Couldn’t load the sound pieces."; });
