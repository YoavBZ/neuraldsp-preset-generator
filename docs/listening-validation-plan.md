# Stage 0b: does the judge order clear differences the way the listener does?

Declared before any trial is built. `docs/measuring-closeness.md` makes
`analysis/aligned.py` the judge of closeness, on evidence that is either indirect
(known changes) or post hoc (16 trials it was tuned after). This short test asks
whether the judge picks the listener's answer when two renders differ clearly. It is
stage 0b of `docs/supervised-model-plan.md`, cut to about 20 minutes of listening at
the listener's request (from the ~2.5 h first planned).

## What it can and cannot show

- A pass means that aligned log-mel measures order **clear** differences the way this
  listener does. It does not separate the judge from ALM or from the judge's union
  band set: on clear pairs they predict the same answer (all 24 of the first draw's
  pairs). Nor does it reach near-ties, where the union and default band sets differ,
  or the size of the kill tests' per-part K3 gains (6–17%, below the "clear" cut). So
  it does not settle K3's union reading.
- The pairs are chosen by the judge's own confidence. A pair the judge calls a
  near-tie that sounds clearly different, its documented blind spot (excess treble the
  recording lacks), is never sampled; and cruder measures agree with the judge on many
  clear pairs too (an unaligned long-term spectrum on 20 of the first draw's 24). A
  pass is evidence for aligned distances on clear differences, weaker evidence for the
  judge in particular.

## Distances

1. **The judge**: `aligned_distance` with default bands, one lag per part estimated
   by `estimate_lag` from the part's whole panel. The only distance tested.
2. **Reported**: ALM as in `scripts/kill_tests.py` (catalogue lag less 52 samples,
   which is 9.5–14 ms off on a few parts), the judge with `bands="union"`, and v3c.

Each is computed on exactly the 4 s the listener hears.

## Material

- **Renders**: the SW50R panel (`scripts/render_preset_panel.py`; 44 factory presets,
  the template, and the template with time effects off), each through the part's own
  DI.
- **Parts**: development parts with a 4-s window where the DI plays in at least 90%
  of the frames; the window is the first such from 0.5 s, in 0.25-s steps. The two
  live-room parts whose amp track's top octave is mostly cymbals (Lost Alive, Until I
  Get Back) are left out (neither has a qualifying window in any case; Honey, from the
  same room, shows no measurable bleed in its crop and stays).

## Trials (30, in two sittings of 15)

- **Test pairs, 24.** Two candidates for one part, among pairs whose |log(dA/dB)|
  under the judge is above the median of all candidate pairs of all parts. Drawn with
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
  options apart. This plan records only its sha256:
  `1b057b79917c0127c89f8fd430de9f7612807922b0efea3a5ba8dc32ac0317c5`.
- Trial numbers, sittings and A/B assignments are drawn when the files are built and
  written, with the builder's output (which prints each file's seed), only to the
  private folder. The listener's folder holds the trial files and the answer sheet.
- Both scripts refuse a trial list whose sha256 differs from the one above.
- The answer sheet's sha256 is committed and pushed before scoring, and the scorer
  records it before any key is read and refuses a different sheet later
  (`scripts/score_listening_validation.py`).

## Analysis

- **Reliability first.** If two or more hidden references are not picked, the test is
  void and nothing is scored. The repeats' consistency is reported.
- **The judge**, on test pairs the listener decided (can't-tell is never counted as
  half):
  - **validated** at 70% or more agreement with a one-sided exact binomial p < 0.05
    against 0.5 (16 of 22 decided pairs);
  - **rejected** when the one-sided 95% upper bound on its agreement is under 70%
    (11 or fewer of 22) and at least 2 of the 3 repeats were answered the same way
    (otherwise a low count may be a listener not hearing the differences, which the
    hidden references, identical audio, cannot catch);
  - **inconclusive** otherwise, or with fewer than 12 decided pairs.
- **The mix.** 10 of the 24 pairs (42%) are ones where the judge and v3c disagree,
  against 17% of clear pairs in the pool. The outcome refers to this mix; the
  agreement reweighted to the pool's split is reported beside it.
- **Power** (22 decided pairs): P(validated) is 0.96 for a judge right 85% of the
  time, 0.87 at 80%, 0.70 at 75%, 0.49 at 70%, 0.30 at 65% and 0.16 at 60%. A
  listener guessing at chance is "rejected" (before the repeat condition) with
  probability 0.58.
- **Reported only**: ALM, the union band set and v3c on the same pairs; on the pairs
  where the judge and v3c disagree, which the listener sided with (sign test); the
  can't-tell rate; and the earlier 16 trials beside this, never pooled.

## Decision

"Validated" covers clear differences only: pairs whose |log(dA/dB)| under the judge
exceeds 0.213 (about 19%; the median test pair is about 35%). That is above the 15%
the model POC's development gates use, so POC results at that scale would rest on an
unvalidated range.

- **Validated**: the judge stays the judge for clear differences. Under
  `docs/kill-test-k3-plan.md`'s clause for "validates the judge but not ALM" (ALM is
  not tested here), the kill tests are recomputed with the judge's conditions only,
  both band sets: K3's union reading still fails, so the verdict stays "not passed"
  (`docs/kill-test-results.md`). Whether to proceed anyway remains the user's call;
  condition 1 there is met only for clear differences.
- **Rejected**: the judge is not validated; the kill-test verdicts are void and model
  work stops (supervised-model plan, stage 0); how closeness is measured is revisited
  before any decision rests on it.
- **Inconclusive** or **void**: the test is run once more, with freshly drawn pairs
  (and, if void, a check of the playback set-up first), never pooled with this run.
  That second outcome is final: anything but "validated" counts as not validated, the
  kill-test verdicts are void, and model work stops.
