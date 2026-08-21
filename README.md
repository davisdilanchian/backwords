# tools — the offline half of Backwords

The page is static and does all its work in the browser. This directory holds
the things that cannot run there: the build that decides which spellings are
allowed, the measurements that settled the design, and the end-to-end test.

## Requirements

    apt-get install espeak-ng ffmpeg
    pip install wordfreq                      # frequency ranking for readability
    pip install librosa numpy playwright      # measurement and the browser test

## How the speller works now

It is learned from a person, not verified against a synthesiser.

    python3 learn_style.py      # calibration answers -> calibration/style.json
    python3 render_style.py     # render a line, and check it against held-out lines

`style.json` is under two kilobytes and replaces a 1.75 MB verified index. It
holds which letters that person uses for each reversed phone, plus the rules
that only show up at word length: close vowels turning into glides, vowel runs
squashing together, the trailing breath being dropped, and the breathy onset
that opens most pieces.

**Why the espeak-verified index was retired.** It required that espeak-ng read a
spelling back as exactly the target phones. A person spelling reversed speech
writes `sthee` where espeak wants `tea` — and the person is right. Saying a
fricated `sth` forward reverses into a clean /t/; saying `t` does not, because
the burst-then-aspiration ordering that marks a stop is precisely what reversal
destroys. The verifier scored the compensating spelling as an error, so the
whole index was optimised away from the spellings that actually work. An
earlier experiment here concluded pre-aspiration did not help; that conclusion
came from espeak's synthetic stops and a human overturned it.

The old build still runs if you want it — `build_lexicon.py`,
`build_syllabary.py`, `build_index.py` — but only `pack.py`'s lexicon half
feeds the page now.

## Rebuilding data/

    python3 build_lexicon.py     # cmudict wordlist -> espeak_lex.json      (~2 min)
    python3 pack.py              # -> ../data/lex.txt   (word -> phones)
    python3 learn_style.py       # -> calibration/style.json, copy to ../data/

`cmudict.json` is the input side only: it decides what phones the line the user
*typed* is made of. It is not served to the browser.

## Checking it

    python3 evaluate.py             # renderer vs lines a person spelled by hand
    python3 looptest.py             # the real page, real browser, synthetic microphone
    python3 acoustic_test.py        # synthesise, reverse, measure

`looptest.py` is the one that tests the thing the tool actually claims. It
drives the page in Chromium with a fake mic, runs four scenarios through the
whole chain — capture, trim, reverse, MFCC, DTW, verdict — and asserts the
scores come out in the right order. If a faithful imitation stops scoring above
0.75, or an unrelated sentence above 0.25, it fails.

`evaluate.py` compares the renderer against lines someone wrote themselves.
Add more by using the page, saving your spelling for a line, and dropping the
download into `calibration/lines-<name>.json`. Whole lines are worth far more
than single sounds — the glides, squashed vowels and dropped breaths only
appear at word length.

## Teaching it a person's spelling

The build verifies spellings with espeak-ng, which reads invented syllables as
fluently as it reads words. That is the whole blind spot: it cannot tell
`moss is a dour tissue` from `slesh eess sless eesh`, and only one of those can
be read aloud. A person can tell instantly, so ask one.

    python3 pick_units.py       # rank chunks by how much work they do -> units.json
                                #   54 chunks cover 50% of everything the app emits
                                #   155 cover 70%, 300 cover 85%

Then open `calibrate.html` in the browser. It walks the ranked list: say the
prompt word, it plays your own voice back reversed, and you write down what you
would have to read to make that sound. Answers persist in the browser, so the
session can be stopped and resumed, and a partial pass is still useful because
the list is ordered by value. Download the result at the end.

    python3 build_index.py
    python3 apply_calibration.py backwords-spellings.json   # --preview to look first
    python3 pack.py

Your spelling outranks everything else for the chunks you answered. Where
espeak disagrees with you, the tool says so and ships your answer regardless —
you are the one who has to read it.

## Measurements

    python3 reversal_matrix.py      # what each phone becomes when reversed
    python3 stops_experiment.py     # pre-aspiration and voicing swaps, tested

Both are reported in `RESULTS.md`, including the two plausible-sounding fixes
that lost to doing nothing.
