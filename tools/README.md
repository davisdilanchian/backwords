# tools — the offline half of Backwords

The page is static and does all its work in the browser. This directory holds
the things that cannot run there: the build that decides which spellings are
allowed, the measurements that settled the design, and the end-to-end test.

## Requirements

    apt-get install espeak-ng ffmpeg
    pip install wordfreq                      # frequency ranking for readability
    pip install librosa numpy playwright      # measurement and the browser test

## Rebuilding data/

Run in order, from this directory:

    python3 build_lexicon.py     # cmudict wordlist -> espeak_lex.json      (~2 min)
    python3 build_syllabary.py   # generate + verify syllables              (~5 min)
    python3 build_index.py       # merge words + syllables -> index.json
    python3 pack.py              # -> ../data/lex.txt, ../data/idx.txt

The rule the build exists to enforce: **the app never invents a spelling at
runtime.** Every piece it can emit was written down, read back by espeak-ng,
and kept only if the engine returned the phones we asked for. Spellings that
read the wrong way — `zz` becoming "zee zee", `eh` becoming "ay", `-th` going
voiceless — are dropped at build time instead of surprising someone with a
microphone. `build_syllabary.py` throws about 460,000 candidate spellings at
espeak-ng and keeps the ~52,000 that survive.

`cmudict.json` is the input side only: it decides what phones the line the user
*typed* is made of. It is not served to the browser.

## Checking it

    python3 evaluate.py -v          # spelling round-trip, against the shipped app.js
    python3 looptest.py             # the real page, real browser, synthetic microphone
    python3 acoustic_test.py        # synthesise, reverse, measure

`looptest.py` is the one that tests the thing the tool actually claims. It
drives the page in Chromium with a fake mic, runs four scenarios through the
whole chain — capture, trim, reverse, MFCC, DTW, verdict — and asserts the
scores come out in the right order. If a faithful imitation stops scoring above
0.75, or an unrelated sentence above 0.25, it fails.

`evaluate.py` covers the written script only. `testset.txt` is what the cost
weights were tuned on; `holdout.txt` was never used for tuning.

## Measurements

    python3 reversal_matrix.py      # what each phone becomes when reversed
    python3 stops_experiment.py     # pre-aspiration and voicing swaps, tested

Both are reported in `RESULTS.md`, including the two plausible-sounding fixes
that lost to doing nothing.
