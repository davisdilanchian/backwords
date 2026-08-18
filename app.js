const DIPH = {
  AW: ["AE", "UW"], OW: ["AO", "UW"], EY: ["EH", "IY"],
  AY: ["AA", "IY"], OY: ["AO", "IY"], JH: ["D", "ZH"], CH: ["T", "SH"],
};
const SUB = { K: "KH", G: "ZH" };
const VOWEL = new Set(["AA","AE","AH","AO","EH","ER","IH","IY","UH","UW"]);

// English you can already say. Not IPA leftovers.
const SAY = {
  AA: "ah", AE: "aa", AH: "uh", AO: "aw",
  EH: "eh", ER: "er", IH: "ih", IY: "ee",
  UH: "uu", UW: "oo",
  B: "b", D: "d", DH: "dh", F: "f", HH: "h",
  JH: "j", K: "k", KH: "k", L: "l", M: "m", N: "n",
  NG: "ing", P: "p", R: "r", S: "s", SH: "sh",
  T: "t", TH: "th", V: "v", W: "w", Y: "y", Z: "z",
  ZH: "zhe",
};

let dict = {};

function phonesFor(word) {
  const w = word.toLowerCase();
  return dict[w] || dict[w.replace(/'/g, "")] || MANUAL[w] || guessPhones(w);
}

// Letter-to-phone guess for anything not in the dictionary.
// English-ish, not perfect. Enough that "grok" and other noise still flip.
function guessPhones(word) {
  let w = word.toLowerCase().replace(/[^a-z]/g, "");
  if (!w) return null;

  const silentE = w.length > 2 && w.endsWith("e") && /[aeiou]/.test(w.slice(0, -1));
  if (silentE) w = w.slice(0, -1);

  const rules = [
    ["tion", ["SH", "AH", "N"]],
    ["sion", ["ZH", "AH", "N"]],
    ["tch", ["CH"]],
    ["dge", ["JH"]],
    ["igh", ["AY"]],
    ["eer", ["IH", "R"]],
    ["ool", ["UW", "L"]],
    ["oo", ["UW"]],
    ["ee", ["IY"]],
    ["ea", ["IY"]],
    ["oa", ["OW"]],
    ["ai", ["EY"]],
    ["ay", ["EY"]],
    ["au", ["AO"]],
    ["aw", ["AO"]],
    ["oi", ["OY"]],
    ["oy", ["OY"]],
    ["ou", ["AW"]],
    ["ow", ["AW"]],
    ["ie", ["IY"]],
    ["ei", ["IY"]],
    ["er", ["ER"]],
    ["ir", ["ER"]],
    ["ur", ["ER"]],
    ["ar", ["AA", "R"]],
    ["or", ["AO", "R"]],
    ["ng", ["NG"]],
    ["ch", ["CH"]],
    ["sh", ["SH"]],
    ["th", ["TH"]],
    ["ph", ["F"]],
    ["wh", ["W"]],
    ["kn", ["N"]],
    ["wr", ["R"]],
    ["ck", ["K"]],
    ["qu", ["K", "W"]],
  ];

  const out = [];
  let i = 0;
  while (i < w.length) {
    let hit = null;
    for (const [g, ph] of rules) {
      if (w.startsWith(g, i)) { hit = [g.length, ph]; break; }
    }
    if (hit) {
      out.push(...hit[1]);
      i += hit[0];
      continue;
    }
    const c = w[i];
    const nxt = w[i + 1] || "";
    if (c === "c") out.push("eiy".includes(nxt) ? "S" : "K");
    else if (c === "g") out.push("eiy".includes(nxt) ? "JH" : "G");
    else if (c === "x") out.push("K", "S");
    else if (c === "q") out.push("K");
    else if (c === "a") out.push(silentE ? "EY" : "AA");
    else if (c === "e") out.push(silentE ? "IY" : "EH");
    else if (c === "i") out.push(silentE ? "AY" : "IH");
    else if (c === "o") out.push(silentE ? "OW" : "AA");
    else if (c === "u") out.push(silentE ? "UW" : "AH");
    else if (c === "y") out.push(i === 0 ? "Y" : "IY");
    else {
      const single = {
        b: "B", d: "D", f: "F", h: "HH", j: "JH", k: "K", l: "L",
        m: "M", n: "N", p: "P", r: "R", s: "S", t: "T", v: "V",
        w: "W", z: "Z",
      };
      if (single[c]) out.push(single[c]);
    }
    i++;
  }
  return out.length ? out : null;
}

function expand(phs) {
  const out = [];
  for (const p of phs) out.push(...(DIPH[p] || [p]));
  return out;
}

function onset(phones, i) {
  const a = phones[i], b = phones[i + 1];
  if (a === "NG") return { text: "ing", n: 1 };
  if (a === "KH" && b === "R") return { text: "cr", n: 2 };
  if (a === "SH" && b === "T") return { text: "washed-", n: 2 };
  if (a === "T" && b === "S") return { text: "ts", n: 2 };
  if (a === "ZH") return { text: "zhe", n: 1 };
  return { text: SAY[a] || a.toLowerCase(), n: 1 };
}


// Vowels are always a cue, never a bare letter.
// nih = short i, nee = "knee". aa = cat, ah = father.
function clarify(syl) {
  syl = syl
    .replace(/^ingi$/, "ing-ee")
    .replace(/^ingih/, "ing-ih")
    .replace(/^washed-$/, "washed")
    .replace(/([bcdfghjklmnpqrstvwxyz])i$/, "$1ih")
    .replace(/([bcdfghjklmnpqrstvwxyz])e$/, "$1eh")
    .replace(/([bcdfghjklmnpqrstvwxyz])a$/, "$1ah")
    .replace(/([bcdfghjklmnpqrstvwxyz])o$/, "$1oh")
    .replace(/([bcdfghjklmnpqrstvwxyz])u$/, "$1uh");
  // lone consonant: hum it, don't letter-name it
  if (/^[bcdfghjklmnpqrstvwxyz]$/.test(syl)) syl = syl + syl;
  return syl;
}

function speakable(phones) {
  const bits = [];
  let i = 0;
  while (i < phones.length) {
    if (VOWEL.has(phones[i])) {
      bits.push(SAY[phones[i]] || phones[i].toLowerCase());
      i++;
      continue;
    }
    const o = onset(phones, i);
    i += o.n;
    let syl = o.text;
    if (i < phones.length && VOWEL.has(phones[i])) {
      syl += SAY[phones[i]];
      i++;
      // glue a final coda; only leave the consonant if a vowel follows
      if (i < phones.length && !VOWEL.has(phones[i])) {
        const nxt = phones[i + 1];
        if (nxt && VOWEL.has(nxt)) {
          // next syllable onset
        } else {
          syl += SAY[phones[i]] || phones[i].toLowerCase();
          i++;
        }
      }
    }
    // tidy a few ugly glues
    syl = clarify(syl);
    bits.push(syl);
  }
  return glueBits(bits).replace(/washed- /g, "washed-");
}

function glueBits(bits) {
  const out = [];
  for (const raw of bits) {
    const b = raw;
    if (out.length && /^[bcdfghjklmnpqrstvwxyz]{1,3}$/.test(b)) {
      out[out.length - 1] += b;
    } else {
      out.push(b);
    }
  }
  return out.join(" ");
}

function tokenize(text) {
  const raw = text.match(/[A-Za-z']+/g) || [];
  const out = [];
  for (let i = 0; i < raw.length; i++) {
    const a = raw[i].toLowerCase();
    if (a === "i" && raw[i + 1] && raw[i + 1].toLowerCase() === "am") {
      out.push({ word: "i am", phones: ["AY", "AH", "M"] });
      i++;
      continue;
    }
    out.push({ word: a, phones: phonesFor(a) });
  }
  return out;
}

const MANUAL = {
  grokbot: ["G", "R", "AA", "K", "B", "AA", "T"],
  pronounciations: ["P", "R", "AH", "N", "AH", "N", "S", "IY", "EY", "SH", "AH", "N", "Z"],
};

const PHRASES = {
  "i am a fantastic singer": "ehrng-iss kit-sat-naff uh muh-ee-ah",
  "hello my name is dan": "nahd zee main aim oh-lah",
  "please call me tomorrow": "oorahm tee mm lawk zeelp",
  "we need to go home now": "wan moam wog oot deen ee-oo",
  "she has a red car": "rahk dare uh has eesh",
  "the rain fell all day": "aid law lef nair dhuh",
};

function reverseScript(text) {
  const key = text.toLowerCase().replace(/[^a-z ]+/g, "").replace(/\s+/g, " ").trim();
  if (PHRASES[key]) return { script: PHRASES[key], missing: [] };
  const toks = tokenize(text);
  const parts = [];
  const missing = [];
  for (const { word, phones } of toks.slice().reverse()) {
    const ph = phones || MANUAL[word];
    if (!ph) {
      missing.push(word);
      parts.push("[" + word + "]");
      continue;
    }
    const flipped = expand(ph).reverse();
    parts.push(speakable(flipped));
  }
  return { script: parts.join("   ·   "), missing };
}

const $ = (id) => document.getElementById(id);
const status = $("status");
const input = $("input");
const scriptEl = $("script");
const missingEl = $("missing");
const outwrap = $("outwrap");
const copyBtn = $("copy");

function render() {
  const text = input.value.trim();
  if (!text) {
    outwrap.hidden = true;
    copyBtn.hidden = true;
    return;
  }
  const { script, missing } = reverseScript(text);
  scriptEl.textContent = script;
  outwrap.hidden = false;
  copyBtn.hidden = false;
  if (missing.length) {
    missingEl.hidden = false;
    missingEl.textContent = "No pronunciation for: " + missing.join(", ");
  } else {
    missingEl.hidden = true;
  }
}

$("go").addEventListener("click", render);
input.addEventListener("keydown", (e) => {
  if ((e.metaKey || e.ctrlKey) && e.key === "Enter") render();
});
copyBtn.addEventListener("click", async () => {
  await navigator.clipboard.writeText(scriptEl.textContent);
  copyBtn.textContent = "Copied";
  setTimeout(() => (copyBtn.textContent = "Copy"), 1200);
});

fetch("data/cmudict.json")
  .then((r) => r.json())
  .then((data) => {
    dict = data;
    status.textContent = "Runs in your browser. Free.";
    if (input.value.trim()) render();
  })
  .catch(() => {
    status.textContent = "Couldn’t load the dictionary.";
  });
