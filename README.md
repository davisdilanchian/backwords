# Backwords

Type a line. Get a script you can say out loud. Record it, play the take
backwards, and it should say the line.

Live: https://davisdilanchian.github.io/backwords/

## How it works

Reversing a recording reverses the signal, not the phoneme list. So the target
is built in *atomised* phones — diphthongs split into the two vowel targets they
glide between, affricates into stop plus fricative — and that is what gets
reversed.

Turning those phones back into something a person can read is a search, not a
transliteration. A dynamic program segments the reversed phone string and spells
each piece with an entry from a verified index, preferring real English words
because people read those reliably. Where an exact spelling does not exist it
pays a measured penalty for the nearest sound rather than silently emitting
something unreadable.

The index is the load-bearing part. Every entry in it — about 30,000 common
words and 52,000 generated syllables — was read back by espeak-ng at build time
and kept only if the engine produced the phones we asked for. Nothing is guessed
at runtime. See [tools/](tools/) for the build and
[tools/RESULTS.md](tools/RESULTS.md) for the measurements.

Round-trip phone error rate is 0.067 on the tuning set and 0.078 on a holdout
that was never tuned against; 90% of held-out lines land within 20%. The parts
English genuinely cannot spell — a syllable-final `h`, an initial `ng` — are
listed on the page and in RESULTS.md rather than papered over.

## Layout

    index.html  app.js  style.css     the site, static, no build step
    data/lex.txt                      word -> phones, for the line you type
    data/idx.txt                      phones -> verified spellings, for the script
    tools/                            offline build and evaluation
