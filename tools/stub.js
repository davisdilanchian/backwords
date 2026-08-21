window.__feed = null;
navigator.mediaDevices.getUserMedia = async () => {
  const ctx = new AudioContext();
  const r = await fetch(window.__feed);
  const buf = await ctx.decodeAudioData(await r.arrayBuffer());
  const dest = ctx.createMediaStreamDestination();
  const src = ctx.createBufferSource();
  src.buffer = buf; src.connect(dest);
  src.start(ctx.currentTime + 1.2);         // generous: setup must never clip the head
  window.__feedMs = buf.duration * 1000 + 1200;
  return dest.stream;
};
