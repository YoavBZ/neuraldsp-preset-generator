# Listening check L: does the ear agree with the average-guitar measure?

Declared 2026-10-06, before any answer. This is Phase 0 L of
[di-recovery-plan.md](di-recovery-plan.md); background in
[di-robustness-results.md](di-robustness-results.md). Built, run and scored by
`learn/build_avg_listening.py`. Nothing is rendered: every option is an existing render.

## Material

- **Parts:** K1's 25 parts (clean PR12), with K1's lags.
- **Options:** the 21 clean PR12 factory presets. template+R is not offered.
- **Half B only:** 5.5–10 s of each 10-s crop, with recording bands.
- **R:** the amp track (`reference.wav`).

## The measures

- **The average-guitar measure:** the precomputed half-B distances of the `avg`
  renders (`avg-yardstick-distances.json`, `recording|B`).
- **The true-DI judge:** `aligned_distance` on half B, comparing the panel render
  with R, through the true DI.
- **The swap-DI judge:** the same, with the `swap` render and the swap DI.
- Every measure uses the part's lag and `render_latency=52`. Both judges are computed
  once and cached in `~/ndsp-presets/listening/avg-measure/work/distances.json`.

## Trials (36, in two sittings of 18)

- **24 disagreement trials.** A and B are two factory presets, both rendered through
  the average-guitar DI.
  - The average-guitar measure separates them: |log d_avg(A) − log d_avg(B)| ≥ 0.15.
  - The true-DI judge prefers the other one.
- **6 swap trials.** The same two presets rendered through another player's DI (the
  `swap` renders and DI). The average-guitar measure and the swap-DI judge prefer the
  same one, each by at least 0.15.
- **6 hidden repeats.** Six disagreement trials, drawn by the seed, are played again
  with A and B swapped. Each original is in sitting 1 and its repeat in sitting 2.
- **The choice:**
  - At most 2 trials per part, counting both kinds, and no pair is used twice.
  - Disagreement trials are chosen first, then swap trials.
  - Bands take turns (round-robin), and each band takes its best fitting pair.
  - "Best" means a guitar-exposed part first, then the largest average-guitar margin.
    Ties are broken by seed 20261006.
  - Exposure is the share of half B where the true DI plays (≥ 0.9). This turned out
    to be 1.0 on all 25 parts, so in practice the margin decides. R is an isolated amp
    track, so no vocals or band cover it.
  - If fewer than 24 disagreement or 6 swap trials qualify, the builder stops; the bar
    is not lowered.
- **The draw.** Trial order, sittings and A/B come from the system's randomness and
  are written only to the private key.
  - The measure's option is A on exactly 12 of the 24 disagreement trials and 3 of
    the 6 swap trials.
  - No part plays twice in a row.

## Audio

- **Excerpts.** R is half B of the amp track. A and B are aligned to it exactly as the
  judge aligns them: recording[t] matches render[t − lag].
- **Levels.**
  - Every clip gets a 10-ms raised-cosine fade at each edge.
  - Each clip is then given one static gain to the same EBU R128 integrated loudness:
    −20 LUFS, lowered by one shared amount for the whole test if any clip would peak
    above −1 dBTP.
  - Mono, 24-bit FLAC.
- **Each trial** is one file: Reference, A, B, then again (about 30 s). R, A and B are
  also saved alone for replay.

## What was built (counts only; no pair is named)

- **Qualifying disagreement pairs:** 343 of 5,775 factory pairs, on 16 parts in 6
  bands. At 2 per part, 29 could be chosen.
- **Qualifying swap pairs:** 1,767, on all 25 parts in 9 bands.
- **The 24 disagreement trials:**
  - 11 parts with 2 trials and 2 parts with 1, over 6 bands. Dom McLennon, Eggy and
    the Travelling Band have 6 each; Zeno, Eat The Feeder and Atlantis Bound have 2.
  - Average-guitar margins run from 0.158 to 0.562.
  - The true-DI judge's opposite margin is small on most of them (median about 0.04,
    largest 0.367). So these trials mostly ask "the measure is clear and the judge is
    nearly tied: does the ear follow the measure?"
- **The 6 swap trials:** 6 parts in 6 bands, average-guitar margins 0.374–0.578.
- **Length:** 18 minutes of audio; with answering, about 20–25 minutes.
- **Alignment:** K1's lags are used as the judge uses them. On a few parts another lag
  estimate differs by tens of samples (under 2 ms, one part 6 ms). Clips play one
  after another, never mixed, so such offsets cannot be heard.

## Blinding and hashes

- **The listener's folder** (`~/ndsp-presets/listening/avg-measure/listen/`) holds
  only numbered trial files and `ANSWERS.md`.
- **The key** (`private/trials.json`) holds the pairs, distances, order and A/B.
  - Nobody opens it before every answer is in.
  - Its sha256 is recorded here, and the scorer refuses any other key:
    `329e0ed86af12339fd8937dac524c9b8b8b0e49ee469ef52da6381eec7b80483`
- **The answer sheet.** When it is complete, its sha256 is committed in
  `docs/avg-measure-listening-answers.sha256` before scoring.
  - The scorer records the sheet's hash before it reads the key.
  - It refuses a different sheet afterwards.

## Taking it

    .venv/bin/python -m learn.build_avg_listening take

- Answer `a` or `b`; this is forced choice.
- To listen again: Enter replays the trial; `r`, `pa` and `pb` play R, A or B alone.
- `q` stops, and a later run resumes where it stopped.
- Use the same headphones and level throughout, with a break between the sittings.

## Pass rule

- **Void:** fewer than 5 of the 6 repeats are answered consistently (the same preset
  chosen both times). Nothing else is read.
- **Passed:** otherwise, with at least 17 of the 24 disagreement trials agreeing with
  the average-guitar measure (one-sided binomial p 0.032).
- **Failed:** otherwise. The measure is wrong; stop and rethink before Phase 2.
- **Reported, not part of the rule:**
  - agreement on the swap trials, out of 6;
  - agreement with the true-DI judge on the disagreement trials (24 minus the above);
  - results by sitting, and how often A was chosen.

    .venv/bin/python -m learn.build_avg_listening score
