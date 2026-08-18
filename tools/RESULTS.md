# What was measured

## The metric

The app's claim is: read this script aloud, reverse the take, hear the line you
typed. The part the app controls is the spelling, so that is what is measured.

    target = reverse(atomise(cmudict(line)))     # what the reversed take must sound like
    got    = atomise(espeak_ng(script))          # what an independent reader actually says
    PER    = edit_distance(target, got) / len(target)

`atomise` splits phones that are still moving when you cut them in half —
diphthongs into the two vowel targets they glide between, affricates into stop
plus fricative, `ER` into vowel plus `R`. Reversing a *list* of phonemes is not
what reversing *audio* does; atomising first is what makes the comparison mean
anything.

espeak-ng is a second opinion by construction: a real letter-to-sound engine
that has never seen this project and generalises to spellings that are not
words. It is the closest available stand-in for a stranger reading the script
cold.

## Round-trip phone error rate

| | mean PER | exact | within 20% |
|---|---|---|---|
| previous build, 40-phrase set | 0.395 | 0/40 | 11/40 (28%) |
| current build, 40-phrase set  | **0.067** | 18/40 | 38/40 (95%) |
| current build, 50-phrase holdout | **0.078** | 15/50 | 45/50 (90%) |

The holdout was never used to tune the cost weights. A grid search over the
weights moved the result by under 0.001, which is the signal that the weights
stopped being the bottleneck — coverage of the verified index is.

## Acoustic check

`acoustic_test.py` synthesises the script, reverses the waveform, and measures
MFCC-DTW distance to synthesised audio of the original line. Same voice on both
sides, so voice is not a confound.

| | distance |
|---|---|
| ceiling — same line, slight speed change | 0.009 |
| **this build, reversed** | **0.299** |
| previous build, reversed | 0.367 |
| chance — reversed script of a different line | 0.644 |

On a scale where 1 is the ceiling and 0 is chance: previous build 0.43, this
build 0.55, closer on 18 of 20 phrases.

That 0.55 is the honest headline. Getting the phones right is necessary and not
sufficient: reversing audio also reverses every formant transition, every stop
burst, and the whole prosodic envelope, and no choice of spelling recovers
those. A phone-accurate script is the ceiling this approach has, not a promise
of a clean listen.

An offline phone recogniser was also tried on the reversed audio. It scores
0.740 against the target where its own noise floor on *forward* synthetic
speech is 0.737, so it cannot separate a good script from a bad one here and is
reported only as a sanity check.

## What is not fixable

These are properties of English, not bugs, and they set the floor:

- **A word that starts with `h`.** Reversed, the breath lands at the end of a
  piece. English has no way to spell a syllable-final `/h/` — `ahh` drops it,
  `ah h` gets read as the letter aitch. The app tells the reader to exhale.
- **A word that ends in `ng`.** Reversed, a piece has to *begin* with `/ŋ/`,
  which no English word does. Anything spelled `ng-` picks up a vowel and a
  hard `g`. It comes back closer to `n`.
- **Bare lax vowels.** `AE`, `EH`, `IH`, `UH` cannot stand alone in an open
  syllable — `a` reads as "ay", `eh` as "ay", `ih` as "eye", `oo` as "oo" not
  "uh". They only survive inside a closed syllable, so a target that isolates
  one has to borrow a neighbouring consonant or take the error.
- **Impossible onsets.** `/zl/`, `/tsn/` and friends need either an inserted
  vowel or a devoiced first consonant. Both cost one phone.

Together these account for roughly 40% of the remaining error. The rest is
voicing pairs and glide/vowel pairs (`W`/`UW`, `Y`/`IY`), which the strict
metric counts in full even though reversal degrades voicing cues anyway.
