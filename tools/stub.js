window.__feed = null;
navigator.mediaDevices.getUserMedia = async () => {
  const ctx = new AudioContext();
  const r = await fetch(window.__feed);
  const buf = await ctx.decodeAudioData(await r.arrayBuffer());
  const dest = ctx.createMediaStreamDestination();
  const src = ctx.createBufferSource();
  src.buffer = buf; src.connect(dest);
  src.start(ctx.currentTime + 0.45);        // let the recorder come up first
  window.__feedMs = buf.duration * 1000 + 450;
  return dest.stream;
};
