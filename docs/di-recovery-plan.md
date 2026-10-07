# Song to preset by rebuilding the DI: the plan

Written 2026-10-06, before any of its models, listening trials or new renders exist.
Revised the same day after an independent review (findings at the end).

## The idea, and the measure

A song has no DI. The judge (`analysis/aligned.py`) chooses presets well but needs one.
So: a network rebuilds the guitar's DI from the recorded guitar (an isolated amp track,
or a stem separated from the song). Candidate presets are rendered through the rebuilt
DI, and the judge picks the one closest to the recording.

**The measure** (user's decision, 2026-10-06, `ROADMAP.md`) is the *average-guitar
measure*.
- The preset is rendered through the take's true DI, re-equalised to an average
  guitar's long-term balance. The average is computed from training folds only and
  frozen per fold in a file shared by the measure and the network's target.
- It is judged against the record on half B.
- The judge's own question (the true DI) is reported beside it.
- The measure cannot validate itself; only the listening check (L) can.

**What the measure already shows** (clean PR12, K1's 25 parts, 21-preset menu, band
median against template+R under recording / union bands):

| | score |
|---|---|
| the measure's own split-half oracle | −0.149 / −0.153 |
| best possible pick on half B | −0.168 / −0.153 |
| `avg+mild` (the measure's DI with mild artefacts; shares the oracle's pick on 20/25 parts) | −0.149 / −0.136 |
| **`flatref`**: the amp track re-equalised as the DI, no training | −0.098 / −0.086 |
| long-term spectrum match against other bands' average renders, no DI | −0.061 / −0.065 |
| **`flatstem`**: the separated stem, re-equalised, no training (18 parts) | −0.019 / −0.011 |
| random preset | +0.018 |
| leave-band-out constant preset | +0.056 |

So the training-free stand-in already gets about 60% of the oracle's gain on amp
tracks, and very little on stems. **A network earns its place only by beating
`flatref` and `flatstem` paired.** The stem path, the product's real input, is where
most of the gap is.

**Timing.** A DI rebuilt from the recording is aligned with it, and the judge then needs
`lag = −52`. This was measured: distances are smallest there, and the render leads by
about 52 samples. The test runs the true average-balanced DI through the rebuilt-DI path
and must reproduce the oracle's picks.

## Phase 0: cheap checks before any overnight run

**L. Does the ear agree with the measure?** A declared blind listening check of about 20
minutes, forced choice.
- **Trials:**
  - R is the record's guitar, half B of the amp-track crop.
  - A and B are two factory presets rendered through the average-guitar DI, the same
    aligned crops, loudness-matched as the judge normalises.
  - **24 disagreement trials:** the average-guitar measure separates A and B by at least
    0.15 in log distance, and the true-DI judge prefers the other.
  - **6 swap trials:** A and B through another player's DI (the `swap` renders), where
    the average-guitar measure and the swap-DI judge agree by at least 0.15. They check
    a user who isn't an average guitar.
  - **6 hidden repeats.**
  - At most two trials per part, spread over bands.
- **Pass:** at least 17 of 24 disagreement trials agree with the average-guitar measure
  (one-sided binomial p < 0.05), with at least 5 of 6 repeats consistent. Fewer
  consistent repeats voids the check.
- **If it fails:** the measure is wrong. Stop and rethink before Phase 2.

**D. How good must a rebuilt DI be?** Dose-response on K1's parts, about 550 renders per
level. The DI is the average-guitar DI mixed with the `flatref` stand-in at β = 0.25,
0.5 and 0.75, to model leftover amp processing. Choose and score as in the robustness
test. This gives the network's spec: how much leftover processing still keeps most of
the oracle's gain.

**P. Why does the stem path fail?**
- Score `flatstem` on single-guitar parts against multi-guitar parts.
- Compare the stem against the amp track within the same pipeline: same DI construction,
  the stem as the judged recording.
- Report how much of the loss is the separator's leftover other instruments.

**T. A one-hour run before the overnight one.** Train the network on one fold for an
hour, time the steps, and check it on held-out-band renders against `flatref`, scored
with the same choosing procedure. The overnight run starts only if it already beats
`flatref`'s choices there.

**S. Set 3, declared before any match touches it.**
- **Material:** 77 usable parts in 17 bands. Distortion defeats the repo's envelope test,
  so the waveform same-take test (GCC-PHAT, 20-s windows) is adopted for set 3, stated
  as a departure.
- **Exclusions:**
  - parts with fewer than 3 passing windows;
  - clipped DIs;
  - two-lag-cluster parts.
- **Split:** about a third of the bands held out by a seeded draw. Development bands get
  K3-style folds.

## Phase 1: the network

- **Folds.** K3's four band folds (seed 20261003) for sets 1–2, and seeded band folds for
  set 3's development bands. A part is only ever processed by a network that saw no DI
  from its band, so renders and averages are filtered by fold.
- **Pairs.**
  - **Input:** a render made from the *raw* DI, after a random pre-amp guitar EQ
    (±6 dB tilt, ±6 dB bells; pickup and guitar variation).
  - **Target:** that pre-amp-EQ'd DI re-equalised to the fold's frozen average balance.
  - **Sources:** the existing PR12 renders (no pre-amp EQ, fold-filtered) to start, then
    about 15k each of SW50R and AC20, and fresh PR12 with pre-amp EQ.
- **Input augmentation, target unchanged:**
  - a mic and room EQ after the amp;
  - bleed 12–30 dB down;
  - a noise floor;
  - in stage two, mixing into backings and separating with the shipped separator.
- **Network.** A waveform Demucs-style U-Net (3–8M parameters) with strided down- and
  up-sampling, so its receptive field reaches about 0.5 s (compression, decay).
  - Loss: 100·L1 plus a multi-resolution STFT loss, on 3-s crops.
  - Inference on overlapping 6-s windows.
  - Running: on MPS under `caffeinate`, with the steps timed in T.
- **Reported:** the rebuilt DI's long-term balance error per third octave, and its
  timing (cross-correlation peak at 0 ± 1 sample).

## Phase 2: the test on real recordings (decides)

- **Material:**
  - K1's 25 parts (clean PR12, 21-preset menu);
  - set 3's development parts with each amp's factory menu plus template+R, for SW50R,
    AC20 and PR12 separately.
- **Inputs:** (a) the amp track; (b) the separated stem.
- **Procedure.** Choose on half A through the rebuilt DI (lag −52). Score on half B under
  the average-guitar measure.
- **Comparators:**
  - template+R;
  - the leave-band-out constant;
  - `flatref` / `flatstem`;
  - the long-term spectrum match;
  - for PR12, the POC model;
  - the measure's oracle.
- **Pass, per material and input, under both band sets:**
  - the network's pick beats `flatref` (or `flatstem` for stems), paired: band median of
    log(network/stand-in) at most log 0.95, band sign-flip p < 0.1;
  - against template+R, band median at most log 0.9;
  - closer than template+R and the constant on more than half the parts.
- **Reported:** the judge's own question, part medians, and results by gain class.

## Phase 3: beyond the menu, and the product

- **Search.** Only after Phase 2 passes: a judge-scored search through the rebuilt DI,
  from the menu pick, with a positive control on renders.
- **Product.** Then `scripts/propose_preset.py`.
- **Fallback.** The long-term spectrum match needs no DI or network. It is a fallback
  for when the rebuilt DI is out of distribution.
- **Confirmation.** Set 3's held-out bands, declared once.

## The review's findings, and what changed

- **The 15% "equal to the oracle" result was not evidence.** `avg` *is* the oracle, and
  `avg+mild` shares its pick on 20/25 parts. The training-free stand-ins and a no-DI
  spectrum match now sit in the table as comparators, and the gates are paired against
  them.
- **Folds.** K3's folds, not "K1's", which has none. Training DIs and averages are
  filtered by fold, and set 3's development bands are folded too.
- **Render from raw DIs.** The pre-amp guitar EQ is now part of the plan, so the network
  learns to remove a guitar's balance.
- **The listening check** has more disagreement trials, forced choice, swap trials and a
  repeat rule.
- **The lag convention** is −52, measured.
- **The 0.5-s receptive field** and the MPS cautions are stated.
- **New cheap checks:** dose-response, the stem path, and a one-hour run.

## Phase 0 T, result (2026-10-07): inconclusive, so no overnight run

- **Run.** One hour of training on K3 fold 0 (4,600 steps). Validation loss fell from
  105 (the input used as the DI) to 57.
- **On 16 held-out-band renders**, band median against template+R under the
  average-guitar measure:
  - choosing through the rebuilt DI: −0.184 (mean −0.224);
  - through `flatref`: −0.125 (mean −0.135);
  - through the measure's own DI (the oracle): −0.355.
- **Paired, rebuilt against `flatref`:** 6 better, 5 worse, 5 ties, median 0.
- **Verdict.** The plan required the rebuilt DI to "already beat `flatref`'s choices
  there" before an overnight run. It doesn't clearly, so none is started.
- **Diagnostic** (reported, not a gate). How much of the gap to the oracle is the DI's
  *level* (unknowable from a song) rather than its shape? The check is re-run with the
  measure's DI at the assumed level, and with the rebuilt DI at the true level.

### The level diagnostic, and a declared second look (2026-10-07)

| choosing through… (16 clips, average-guitar measure, median vs template+R) | score |
|---|---|
| the measure's DI at its true level (the oracle) | −0.355 |
| the measure's DI at the assumed −22.9 LUFS | −0.310 |
| the rebuilt DI at the true level | −0.253 |
| the rebuilt DI at the assumed level | −0.184 |
| `flatref` | −0.125 |

- **Level costs little.** Unknowable from a song, it moves the oracle by only 0.045.
- **The rebuilt DI's shape is the bottleneck.** At the same assumed level, the ideal
  shape beats the rebuilt DI on 11 of 14 decided clips (median −0.04, and −0.127 in the
  medians). The network is what to improve.

**Second look, declared before it runs.**
- **Training:** resume fold 0's network from the one-hour checkpoint. Train 3 more hours
  on the same PR12 cache, with the learning rate decaying (cosine) from 3e-4 to 2e-5.
- **Check:** re-run the T check on the same 16 clips.
- **Rule:** the overnight multi-fold run, with the SW50R/AC20 pairs, goes ahead if the
  rebuilt DI beats `flatref` paired on at least 9 of the decided clips, with a median
  difference ≤ −0.03.
- **Reporting:** this is a second look on the same clips and is reported as such.

### Second look, result (2026-10-07 05:00): misses the declared rule by one clip

After 4 hours of training in all (validation loss 53.1, from 56.8 after one hour), on
the same 16 clips:

| | median | mean |
|---|---|---|
| rebuilt DI | −0.295 | −0.304 |
| `flatref` | −0.125 | −0.135 |
| oracle | −0.355 | −0.408 |

- **Paired, rebuilt against `flatref`:** 8 better, 4 worse, 4 ties, median −0.046.
- **Against the rule:**
  - "at least 9 better of the decided clips": 8 of 12, so **not met**;
  - "median ≤ −0.03": met.

**What happens next, decided before Phase 2 is run or read.**
- The gate existed to avoid spending overnight compute on a network that doesn't
  improve. The remaining folds' networks are trained overnight anyway, while the GPU
  is idle, with fold 0's exact recipe: 60 minutes at 3e-4, then 180 minutes of cosine
  decay to 2e-5, PR12 cache only.
- **Phase 2 is neither run nor read** until the user decides whether to proceed despite
  the near miss.
- Training spends compute only. It reads no result on the Phase 2 parts.

**User's decision (2026-10-07 morning).** Run Phase 2 as planned despite the near miss.
It runs once all four fold networks are trained, with the gates declared above.

## Phase 2 on set 3: specifics, declared 2026-10-07 before any set-3 match

- **One network for all of set 3.** It is trained on all three amps: the PR12 cache plus
  the SW50R and AC20 pair caches.
  - Its DIs come from set 2's development bands and Guitar-TECHS P1, leaving out K3
    fold 2. That is Eat The Feeder's fold, the only band shared with set 3.
  - So it has heard no DI from any set-3 band, development or held out.
  - Its average balance is K3 fold 2's frozen average.
  - Recipe: fold 0's, extended because the data is three times larger: 60 minutes at
    3e-4, then 300 minutes of cosine decay to 2e-5.
- **Menus.** For each development part, each amp's factory presets plus that amp's
  template+R, all with R, in three separate menus: PR12, SW50R and AC20.
  - Choosing and scoring are per amp, as in Phase 2 above.
  - Also reported: the best of the three amps' picks, by the judge through the rebuilt
    DI on half A.
- **Inputs:** the amp track, and htdemucs_6s stems of the instrumental mix (shifts=0, a
  30-s context, separated on CPU so the GPU stays free).
- **Weighting.** Gates are applied with parts weighted by band (`validation-set3.md`).
  Gain classes are descriptive only.
- **Held-out bands** are not touched until a later, separately declared confirmation.
