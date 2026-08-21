# What was measured

Two channels carry the line to the reader: a written spelling and a recording
of the line played backwards. They were measured separately, because they turn
out to be nowhere near equally good.

## Why there is an audio channel at all

The tool has to make `reverse(take) ≈ line` true. That is the same statement as
`take ≈ reverse(line)`, so the thing the reader has to produce is the line
played backwards — an actual signal. It can be recorded and handed to them
directly. The spelling is one lossy encoding of that signal; the signal itself
is not lossy at all.

Measured through the shipped page, with a synthetic microphone
(`tools/looptest.py`), scoring each attempt against the user's own first take:

| what went into the microphone | score |
|---|---|
| a faithful imitation of the reversed audio | **99.7%** |
| someone reading the written script | **42.0%** |
| an unrelated sentence | 5.7% |

Reading the spelling recovers about two fifths of what imitating the audio
does. That gap is the reason the page leads with the recording and treats the
spelling as a crutch.

The score is DTW over MFCCs, computed in the browser. Its anchors are measured
on this exact path: capturing the same audio twice sits at 0.083 DTW, a
faithful imitation at 0.121, a script reading at 0.404, an unrelated sentence
at 0.582. `similarity()` maps that to 0–1.

## A codec bug worth recording

The first build captured with `MediaRecorder`, which encodes to Opus. Opus is
tuned for speech running forwards and shapes quantisation noise around attacks
that become decays once the take is flipped, so
`decode(encode(reverse(x))) ≠ reverse(decode(encode(x)))`. A faithful
imitation scored **0.324** DTW — most of the way to an unrelated sentence.
Capturing raw PCM off the audio graph instead brought the same take to
**0.121**. The audio maths itself was never wrong: `reverse(reverse(x))`
against `x` measures 0.000, and a reversed file against its source measures
0.004.

## The written script

    target = reverse(atomise(cmudict(line)))     # what the reversed take must sound like
    got    = atomise(espeak_ng(script))          # what an independent reader actually says
    PER    = edit_distance(target, got) / len(target)

`atomise` splits phones that are still moving when you cut them in half —
diphthongs into the two vowel targets they glide between, affricates into stop
plus fricative, `ER` into vowel plus `R`. Reversing a *list* of phonemes is not
what reversing *audio* does; atomising first is what makes the comparison mean
anything. espeak-ng is a second opinion by construction: a real letter-to-sound
engine that has never seen this project and generalises to spellings that are
not words.

| | mean PER | exact | within 20% |
|---|---|---|---|
| transliteration build, 40-phrase set | 0.395 | 0/40 | 11/40 (28%) |
| current build, 40-phrase set | **0.067** | 18/40 | 38/40 (95%) |
| current build, 50-phrase holdout | **0.078** | 15/50 | 45/50 (90%) |

A grid search over the cost weights moved this by under 0.001, which is the
signal that the weights stopped being the bottleneck — coverage of the verified
index is.

## Things that sounded clever and were not

Reversal was measured per phone by putting each one in a carrier frame,
flipping the audio, and matching it against forward renditions of every phone
(`tools/reversal_matrix.py`). Vowels come back essentially intact — 7 of 8, and
the eighth is a tie. Consonants do not: only 9 of 20 survive, and voiceless
stops systematically arrive voiced, because the burst-then-aspiration ordering
that cues voicelessness is exactly what reversal destroys.

That suggests two fixes. Both were tested against the real acoustic objective
and both lost:

| target | best script | naive phone reversal | pre-aspiration | voicing swap |
|---|---|---|---|---|
| top | `p'0t` | **0.267** | 0.331 | 0.306 |
| pot | `t'0b` | 0.260 | 0.273 | **0.225** |
| cat | `t'ak` | **0.298** | 0.415 | 0.330 |
| bat | `t'ab` | 0.397 | **0.389** | 0.478 |
| dog | `g'0t` | 0.351 | 0.348 | **0.311** |

Pre-aspiration loses 4 times in 5. Voicing compensation wins twice and loses
three times, which is noise. Naive phone reversal is already at the ceiling of
what a spelling can do, and the remaining gap belongs to the audio, not the
orthography. This is the measurement that settled the design.

## What is not fixable in the spelling

Properties of English, not bugs, and they set the floor:

- **A word that starts with `h`.** Reversed, the breath lands at the end of a
  piece. English has no way to spell a syllable-final `/h/` — `ahh` drops it,
  `ah h` gets read as the letter aitch.
- **A word that ends in `ng`.** Reversed, a piece has to *begin* with `/ŋ/`,
  which no English word does. Anything spelled `ng-` picks up a vowel and a
  hard `g`.
- **Bare lax vowels.** `AE`, `EH`, `IH`, `UH` cannot stand alone in an open
  syllable — `a` reads as "ay", `eh` as "ay", `ih` as "eye". They only survive
  inside a closed syllable.
- **Impossible onsets.** `/zl/`, `/tsn/` and friends need either an inserted
  vowel or a devoiced first consonant.

Together these are roughly 40% of the remaining spelling error. None of them
touch the audio channel, which is the other reason it leads.

## Still open

Every number here is espeak on one side or the other. A human voice has real
stop bursts and real aspiration where espeak has synthesised ones, so the
per-phone reversal table in particular deserves re-measuring against recorded
speech. The loop in the page is the instrument for that: it scores a real take
against a real take, with no synthesis anywhere in the path.
