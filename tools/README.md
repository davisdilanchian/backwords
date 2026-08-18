# tools — the offline half of Backwords

The site is static and runs the search in the browser. Everything that decides
*which spellings are allowed* happens here, offline, and gets baked into
`data/idx.txt`.

The point of this directory is one rule: **the app never invents a spelling at
runtime.** Every piece it can emit was written down, read back by an
independent grapheme-to-phoneme engine (espeak-ng), and kept only if the engine
said the same phones we asked for. Spellings that read the wrong way — `zz`
becoming "zee zee", `eh` becoming "ay", `-th` going voiceless — are dropped at
build time instead of shipping and surprising someone with a microphone.

## Requirements

    apt-get install espeak-ng ffmpeg
    pip install wordfreq                    # word frequencies, for readability ranking
    pip install pocketsphinx librosa numpy  # only for acoustic_test.py

## Rebuilding data/

Run in order, from this directory:

    python3 build_lexicon.py     # cmudict wordlist -> espeak_lex.json   (~2 min)
    python3 build_syllabary.py   # generate + verify syllables -> syllabary.json (~5 min)
    python3 build_index.py       # merge words + syllables -> index.json
    python3 pack.py              # -> ../data/lex.txt, ../data/idx.txt

`build_syllabary.py` is the interesting one. It takes a table of candidate
graphemes per phone, expands it over syllable templates (V, CV, VC, CVC, plus
onset and coda clusters), and throws the whole cross-product — around 460,000
spellings — at espeak-ng. Roughly 52,000 survive. The survivors are the
alphabet the app is allowed to write in.

`cmudict.json` is the input side only: it decides what phones the line the user
*typed* is made of. It is not served to the browser.

## Checking it

    python3 evaluate.py -v       # phone error rate against the shipped app.js
    python3 acoustic_test.py     # synthesise, reverse the audio, measure

`evaluate.py` is the one to trust. It runs the real `app.js` through node,
reads the script it produced with espeak-ng, reverses those phones, and
compares against the line that went in. `testset.txt` is what the cost weights
were tuned on; `holdout.txt` was never used for tuning.

See `RESULTS.md` for the numbers and for what is not fixable.
