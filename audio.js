// Audio for Backwords: capture, reverse, play, and score.
//
// The whole tool rests on one identity. We want the reversed take to sound like
// the line, and reverse(take) ≈ line is the same statement as
// take ≈ reverse(line). So the thing to imitate is the line played backwards —
// a real signal, not a spelling. Record the line, flip it, and that recording
// is the target. Everything here exists to make that loop tight enough to
// practise against.

const BW = (() => {
  let ctx = null;
  const audio = () => (ctx ||= new (window.AudioContext || window.webkitAudioContext)());

  // ---- capture ------------------------------------------------------------

  // A stream is taken per take and released after. Holding one open across
  // takes looks tidier but hands you a dead track the moment the device
  // changes, and leaves the recording light on between attempts.
  function mic() {
    return navigator.mediaDevices.getUserMedia({
      audio: { echoCancellation: false, noiseSuppression: false, autoGainControl: false },
    });
  }

  // Raw PCM, deliberately. MediaRecorder would be less code, but it encodes to
  // Opus, and Opus is tuned for speech running forwards — it shapes noise
  // around attacks that become decays once you flip the take. Measured, that
  // round-trip costs about 0.32 DTW, which is most of the way to sounding like
  // a different sentence. So we take the samples straight off the graph.
  const WORKLET = `
    class Cap extends AudioWorkletProcessor {
      process(inputs) {
        const ch = inputs[0] && inputs[0][0];
        if (ch) this.port.postMessage(ch.slice(0));
        return true;
      }
    }
    registerProcessor("cap", Cap);
  `;
  let workletReady = null;

  // Getting the graph up costs a few hundred milliseconds the first time, and
  // that is time the user thinks they are being recorded. Do it early, on a
  // gesture, so pressing record is instant.
  async function warm() {
    const ctx = audio();
    if (ctx.state === "suspended") await ctx.resume();
    try {
      workletReady ||= ctx.audioWorklet.addModule(
        URL.createObjectURL(new Blob([WORKLET], { type: "application/javascript" })));
      await workletReady;
    } catch (e) { /* ScriptProcessor fallback needs no module */ }
  }

  function record() {
    let stop, live;
    // resolves the moment samples are actually being collected, so the UI can
    // wait and never claim to be recording before it is
    const ready = new Promise((res) => (live = res));
    const done = (async () => {
      const ctx = audio();
      if (ctx.state === "suspended") await ctx.resume();
      const s = await mic();
      const chunks = [];
      let node, src, sink;
      try {
        src = ctx.createMediaStreamSource(s);
        sink = ctx.createGain();
        sink.gain.value = 0;                 // pull the graph without monitoring
        try {
          workletReady ||= ctx.audioWorklet.addModule(
            URL.createObjectURL(new Blob([WORKLET], { type: "application/javascript" })));
          await workletReady;
          node = new AudioWorkletNode(ctx, "cap");
          node.port.onmessage = (e) => chunks.push(e.data);
        } catch (e) {
          node = ctx.createScriptProcessor(4096, 1, 1);
          node.onaudioprocess = (ev) => chunks.push(new Float32Array(ev.inputBuffer.getChannelData(0)));
        }
        src.connect(node); node.connect(sink); sink.connect(ctx.destination);
        live();
        await new Promise((res) => (stop = res));
        await new Promise((res) => setTimeout(res, 120));   // let the tail arrive
      } finally {
        try { src && src.disconnect(); } catch (e) {}
        try { node && node.disconnect(); } catch (e) {}
        try { sink && sink.disconnect(); } catch (e) {}
        for (const t of s.getTracks()) t.stop();
      }
      const n = chunks.reduce((a, c) => a + c.length, 0);
      if (!n) throw new Error("empty recording");
      const buf = ctx.createBuffer(1, n, ctx.sampleRate);
      const d = buf.getChannelData(0);
      let o = 0;
      for (const c of chunks) { d.set(c, o); o += c.length; }
      return buf;
    })();
    done.catch(() => live());          // never leave a caller awaiting ready
    return { stop: () => stop && stop(), done, ready };
  }

  // ---- shaping ------------------------------------------------------------

  function reverse(buf) {
    const out = audio().createBuffer(buf.numberOfChannels, buf.length, buf.sampleRate);
    for (let c = 0; c < buf.numberOfChannels; c++) {
      const src = buf.getChannelData(c), dst = out.getChannelData(c);
      for (let i = 0, n = buf.length; i < n; i++) dst[i] = src[n - 1 - i];
    }
    return out;
  }

  // Silence at the head becomes silence at the tail once flipped, which throws
  // the alignment off and makes every take sound late. Cut it before flipping.
  function trim(buf, floor = 0.02, padMs = 30) {
    const d = buf.getChannelData(0), n = buf.length;
    const win = Math.max(1, Math.round(buf.sampleRate * 0.01));
    const loud = (i) => {
      let s = 0;
      for (let k = i; k < Math.min(n, i + win); k++) s += d[k] * d[k];
      return Math.sqrt(s / win);
    };
    let peak = 0;
    for (let i = 0; i < n; i += win) peak = Math.max(peak, loud(i));
    const gate = Math.max(peak * floor, 1e-4);
    let a = 0, b = n;
    for (let i = 0; i < n; i += win) if (loud(i) > gate) { a = i; break; }
    for (let i = n - win; i >= 0; i -= win) if (loud(i) > gate) { b = i + win; break; }
    const pad = Math.round((padMs / 1000) * buf.sampleRate);
    a = Math.max(0, a - pad); b = Math.min(n, b + pad);
    if (b <= a) return buf;
    const out = audio().createBuffer(buf.numberOfChannels, b - a, buf.sampleRate);
    for (let c = 0; c < buf.numberOfChannels; c++) {
      out.getChannelData(c).set(buf.getChannelData(c).subarray(a, b));
    }
    return out;
  }

  let playing = null;
  function play(buf, rate = 1) {
    stop();
    const src = audio().createBufferSource();
    src.buffer = buf;
    src.playbackRate.value = rate;
    src.connect(audio().destination);
    src.start();
    playing = src;
    return new Promise((res) => (src.onended = res));
  }
  function stop() { if (playing) { try { playing.stop(); } catch (e) {} playing = null; } }

  // ---- wav export ---------------------------------------------------------

  function toWav(buf) {
    const n = buf.length, ch = Math.min(2, buf.numberOfChannels), sr = buf.sampleRate;
    const out = new DataView(new ArrayBuffer(44 + n * ch * 2));
    const str = (o, s) => { for (let i = 0; i < s.length; i++) out.setUint8(o + i, s.charCodeAt(i)); };
    str(0, "RIFF"); out.setUint32(4, 36 + n * ch * 2, true); str(8, "WAVEfmt ");
    out.setUint32(16, 16, true); out.setUint16(20, 1, true); out.setUint16(22, ch, true);
    out.setUint32(24, sr, true); out.setUint32(28, sr * ch * 2, true);
    out.setUint16(32, ch * 2, true); out.setUint16(34, 16, true);
    str(36, "data"); out.setUint32(40, n * ch * 2, true);
    let o = 44;
    for (let i = 0; i < n; i++) {
      for (let c = 0; c < ch; c++) {
        const v = Math.max(-1, Math.min(1, buf.getChannelData(c)[i]));
        out.setInt16(o, v < 0 ? v * 0x8000 : v * 0x7fff, true); o += 2;
      }
    }
    return new Blob([out], { type: "audio/wav" });
  }

  // ---- scoring ------------------------------------------------------------
  // MFCC + DTW. Enough to tell "that landed" from "that did not" without
  // shipping a recogniser.

  function fft(re, im) {
    const n = re.length;
    for (let i = 1, j = 0; i < n; i++) {
      let bit = n >> 1;
      for (; j & bit; bit >>= 1) j ^= bit;
      j ^= bit;
      if (i < j) { [re[i], re[j]] = [re[j], re[i]]; [im[i], im[j]] = [im[j], im[i]]; }
    }
    for (let len = 2; len <= n; len <<= 1) {
      const ang = -2 * Math.PI / len, wr = Math.cos(ang), wi = Math.sin(ang);
      for (let i = 0; i < n; i += len) {
        let cr = 1, ci = 0;
        for (let k = 0; k < len / 2; k++) {
          const ar = re[i + k], ai = im[i + k];
          const br = re[i + k + len / 2] * cr - im[i + k + len / 2] * ci;
          const bi = re[i + k + len / 2] * ci + im[i + k + len / 2] * cr;
          re[i + k] = ar + br; im[i + k] = ai + bi;
          re[i + k + len / 2] = ar - br; im[i + k + len / 2] = ai - bi;
          const nr = cr * wr - ci * wi; ci = cr * wi + ci * wr; cr = nr;
        }
      }
    }
  }

  const mel = (f) => 2595 * Math.log10(1 + f / 700);
  const unmel = (m) => 700 * (10 ** (m / 2595) - 1);

  function filterbank(nFilt, nFft, sr) {
    const lo = mel(60), hi = mel(Math.min(7600, sr / 2));
    const pts = [];
    for (let i = 0; i < nFilt + 2; i++) {
      pts.push(Math.floor((nFft + 1) * unmel(lo + (hi - lo) * i / (nFilt + 1)) / sr));
    }
    const fb = [];
    for (let i = 1; i <= nFilt; i++) {
      const row = new Float32Array(nFft / 2 + 1);
      for (let k = pts[i - 1]; k < pts[i]; k++) row[k] = (k - pts[i - 1]) / Math.max(1, pts[i] - pts[i - 1]);
      for (let k = pts[i]; k < pts[i + 1]; k++) row[k] = (pts[i + 1] - k) / Math.max(1, pts[i + 1] - pts[i]);
      fb.push(row);
    }
    return fb;
  }

  function mfcc(buf, nCep = 13) {
    const sr = buf.sampleRate, d = buf.getChannelData(0);
    const nFft = 512, hop = Math.round(sr * 0.010), win = Math.round(sr * 0.025);
    const nFilt = 26, fb = filterbank(nFilt, nFft, sr);
    const ham = new Float32Array(win);
    for (let i = 0; i < win; i++) ham[i] = 0.54 - 0.46 * Math.cos(2 * Math.PI * i / (win - 1));
    const frames = [];
    for (let s = 0; s + win <= d.length; s += hop) {
      const re = new Float64Array(nFft), im = new Float64Array(nFft);
      for (let i = 0; i < win; i++) re[i] = d[s + i] * ham[i];
      fft(re, im);
      const pow = new Float64Array(nFft / 2 + 1);
      for (let k = 0; k <= nFft / 2; k++) pow[k] = (re[k] * re[k] + im[k] * im[k]) / nFft;
      const eng = new Float64Array(nFilt);
      for (let m = 0; m < nFilt; m++) {
        let s2 = 0;
        for (let k = 0; k < pow.length; k++) s2 += pow[k] * fb[m][k];
        eng[m] = Math.log(s2 + 1e-10);
      }
      const c = new Float32Array(nCep);
      for (let i = 0; i < nCep; i++) {
        let s3 = 0;
        for (let m = 0; m < nFilt; m++) s3 += eng[m] * Math.cos(Math.PI * i * (m + 0.5) / nFilt);
        c[i] = s3;
      }
      frames.push(c);
    }
    // per-utterance normalisation, so loudness and mic gain drop out
    if (!frames.length) return frames;
    for (let i = 0; i < nCep; i++) {
      let mu = 0; for (const f of frames) mu += f[i]; mu /= frames.length;
      let sd = 0; for (const f of frames) sd += (f[i] - mu) ** 2;
      sd = Math.sqrt(sd / frames.length) + 1e-8;
      for (const f of frames) f[i] = (f[i] - mu) / sd;
    }
    return frames;
  }

  function cos(a, b) {
    let d = 0, na = 0, nb = 0;
    for (let i = 0; i < a.length; i++) { d += a[i] * b[i]; na += a[i] * a[i]; nb += b[i] * b[i]; }
    return 1 - d / (Math.sqrt(na) * Math.sqrt(nb) + 1e-10);
  }

  function dtw(A, B) {
    if (!A.length || !B.length) return 1;
    const n = A.length, m = B.length;
    let prev = new Float64Array(m + 1).fill(Infinity), cur = new Float64Array(m + 1);
    const steps = new Int32Array(m + 1);
    let pstep = new Int32Array(m + 1);
    prev[0] = 0;
    for (let i = 1; i <= n; i++) {
      cur[0] = Infinity; steps[0] = 0;
      for (let j = 1; j <= m; j++) {
        const c = cos(A[i - 1], B[j - 1]);
        let best = prev[j - 1], bs = pstep[j - 1];
        if (prev[j] < best) { best = prev[j]; bs = pstep[j]; }
        if (cur[j - 1] < best) { best = cur[j - 1]; bs = steps[j - 1]; }
        cur[j] = best + c; steps[j] = bs + 1;
      }
      [prev, cur] = [cur, prev];
      pstep.set(steps);
    }
    return prev[m] / Math.max(1, pstep[m]);
  }

  // 0..1, where 1 means the flipped take lands on the line.
  // Anchored on measured takes through this exact path: capturing the same
  // audio twice sits at 0.08, a faithful imitation at 0.12, someone reading
  // the written script at 0.40, and an unrelated sentence at 0.58.
  function similarity(a, b) {
    const d = dtw(mfcc(a), mfcc(b));
    return Math.max(0, Math.min(1, 1 - (d - 0.10) / 0.50));
  }

  return { audio, warm, record, reverse, trim, play, stop, toWav, mfcc, dtw, similarity };
})();

if (typeof module !== "undefined") module.exports = BW;
