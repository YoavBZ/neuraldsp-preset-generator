# Measuring how close a preset is to a recording

Every decision in this project rests on one number: how close a preset's sound is
to a recording. This document records what that number is, why it changed on
2026-10-03, and what it still cannot be trusted for.

## The verdict

- **`unpaired-v3` and its corrections (v3c, `corrected_pair`) are retired as
  judges of closeness.** They stay as search objectives where nothing better runs
  yet, but no conclusion may rest on them, and a search answer must never be
  judged by the score it was optimised against.
- **The judge is `analysis/aligned.py`**: the preset rendered through the DI of the
  very take the recording captured, compared with that recording frame by frame.
  It applies wherever a part's own DI exists (the validation material) and no more
  than half the scored frames are pauses; it refuses the rest. It does not apply to
  the product's song-only use, which has no DI.
- **It is not validated yet.** Listening validation is stage 0b of
  `docs/supervised-model-plan.md` (about 100 trials). Until then it is the best
  measure available, not ground truth.

## Why v3 was retired

Three independent reviews (perceptual, empirical, setup), each measuring on the
project's own renders and amp tracks, and one blind listening test.

**Listening.** In 16 blind R-A-B trials, the shipped template against the
real-guitar search answer, the listener chose the template 15 times. Agreement
with the listener:

| Distance | Agreed |
|---|---|
| `unpaired-v3` as stored | 5/16 |
| `corrected_pair` | 7/16 |
| v3c (kill-test version) | 9–10/16 |
| aligned log-mel (ALM, frozen before the answers were read) | 12/16 |
| an unpaired long-term loudness distance (frozen) | 12/16 |
| ALM with its level offset removed | 14/16 |
| `analysis/aligned.py` (built after the answers were read) | 12/14 scored |

`analysis/aligned.py` refuses the two trials on Lost Alive, where over half the
scored frames are pauses; with that refusal off it agrees on 14 of 16. Its design was
chosen after the answers were read: the per-frame floor's family scored 14 where a
per-band floor's scored 11–13, and that was in view when the choice was made.

Because the listener chose the template 15 times out of 16, a score that always
says "template" gets 15/16. The informative part is the 8 trials where
`corrected_pair` called the search answer closer: the listener disagreed on all 8.
The search answers had reverb raised (to 94% on one), tremolo switched on, input
gain up 10–20 dB and EQ bands pushed to ±12 dB. v3 favoured them; the listener
heard them as wrong ("guitar barely audible" on two).

**Controlled changes.** A known one-octave EQ of ±1, 2 or 3 dB at 400 Hz, 1.6 kHz
or 5 kHz, applied to the template's render on the 27 parts where the DI plays in
both halves, scored against the real amp track (486 changes):

| Distance | Same sign on both halves | Falls when the EQ shrinks the octave's gap to the recording |
|---|---|---|
| v3, level left out | 58% | 56% (chance) |
| v3c | 74% | 68% |
| ALM | 92% | 90% |
| `analysis/aligned.py` | 94% | 88% |

So searches driven by v3 followed a signal that barely points the right way.

The last column counts the 386 changes that unambiguously move the octave towards
or away from the recording, with "the octave's gap" measured against the total
power. That ground truth is a choice. Under three conventions:

| Octave gap measured against | `analysis/aligned.py` | with `bands="union"` | ALM |
|---|---|---|---|
| total power | 87.6% | 85.8% | 89.6% |
| loudness alone | 86.7% | 84.9% | 89.0% |
| the mean over the scored mel bands | 87.8% | 88.8% | 88.6% |

ALM points the right way slightly more often; read them as close. All are weakest
at 400 Hz (73% here, ALM 74%).

**Specific defects in v3**, each reproduced by a reviewer:

- Its MFCC term measures the noise floor above 10 kHz, 22–53 dB below the amp
  track's own. Adding -40 dB of pink noise to a render brought it *closer* to the
  amp track in 8 of 8 cases.
- Its tilt term jumps when a band crosses its 40-dB inclusion boundary: an 80 Hz
  high-pass moved it from 0.08 to 4.31 on one part while the spectrum barely moved.
- Its dynamics terms (crest over the whole excerpt including gaps, attack, LRA on
  3-s blocks) were below chance against the listener (5/16).
- It has no working measure of time effects: a 420 ms echo at -6 dB scored 0.7× an
  octave EQ and moved one candidate closer.
- Its third-octave bands put 26% of the weight below 200 Hz where hearing puts
  about 12%, and 21% above 1.6 kHz against about 47%.
- 80% split-half stability needs a v3c gap of about a 6 dB octave EQ; ALM gets
  there at 1–2 dB.

## What the aligned distance does

Both signals are loudness-normalised to -23 LUFS. Log-mel spectra (64 bands,
50 Hz–16 kHz, frames of 1024, 2048 and 4096 samples) are compared cell by cell
after:

- **Alignment.** The recording's lag behind the render belongs to the recording,
  not to the preset, so it is estimated once per recording and must be passed for
  every candidate. `estimate_lag` pools several unlike renders: the peak of their
  summed 80 Hz–2 kHz cross-correlation magnitudes, within ±15 ms of the catalogued
  lag less the plugin latency; a higher peak just outside that window is refused.
  - Catalogued lags are quantised to 10 ms and off by 2.5 ms or more on 9 of 43
    parts, by 42 ms on Prodigal 4. There the catalogued hint is refused, as it
    should be, and the lag is found without it (it also gives the lowest distance).
    `estimate_lag` only refuses; a caller widens the window itself.
  - Pooled over nine renders, the estimate agrees with another estimate of the
    same family (a full-band correlation against one same-take render) to 0.3 ms
    on 25 of 27 parts. The misses are Drag Me Down 4 (0.3 ms, borderline) and
    Strangest Places, whose correlation has two peaks; pooling the whole panel
    there picks the other one. Which renders are pooled matters elsewhere too
    (Signs 3: 16 samples from nine of them, -29 from the whole panel), so a study
    should record one lag per recording and reuse it.
  - One render alone was 6 ms off on one part, and earlier versions that estimated
    per candidate over ±50 ms missed by up to about 2,000 samples on the listening
    trials. GCC-PHAT finds spurious zero-lag peaks on distorted renders.
  - The lag that minimises the distance sits a median 0.75 ms later than the
    estimate (26 of 27 parts), at a cost of at most 0.055 dB.
- **Frames**: where the DI plays, plus 1.5 s after, including notes played just
  before the window, so reverb and delay tails count where a part leaves gaps. On
  the 27 parts where the DI plays most of the time the tails changed nothing: the
  template with its delay, reverb and compressor on scored 0.97 dB from the same
  template with them off, with or without tails, against 4.49 between two random
  factory presets (median over 5 fixed draws, 3.97–4.86).
- **Bands**: by default those within 30 dB of the recording's long-term peak, the
  same for every candidate. On the stage-0b windows the highest such band is under
  6.4 kHz on 27 of 29 parts and under 4 kHz on 8; on K1's windows 21–56 of the 64
  bands are scored. Treble above that is not scored, so excess top end the
  recording lacks is barely seen: a +12 dB octave at 8 kHz, scored against the
  real recordings on the 8 parts where it moves the render away from them, costs
  +0.10 dB. `bands="union"` adds the bands within 30 dB of the candidate's own
  peak; there the same boost costs +0.26 dB, but known EQ moves are tracked less
  well (the table above) and halves agree less often (91% against 94%). Scoring
  every band costs more still (83% right way, 88% across halves). This is a
  trade-off the listening test should settle: stage 0b scores both band sets, and
  K1 conclusions about search answers that raised the top EQ bands carry this
  caveat.
- **Level**: the render's level difference is taken out first (the median over the
  cells where the DI plays and the recording is above its floor), then what is left
  of the mean after the floor. ALM's mean signed difference exceeded 2 dB on 71% of
  comparisons, and output level is a separate control.
- **Floor**: in each frame both sides are clamped 40 dB under the recording's
  loudest band in that frame, a rough stand-in for masking. 40 dB is a judgement
  call between measured alternatives (pink noise at -40 dB added to 6 renders on
  each of the 27 active parts, counted where it brought the render more than
  0.1 dB closer to the amp track; the EQ test above, total-power convention):

  | Floor | Noise rewarded | EQ right way | Mel-band convention |
  |---|---|---|---|
  | none | 40 of 162 | 87.3% | 89.6% |
  | 30 dB | 2 of 162 | 82.1% | 85.9% |
  | 40 dB (used) | 8 of 162 | 87.6% | 87.8% |
  | 50 dB | 24 of 162 | 88.9% | 89.6% |

  Applying the floor before the level step instead gave 0 of 162 but pointed the
  right way less often (84.5%, earlier band set). The 8 cases left are not pauses:
  they are on Signs 2 and Today's The Day 07 and 10, on renders (two of them the
  template, the worst Benny Tele, by 1.79 dB on Today's 07) that sit 12–30 dB
  under the recording at 1.8–5 kHz, so the noise fills a real tonal deficit. When a render is much darker than the
  recording, the distance cannot tell broadband noise from missing treble. In
  pauses the recording's own hiss is the loudest thing in the frame, presumably
  audible, so matching it still counts; whether this listener hears it is one of
  the listening checks below.
- **Refusals.** A window where more than half the scored frames are pauses (tails
  where the DI is silent) is refused; a silent lead-in is not scored and does not
  count. On the 1–10 s windows that refuses 6 of 43 parts (Hikikomori for too few
  frames). Where pauses dominate, the ranking hangs on them: on the 15 sparse
  parts, scoring only the frames where the DI plays against scoring all of them
  changed the best preset on 6 and moved the ranking to a median ρ of 0.968 (0.199
  at worst), while on the 27 active parts it changed nothing (measured before the
  band change). A recording inaudible where the DI plays is refused too, and
  non-finite or channels-first input raises an error.
- **No bleed handling.** An earlier version dropped bands where the recording held
  other instruments while the DI rested. On the 27 active parts the DI never rests
  long enough to measure that, and where it does the check took a high-gain
  preset's own noise, or a band holding only the recording's noise floor, for
  bleed. The catalogue has no bleed flag yet, and the refusal above is not a bleed
  check: it refuses the two live-room parts whose top octave is mostly cymbals on
  their 1–10 s windows because pauses dominate there, not because of the cymbals.

It reports the distance in dB and two parts: `tonal` (the long-term per-band
difference) and `temporal` (what is left frame by frame: attack, drive texture,
tails).

### How it responds to known changes

Each change applied to a real render and scored against the unchanged render,
median over 27 parts, in units of a +3 dB octave EQ at 1.6 kHz:

| Change | ALM | `analysis/aligned.py` |
|---|---|---|
| +3 dB octave at 1.6 kHz (dB) | 0.78 | 0.73 |
| +3 dB octave at 100 Hz | 0.35 | 0.32 |
| +6 dB octave at 8 kHz | 0.35 | 0.39 |
| 420 ms echo at -6 dB | 3.86 | 4.04 |
| 0.8 s reverb at -8 dB | 2.32 | 2.29 |
| 4:1 compression, half the time | 0.81 | 0.76 |
| soft clipping (tanh, ×4) | 2.52 | 2.08 |
| pink noise at -40 dB (against the render itself) | 0.26 | 0.14 |
| a 3 ms misalignment | 1.01 | 0.86 |

Against a copy of itself, a 3 ms misalignment costs about as much as an audible EQ
change. Against a real recording, already about 2–20 dB away, the distance is far
flatter (the 0.055 dB above). Correcting the catalogue's lags kept ALM's ranking
of the 44 presets at ρ ≥ 0.993 and changed the best preset on 1 of 30 parts.

## Scale

Measured with ALM, on active parts (1–10 s):

- the dry template: 6.74 (30 parts);
- the best of 44 SW50R factory presets, chosen in-sample: 3.84 (30 parts);
- a second microphone on the same amp, same take: 3.36 (23 parts). Another review
  measured 4.2 on 19 parts, which would put the best preset closer than the second
  microphone.

On the median part no factory preset was closer than the second microphone. Report
gains against that yardstick, not as raw percentages: "31% closer" moved the
template to roughly the distance between two microphones on the real amp.

About half of a part's headroom is specific to the microphone and the player. The
preset that wins against one microphone gains 28% there but 16% against the second
microphone on the same amp, and is the second microphone's own winner on 6 of 21
parts. A conclusion should also hold against the second microphone and through
other players' DIs.

## What it still cannot be trusted for

- **Distortion character.** With the spectrum matched, +6 dB of drive scores
  1.4–2× an octave EQ under ALM and 0.25–1× under long-term spectral measures.
  Which matches the ear is unmeasured.
- **Low frequencies.** A +3 dB octave at 100 Hz counts a third as much as one at
  1.6 kHz. A loudness model weights low frequencies about as mel bands do, and
  v3's third-octave bands about equally; which matches this listener is
  unmeasured.
- **Sub-additivity.** Far from the reference, a change that measures 0.5 dB by
  itself moved ALM by about 0.14. Small differences between two
  candidates that are both far from the recording are weak evidence.
- **Recordings with processing the plugin cannot make**: four amp tracks carry a
  printed 2.5 Hz tremolo, and six have dead-flat dynamics. Flag single-part
  verdicts on them.
- **Mostly silent crops.** 13 of 43 crops have the DI active under half the time;
  6 are refused on their 1–10 s windows, and where pauses are a large share of the
  rest the ranking leans on pauses, hiss and bleed.
- **Treble the recording lacks** (bands, above), which matters wherever an answer
  raised the top EQ bands.
- **400 Hz.** The weakest octave on the EQ test (73%).
- **Near ties.** In the lowest quarter of |log(dA/dB)| between two candidates
  (under about 0.09), 7–16% of pairs swap order under any one reasonable
  alternative design (bands, floor, tails); in the top quarter, under 1%
  (measured on the version before the band change).
- **Renders much darker than the recording**, where added noise and missing treble
  look alike (above).
- **The song.** On the one released master on disk (Fragments), the guitar as
  mixed differs from its amp track by 2.3 dB rms of EQ, panning and 1.6 dB less
  crest. Scored against the guitar as mixed instead of the amp track, ALM's
  ranking of the 44 presets held (ρ 0.98, same winner) and v3c's reversed
  (ρ -0.42). One song.

## What follows

- Re-check the conclusions that rested on v3: the kill tests' v3c arm, the
  library-vs-template result (`docs/library-arm-analysis-*.json`) and every "search
  beats its start" count.
- Stage 0b listening validation, scoring both band sets: about 100 trials
  balanced between the two answers, with catches, hidden repeats, second-microphone anchors and trials
  where the measures disagree; can't-tell answers modelled, never counted as half
  agreement.
- Data: one recorded lag per recording in the catalogue (Prodigal 4 first), crops
  re-cut where the DI plays, and bleed flags.
- Listening checks the review asked for: whether hiss matters to this listener
  (a render against itself with -40 dB of pink noise) and whether drive with a
  matched spectrum is heard as ALM or as the spectral measures weight it.
