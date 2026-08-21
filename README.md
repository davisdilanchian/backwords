# Backwords

Say a line backwards well enough that playing the take in reverse says it
properly.

Live: https://davisdilanchian.github.io/backwords/

## How it works

The tool has to make `reverse(take) ≈ line` true. That is the same statement as
`take ≈ reverse(line)` — so the thing you have to say is *the line played
backwards*, which is a real signal, not a spelling. So the page records you
saying the line normally, flips it, and hands it back. You copy what you hear,
it flips your take, and you find out whether it landed.

A written script comes along for the ride, because having something to read
helps. It is built by reversing the line in *atomised* phones — diphthongs
split into the two vowel targets they glide between, affricates into stop plus
fricative — and then spelling that with pieces from an index where every entry
was read back by espeak-ng at build time and kept only if it produced the
phones we asked for. Nothing is guessed at spelling time.

But the two channels are not close. Measured through the page:

| what you do | how close the flipped take lands |
|---|---|
| copy the reversed audio | **99.7%** |
| read the written script | 42.0% |
| say something unrelated | 5.7% |

So the audio leads and the spelling is a crutch. That ordering is the whole
design, and it came out of measurement rather than taste — including two
sensible-sounding fixes to the spelling that turned out to be worse than doing
nothing. See [tools/RESULTS.md](tools/RESULTS.md).

Everything runs in the browser. Nothing is uploaded.

## Layout

    index.html                    the page
    app.js                        the loop: record, flip, score, retry
    audio.js                      capture, reverse, trim, MFCC + DTW scoring
    script.js                     the written crutch
    data/lex.txt                  word -> phones, for the line you type
    data/idx.txt                  phones -> verified spellings, for the script
    tools/                        build, measurements, end-to-end test
