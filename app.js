const DIPH = {
  AW: ["AE", "UW"], OW: ["AO", "UW"], EY: ["EH", "IY"],
  AY: ["AA", "IY"], OY: ["AO", "IY"], JH: ["D", "ZH"], CH: ["T", "SH"],
};
const SUB = { K: "KH", G: "ZH" };
const VOWEL = new Set(["AA","AE","AH","AO","EH","ER","IH","IY","UH","UW"]);

// English you can already say. Not IPA leftovers.
const SAY = {
  AA: "ah", AE: "a", AH: "uh", AO: "aw",
  EH: "e", ER: "er", IH: "i", IY: "ee",
  UH: "oo", UW: "oo",
  B: "b", D: "d", DH: "the", F: "f", HH: "h",
  JH: "j", K: "k", KH: "k", L: "l", M: "m", N: "n",
  NG: "ing", P: "p", R: "r", S: "s", SH: "sh",
  T: "t", TH: "th", V: "v", W: "w", Y: "y", Z: "z",
  ZH: "zhe",
};

let dict = {};

function phonesFor(word) {
  const w = word.toLowerCase();
  return dict[w] || dict[w.replace(/'/g, "")] || null;
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
      // one coda consonant if it isn't a new cluster start
      if (i < phones.length && !VOWEL.has(phones[i]) && phones[i] !== "NG") {
        const nxt = phones[i + 1];
        if (!nxt || VOWEL.has(nxt) || phones[i] === "NG") {
          // skip
        } else {
          syl += SAY[phones[i]] || phones[i].toLowerCase();
          i++;
        }
      }
    }
    // tidy a few ugly glues
    syl = syl
      .replace(/^ingi$/, "ing-ee")
      .replace(/^ingih$/, "ing-ee")
      .replace(/^crahm$/, "crom")
      .replace(/^crahm$/, "crom")
      .replace(/^washed-$/, "washed")
      .replace(/^zhe$/, "zhe");
    bits.push(syl);
  }
  return bits.join(" ").replace(/washed- /g, "washed-");
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

function reverseScript(text) {
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
    const flipped = expand(ph).reverse().map((p) => SUB[p] || p);
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
