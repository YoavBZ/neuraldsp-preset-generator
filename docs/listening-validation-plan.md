# Stage 0b: does the distance hear what the listener hears?

Declared before any trial is built. `docs/measuring-closeness.md` makes
`analysis/aligned.py` the judge of closeness, on evidence that is either indirect
(known changes) or post hoc (16 trials it was tuned after). This short test asks
whether the judge picks the listener's answer when two renders differ clearly. It is
stage 0b of `docs/supervised-model-plan.md`, cut to about 20 minutes of listening at
the listener's request (from the ~2.5 h first planned), so it confirms or rejects the
judge on clear differences; it does not map fine thresholds.

## Question

Given the reference (a part's real amp track) and two renders of the same DI, A and
B, which is closer to the reference? How often does each distance pick the
listener's answer?

## Distances (frozen at the commit that adds this plan's trial list)

1. **The judge**, `aligned_distance` with default bands (primary), with one lag per
   part estimated by `estimate_lag` from the part's whole panel and recorded.
2. **ALM** as in `scripts/kill_tests.py` `alm` (catalogue lag less 52 samples).
3. Reported only: the judge with `bands="union"`, and v3c (`_v3c_compare`).

Each is computed on exactly the 4 s the listener hears.

## Material

- **Renders**: the SW50R panel (`scripts/render_preset_panel.py`; 44 factory presets,
  the template, and the template with time effects off), each through the part's own
  DI.
- **Parts**: development parts with a 4-s window where the DI plays in at least 90%
  of the frames; the window is the first such from 0.5 s, in 0.25-s steps.
  The two live-room parts whose amp track's top octave is mostly cymbals (Lost
  Alive, Until I Get Back) are left out: a guitar's tone is hard to hear through
  them, and the judge does not handle bleed (neither has a qualifying window in any
  case; Honey, from the same room, shows no measurable bleed in its crop and stays).

## Trials (30, in two sittings of 15)

- **Test pairs, 24.** Two candidates for one part, drawn with a fixed seed among
  pairs whose |log(dA/dB)| under the judge is above the median of all candidate
  pairs (clear differences only: below it, the measures' orders are unstable and
  answers are mostly "can't tell"). At least 10 are pairs where the judge and v3c
  pick different candidates. At most 2 per part, at least 8 bands, no candidate in
  more than 3 pairs.
- **Hidden references, 3.** One side is the reference itself; it must be picked.
- **Hidden repeats, 3.** Test pairs presented again, A and B assigned afresh, in the
  second sitting with their originals in the first.

## Presentation

- One R-A-B file per trial (`scripts/build_rab_audition.py`): Reference, A, B, twice,
  4-s segments, each matched to the same LUFS, mono. About 35 s per trial.
- Answer A, B, or can't tell.
- One playback level and the same headphones throughout.

## Blinding

- The committed trial list names the pairs, not their trial numbers. Trial numbers,
  sitting order and A/B assignments are drawn privately when the files are built and
  kept, with the builder's output, in a folder nothing reads until every answer is
  logged with `scripts/log_blind_verdict.py`.
- No distance's prediction is shown to the listener.

## Analysis

- **Reliability first.** If two or more hidden references are not picked, nothing is
  scored and the format is revisited. The repeats' consistency is reported.
- **Primary.** Among test pairs where the listener picked A or B, the share where the
  judge picked the same one. One-sided exact binomial against 0.5. A distance is
  **validated** at 70% or more agreement with its p below its Holm threshold: the
  judge and ALM are tested together, the smaller p against 0.025 and the larger
  against 0.05. With 22 decided pairs that is 17 of 22 at the first step and 16 of 22
  at the second.
- **Can't tell** is never counted as half agreement; its rate is reported.
- **Reported only**: the union band set and v3c on the same pairs; on pairs where the
  judge and v3c disagree, which the listener sided with (sign test); and the earlier
  16 trials beside this, never pooled.
- **Power** (22 decided pairs, the stricter step): a distance right 85% of the time
  validates with probability 0.90, one right 80% of the time 0.73; at the second step
  0.96 and 0.87.

## Decision

- The judge validates: it stays the judge, and the kill tests' verdicts stand as
  declared (`docs/kill-test-k3-plan.md`, "Under the judge").
- Only ALM validates: the kill tests are read under ALM alone, as declared there.
- Neither validates: model work stops (supervised-model plan, stage 0), and how
  closeness is measured is revisited before any decision rests on it.
