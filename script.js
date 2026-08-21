// The written crutch: a spelling of the line, backwards.
//
// This is the weaker of the two channels the app gives you — see audio.js for
// the stronger one. Reversing a recording reverses the signal, not the phoneme
// list, so the target is built in "atomised" phones: diphthongs split into the
// two vowel targets they glide between, affricates into stop + fricative.
// Reverse that, then spell it with pieces whose pronunciation was checked
// offline against a real grapheme-to-phoneme engine (see tools/). Nothing is
// guessed at spelling time: every piece in idx.txt was read back and matched
// before it shipped.
//
// Measured limit: the spelling round-trips at 0.067 phone error, but a reversed
// recording of someone reading it only lands about halfway between chance and
// a perfect match. Reading invented spellings is lossy in a way no better
// spelling fixes. That is why the audio loop exists.

const ALPHA = ["AA","AE","AH","AO","EH","IH","IY","UH","UW",
               "B","D","DH","F","G","HH","K","L","M","N","NG",
               "P","R","S","SH","T","TH","V","W","Y","Z","ZH"];
const CODE = "abcdefghijklmnopqrstuvwxyzABCDE";
const P2C = {};
ALPHA.forEach((p, i) => { P2C[p] = CODE[i]; });

// A phone that is still moving when you cut it in half has to be written as the
// parts it moves through, or the reversal lands on the wrong sound.
const ATOM = {
  AY: "AA IY", EY: "EH IY", OY: "AO IY", AW: "AA UW", OW: "AO UW",
  CH: "T SH",  JH: "D ZH",  ER: "AH R",
};

// Swaps that survive being played backwards: voicing pairs, close vowels,
// and the glide/vowel pairs that are the same gesture either way.
const NEAR_GROUPS = [
  "AA AH","AA AE","AA AO","AE EH","AH AE","IH IY","UH UW","AH ER","AH IH",
  "W UW","Y IY","T D","P B","K G","S Z","F V","TH DH","SH ZH","M N","N NG","L R",
];
const NEAR = {};
for (const p of ALPHA) {
  NEAR[p] = ALPHA.filter(q => q !== p && NEAR_GROUPS.some(g => {
    const s = g.split(" ");
    return s.includes(p) && s.includes(q);
  }));
}
// vowels and glides that show up when a cluster needs breaking
const EPEN = ["AH","IH","UH","IY","UW","EH","AA","R","W","Y","HH"];
const NEAR_C = {}, EPEN_C = EPEN.map(p => P2C[p]);
for (const p of ALPHA) NEAR_C[P2C[p]] = NEAR[p].map(q => P2C[q]);

const CFG = {
  errSubNear: 1.0,   // wrote a close phone instead of the right one
  errIns: 1.6,       // script says a phone the line does not have
  errDel: 2.2,       // phone in the line the script never says
  wErr: 2.5,         // a phone error is worth this much detour
  chunk: 0.25,       // mild pull toward fewer, longer pieces
  maxLen: 7,
};

let LEX = new Map();   // word -> atomised phone codes
let IDX = new Map();   // phone codes -> [[spelling, cost], ...]

function parseLex(text) {
  const m = new Map();
  for (const line of text.split("\n")) {
    const t = line.indexOf("\t");
    if (t > 0) m.set(line.slice(0, t), line.slice(t + 1));
  }
  return m;
}

function parseIdx(text) {
  const m = new Map();
  for (const line of text.split("\n")) {
    const t = line.indexOf("\t");
    if (t < 0) continue;
    const ents = line.slice(t + 1).split("|").map((s) => {
      const cost = parseInt(s[0], 36) / 20;
      const word = s[1] !== "!";               // "!" marks an invented syllable
      return [word ? s.slice(1) : s.slice(2), cost, word];
    });
    m.set(line.slice(0, t), ents);
  }
  return m;
}

// ---- input side ----------------------------------------------------------

function atomise(phones) {
  const out = [];
  for (const p of phones) {
    const a = ATOM[p];
    if (a) out.push(...a.split(" ")); else out.push(p);
  }
  return out;
}

// Letter-to-sound for anything the lexicon has never seen. Longest rule wins.
const LTS = [
  ["ough", "AO"], ["tion", "SH AH N"], ["sion", "ZH AH N"], ["ight", "AA IY T"],
  ["augh", "AO"], ["tch", "T SH"], ["dge", "D ZH"], ["igh", "AA IY"],
  ["air", "EH R"], ["ear", "IY R"], ["eer", "IY R"], ["oor", "UW R"],
  ["our", "AA UW R"], ["ure", "Y UW R"], ["ck", "K"], ["ch", "T SH"],
  ["sh", "SH"], ["th", "TH"], ["ph", "F"], ["gh", "G"], ["wh", "W"],
  ["kn", "N"], ["wr", "R"], ["qu", "K W"], ["ng", "NG"], ["ee", "IY"],
  ["ea", "IY"], ["ie", "IY"], ["ei", "IY"], ["oo", "UW"], ["ou", "AA UW"],
  ["ow", "AA UW"], ["oa", "AO UW"], ["oe", "AO UW"], ["oi", "AO IY"],
  ["oy", "AO IY"], ["ai", "EH IY"], ["ay", "EH IY"], ["au", "AO"],
  ["aw", "AO"], ["ew", "Y UW"], ["ar", "AA R"], ["or", "AO R"],
  ["er", "AH R"], ["ir", "AH R"], ["ur", "AH R"],
];
const SINGLE = { b:"B", d:"D", f:"F", g:"G", h:"HH", j:"D ZH", k:"K", l:"L",
  m:"M", n:"N", p:"P", r:"R", s:"S", t:"T", v:"V", w:"W", z:"Z" };

function guess(word) {
  let w = word.toLowerCase().replace(/[^a-z]/g, "");
  if (!w) return [];
  const silentE = w.length > 2 && w.endsWith("e") && /[aeiou]/.test(w.slice(1, -1));
  if (silentE) w = w.slice(0, -1);
  const out = [];
  let i = 0;
  while (i < w.length) {
    let hit = null;
    for (const [g, ph] of LTS) if (w.startsWith(g, i)) { hit = [g.length, ph]; break; }
    if (hit) { out.push(...hit[1].split(" ")); i += hit[0]; continue; }
    const c = w[i], nx = w[i + 1] || "";
    const soft = "eiy".includes(nx);
    const last = i === w.length - 1;
    if (c === "c") out.push(soft ? "S" : "K");
    else if (c === "g") out.push(...(soft ? ["D", "ZH"] : ["G"]));
    else if (c === "x") out.push("K", "S");
    else if (c === "q") out.push("K");
    else if (c === "y") out.push(i === 0 ? "Y" : "IY");
    else if (c === "a") out.push(...(silentE && last ? ["EH", "IY"] : ["AE"]));
    else if (c === "e") out.push("EH");
    else if (c === "i") out.push(...(silentE && last ? ["AA", "IY"] : ["IH"]));
    else if (c === "o") out.push(...(silentE && last ? ["AO", "UW"] : ["AA"]));
    else if (c === "u") out.push(...(silentE && last ? ["Y", "UW"] : ["AH"]));
    else if (SINGLE[c]) out.push(...SINGLE[c].split(" "));
    i++;
  }
  return out;
}

function phonesFor(word) {
  const w = word.toLowerCase();
  const hit = LEX.get(w) || LEX.get(w.replace(/'/g, ""));
  if (hit) return hit;
  return atomise(guess(w)).map(p => P2C[p]).join("");
}

// ---- the search ----------------------------------------------------------

// Every index key within one edit of what we still owe the listener.
function variants(want) {
  const out = [[want, 0]];
  for (let k = 0; k < want.length; k++) {
    for (const alt of NEAR_C[want[k]]) {
      out.push([want.slice(0, k) + alt + want.slice(k + 1), CFG.errSubNear]);
    }
    if (want.length > 1) out.push([want.slice(0, k) + want.slice(k + 1), CFG.errDel]);
  }
  for (let k = 0; k <= want.length; k++) {
    for (const e of EPEN_C) out.push([want.slice(0, k) + e + want.slice(k), CFG.errIns]);
  }
  return out;
}

function assemble(target) {
  const n = target.length, INF = Infinity;
  const best = new Array(n + 1).fill(INF), back = new Array(n + 1).fill(null);
  best[0] = 0;
  for (let i = 0; i < n; i++) {
    if (best[i] === INF) continue;
    let any = false;
    const hi = Math.min(i + CFG.maxLen, n);
    for (let j = i + 1; j <= hi; j++) {
      const want = target.slice(i, j);
      for (const [key, ecost] of variants(want)) {
        const ents = IDX.get(key);
        if (!ents) continue;
        any = true;
        for (const [spell, c] of ents) {
          const v = best[i] + c + CFG.wErr * ecost + CFG.chunk;
          if (v < best[j]) { best[j] = v; back[j] = [i, spell, ecost]; }
        }
      }
    }
    if (!any && best[i] + 10 < best[i + 1]) {
      best[i + 1] = best[i] + 10;
      back[i + 1] = [i, "uh", CFG.errDel];
    }
  }
  const parts = [];
  let j = n;
  while (j > 0) {
    const [i, spell, ecost] = back[j];
    parts.push({ spell, off: ecost > 0 });
    j = i;
  }
  parts.reverse();
  return parts;
}

function reverseScript(text) {
  const words = (text.match(/[A-Za-z']+/g) || []);
  let target = "";
  const unknown = [];
  for (const w of words) {
    if (!LEX.has(w.toLowerCase()) && !LEX.has(w.toLowerCase().replace(/'/g, ""))) {
      unknown.push(w.toLowerCase());
    }
    target += phonesFor(w);
  }
  target = [...target].reverse().join("");
  if (!target) return { parts: [], unknown, accuracy: 1 };
  const parts = assemble(target);
  const off = parts.filter(p => p.off).length;
  return { parts, unknown, accuracy: Math.max(0, 1 - off / target.length) };
}


const SCRIPTER = {
  load(lexText, idxText) { LEX = parseLex(lexText); IDX = parseIdx(idxText); },
  make: (text) => reverseScript(text),
  get words() { return LEX.size; },
  get pieces() { return IDX.size; },
};

if (typeof module !== "undefined") module.exports = SCRIPTER;
