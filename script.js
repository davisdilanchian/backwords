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
const P2C = {}, C2P = {};
ALPHA.forEach((p, i) => { P2C[p] = CODE[i]; C2P[CODE[i]] = p; });

// A phone that is still moving when you cut it in half has to be written as the
// parts it moves through, or the reversal lands on the wrong sound.
const ATOM = {
  AY: "AA IY", EY: "EH IY", OY: "AO IY", AW: "AA UW", OW: "AO UW",
  CH: "T SH",  JH: "D ZH",  ER: "AH R",
};

// Swaps that survive being played backwards: voicing pairs, close vowels,
// and the glide/vowel pairs that are the same gesture either way.

let LEX = new Map();   // word -> atomised phone codes

function parseLex(text) {
  const m = new Map();
  for (const line of text.split("\n")) {
    const t = line.indexOf("\t");
    if (t > 0) m.set(line.slice(0, t), line.slice(t + 1));
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

// ---- spelling it the way a person actually hears it ---------------------
//
// This part is not derived from a synthesiser. It is learned from someone
// saying words, hearing them reversed, and writing down what they would have
// to read to make that sound. Two things came out of that.
//
// The obvious one is the letters: reversed /t/ arrives fricated and gets
// written "th" or "sth", reversed /k/ becomes "kh", and most pieces open with
// a breath. The subtle one is that those spellings are compensating, not just
// describing. Saying "sthee" forward reverses into a clean /t/; saying "tea"
// does not, because a stop's burst-then-aspiration order is exactly what
// reversal destroys. So the odd-looking spelling is the accurate one.
//
// The structure came from a sentence they wrote by hand: one token per input
// word, in reverse order, which keeps word-sized gaps in the take.

let STYLE = null;

function spellChunk(ph) {
  const key = ph.join(" ");
  if (STYLE.exact[key]) return STYLE.exact[key];
  const vowel = new Set(STYLE.vowels);
  const p = ph.slice();
  // a breath at the end of a piece has no English spelling, and they drop it
  while (p.length > 1 && p[p.length - 1] === "HH") p.pop();
  const out = [];
  for (let i = 0; i < p.length; i++) {
    const cur = p[i], nxt = p[i + 1];
    if (vowel.has(cur) && nxt && vowel.has(nxt)) {
      const pair = STYLE.pair[`${cur} ${nxt}`];
      if (pair) { out.push(pair); i++; continue; }
      if (i === 0 && (cur === "IY" || cur === "IH")) { out.push("y"); continue; }
      if (i === 0 && (cur === "UW" || cur === "UH")) { out.push("w"); continue; }
    }
    out.push((STYLE.phone[cur] || ["?"])[0]);
  }
  const body = out.join("");
  return (STYLE.headBefore.includes(body[0]) ? "h" : "") + body;
}

function reverseScript(text) {
  const words = text.match(/[A-Za-z']+/g) || [];
  const unknown = [];
  const parts = [];
  for (let i = words.length - 1; i >= 0; i--) {      // last word is said first
    const w = words[i].toLowerCase();
    if (!LEX.has(w) && !LEX.has(w.replace(/'/g, ""))) unknown.push(w);
    const codes = phonesFor(w);
    if (!codes) continue;
    const ph = [...codes].reverse().map((c) => C2P[c]);
    if (ph.length) parts.push({ spell: spellChunk(ph), off: false });
  }
  return { parts, unknown, accuracy: 1 };
}

const SCRIPTER = {
  load(lexText, styleText) {
    LEX = parseLex(lexText);
    STYLE = typeof styleText === "string" ? JSON.parse(styleText) : styleText;
  },
  make: (text) => reverseScript(text),
  get words() { return LEX.size; },
  get pieces() { return Object.keys(STYLE.exact).length; },
};

if (typeof module !== "undefined") module.exports = SCRIPTER;
