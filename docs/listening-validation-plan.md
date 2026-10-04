# Stage 0b: does the judge order clear differences the way the listener does?

**Result: validated** (17 of 22 decided pairs, p 0.0085), for clear differences
between clean-to-crunch PR12 renders: `docs/listening-validation-results.md`.

Declared before any trial was built, and amended once before any answer (below).
`docs/measuring-closeness.md` makes
`analysis/aligned.py` the judge of closeness, on evidence that is either indirect
(known changes) or post hoc (16 trials it was tuned after). This short test asks
whether the judge picks the listener's answer when two renders differ clearly. It is
stage 0b of `docs/supervised-model-plan.md`, cut to about 20 minutes of listening at
the listener's request (from the ~2.5 h first planned).

**Amended on 2026-10-04, before any answer was given.** The first build drew its
options from the SW50R panel. A few trials into the first sitting, the listener found
both options too distorted to compare with the amp track (most of the SW50R's factory
presets are high-gain), stopped, and returned no answers. What changed:

- The options come from the PR12 panel, less its high-gain presets (below). AC20, the
  other cleaner Morgan amp, is not used: an audition of an AC20 render must come from a fresh plugin
  process per render, and that many restarts wear out the plugin's licence service.
- The judge's lag is each part's recorded lag, so the four parts whose lag is
  ambiguous are left out of the pool.
- No trial offers the amp's shipped template (time effects on, against a dry amp
  track) or a high-gain preset: one with a drive pedal on or the PR12's volume (its
  gain) above 0.75, read from the preset's settings, never from a distance. That
  leaves 21 of the 34 factory presets and the template with time effects off.
- The clear cut is the median over the new pool's pairs of offered candidates, recorded
  beside the trial list's sha256.
- The trial list records the sha256 of every option's audio, and the builder refuses
  anything else.

The first draw (its sha256 begins 1b057b79) is withdrawn unscored. Its trial list and
keys stay private. Its pairs cannot recur, since every option is now another amp's
render. It does not use up the one rerun allowed below.

**Practice first, then the draw.** Before anything is drawn, the listener hears one
practice file, built like a trial from a part outside the pool (Signs ElecGtr3, whose
lag is ambiguous): the template with time effects off against one offered factory
preset drawn at random. If the listener cannot compare them, the material is amended
again before any draw; the practice's part, options and the listener's verdict are
recorded with the result. **No further withdrawal** once the draw is built: a trial
that cannot be compared is answered "?".

**Practice, heard on 2026-10-04 before the draw:** Signs ElecGtr3, the template with
time effects off against "Lush Clean Wet". The listener could compare them, chose one,
and noted that the amp track itself is driven and one option too clean.

## What it can and cannot show

- A pass means that aligned log-mel measures order **clear** differences the way this
  listener does. It does not separate the judge from ALM or from the judge's union
  band set: on clear pairs they mostly predict the same answer (all 24 pairs of the
  withdrawn first draw; the new draw's count is reported). Nor does it reach near-ties, where the union and default band sets differ,
  or the kill tests' per-part K3 gains (6–17%, most below the clear cut, all on SW50R
  renders outside the tested material; corrected after scoring, when the cut had become
  0.150, from "below the clear cut"). So it does not settle K3's union reading.
- The options are PR12 renders with no drive pedal and a volume of 0.75 or less (clean to
  crunch); the kill tests used the SW50R.
  Whether the listener and the judge agree as often on high-gain options, or on other
  amps, is not tested.
- The pairs are chosen by the judge's own confidence. A pair the judge calls a
  near-tie that sounds clearly different, its documented blind spot (excess treble the
  recording lacks), is never sampled; and cruder measures agree with the judge on many
  clear pairs too (an unaligned long-term spectrum on 20 of the withdrawn draw's 24). A
  pass is evidence for aligned distances on clear differences, weaker evidence for the
  judge in particular.

## Distances

1. **The judge**: `aligned_distance` with default bands, at the part's recorded lag
   (`docs/validation-lags.json`) less the plugin's 52 samples. The only distance
   tested.
2. **Reported**: ALM as in `scripts/kill_tests.py` (catalogue lag less 52 samples,
   which is 9.5–14 ms off on a few parts), the judge with `bands="union"`, and v3c.

Each is computed on exactly the 4 s the listener hears.

## Material

- **Renders**: the PR12 panel (`scripts/render_preset_panel.py`; 34 factory presets
  with time effects off, the template with them off, and the template as shipped),
  each through the part's own DI. Trials offer only the 21 factory presets that are
  not high-gain and the template with time effects off; the pool's distances cover
  all 36.
- **Parts**: development parts with an unambiguous recorded lag (four are left out)
  and a 4-s window where the DI plays in at least 90% of the frames; the window is the first such from 0.5 s, in 0.25-s steps. The two
  live-room parts whose amp track's top octave is mostly cymbals (Lost Alive, Until I
  Get Back) are left out (neither has a qualifying window in any case; Honey, from the
  same room, shows no measurable bleed in its crop and stays).

## Trials (30, in two sittings of 15)

- **Test pairs, 24.** Two candidates for one part, among pairs whose |log(dA/dB)|
  under the judge is above the median over all pairs of offered candidates of all
  parts (the clear cut). Drawn with
  a seed from the system's randomness: first one pair per band, then pairs where the
  judge and v3c pick different candidates until there are 10, then any; at most 2 per
  part, at least 8 bands, no candidate in more than 3 pairs.
- **Hidden references, 3.** One side is the reference itself; it must be picked.
- **Hidden repeats, 3.** Test pairs presented again, A and B drawn afresh, in the
  second sitting with their originals in the first.

## Presentation

- One R-A-B file per trial (`scripts/build_rab_audition.py`): Reference, A, B, twice,
  4-s segments, each matched to the same LUFS, mono. About 35 s per trial.
- On the test pairs, the option the judge calls closer is A on exactly 12, chosen at
  random, so a lean towards A or B cannot add to or take from agreement.
- Answer A, B, or ? (can't tell) on the sheet in the listener's folder.
- One playback level and the same headphones throughout.

## Blinding

- The trial list (pairs and every distance's prediction) and its seed stay in a
  private folder until every answer is in; a listener who saw the pairs could tell the
  options apart. Nobody opens it, the analyst included, before every answer is in.
  This plan records its sha256, the clear cut and counts that name no pair:
  `4a0c547bf2a53c7ee77cf289ddbcea70378620b947e649a35813b671304b963a`; clear cut
  |log ratio| > 0.150 (about 16%). The draw: 22 candidates offered (13 left out as
  high-gain), 28 parts, 3,234 clear pairs, 24 test pairs over 11 bands, 10 of them
  where the judge and v3c disagree.
- Trial numbers, sittings and A/B assignments are drawn when the files are built and
  written, with the builder's output (which prints each file's seed), only to the
  private folder. The listener's folder holds the trial files and the answer sheet.
- Both scripts refuse a trial list whose sha256 differs from the one above.
- The answer sheet's sha256 (of its bytes) is committed and pushed, in
  `docs/listening-validation-answers.sha256`, before scoring; the scorer records it
  before any key is read and refuses a different sheet later
  (`scripts/score_listening_validation.py`).

## Analysis

- **Reliability first.** If two or more hidden references are not picked, the test is
  void and nothing is scored. The repeats' consistency is reported, and decides
  whether a low count can be read as "rejected" (below); a repeat with "?" on
  either side counts as not answered the same way.
- **The judge**, on test pairs the listener decided (can't-tell is never counted as
  half):
  - **validated** at 70% or more agreement with a one-sided exact binomial p < 0.05
    against 0.5 (16 of 22 decided pairs);
  - **rejected** when the one-sided 95% upper bound on its agreement is under 70%
    (11 or fewer of 22) and at least 2 of the 3 repeats were answered the same way
    (otherwise a low count may be a listener not hearing the differences, which the
    hidden references, identical audio, cannot catch);
  - **inconclusive** otherwise, or with fewer than 12 decided pairs.
- **The mix.** At least 10 of the 24 pairs (42%) are ones where the judge and v3c
  disagree. The trial list records the pool's share of such clear pairs, and the
  agreement reweighted to it is reported beside the outcome, which refers to this
  mix.
- **Power** (22 decided pairs): P(validated) is 0.96 for a judge right 85% of the
  time, 0.87 at 80%, 0.70 at 75%, 0.49 at 70%, 0.30 at 65% and 0.16 at 60%. A
  listener guessing at chance is "rejected" with probability 0.58 before the repeat
  condition and 0.29 with it (a guesser answers at least 2 of 3 repeats the same way
  half the time).
- **Reported only**: ALM, the union band set and v3c on the same pairs; on the pairs
  where the judge and v3c disagree, which the listener sided with (sign test); on how
  many test pairs each of them predicts the judge's option; the can't-tell rate; and
  the earlier 16 trials beside this, never pooled.

## Decision

"Validated" covers clear differences between clean-to-crunch PR12 renders only: pairs
whose |log(dA/dB)| under the judge exceeds the clear cut. (In the withdrawn SW50R pool
that was 0.213, about 19%; in this pool it is 0.150, about 16%, just above the 15% the
model POC's development gates use.) POC results below the cut, on high-gain material, or on other amps rest on an
unvalidated range.

- **Validated**: the judge stays the judge for clear differences on clean-to-crunch
  material. Under
  `docs/kill-test-k3-plan.md`'s clause for "validates the judge but not ALM" (ALM is
  not tested here), the kill tests are recomputed with the judge's conditions only,
  both band sets: K3's union reading still fails, so the verdict stays "not passed"
  (`docs/kill-test-results.md`). Whether to proceed anyway remains the user's call;
  condition 1 there is met only for clear differences on clean-to-crunch material,
  and the kill tests' SW50R high-gain renders rest on an unvalidated range.
- **Rejected**: the judge is not validated; the kill-test verdicts are void and model
  work stops (supervised-model plan, stage 0); how closeness is measured is revisited
  before any decision rests on it.
- **Inconclusive** or **void**: the test is run once more, with freshly drawn pairs
  from the same panel and offered candidates (and, if void, a check of the playback set-up first), never
  pooled with this run.
  That second outcome is final: anything but "validated" counts as not validated, the
  kill-test verdicts are void, and model work stops. The rerun's trial-list sha256
  replaces this one in the plan (the scripts read exactly one), and the first run's
  list stays private until the second is scored, since pairs can recur.

Under the kill tests' condition 1 (no POC result read until a measure is
validated), a validated judge lets POC results be read, but any POC gain below the
clear cut, or on high-gain material or another amp, is reported as resting on an
unvalidated range and cannot by itself open a further gate.
