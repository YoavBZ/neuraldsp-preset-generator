# The rebuild gap: where C′ loses ranking from a perfect stem, and a loss judged on ranking. Plan (2026-10-17)

Declared 2026-10-17, before any analysis, training or render of this study. Development data only
(step 3's 24 parts, the frozen Σ `ee91f710947dbb5c`, the PR12 training cache). Code:
`learn/rebuild_gap.py` (main `.venv`: analyses, probes, renders, scores, report) and
`learn/rebuild_gap_train.py` (the torch interpreter: the proxy amp bank, the phase check, the
fine-tune, the rebuilds); tests `tests/test_rebuild_gap.py`, `tests/test_rebuild_gap_train.py`.
Outputs under `~/ndsp-presets/learn/rebuild-gap/`.

The user's rules apply:
- **No pass/fail bars.** Every result is an effect size with a 90% band-clustered interval (t,
  bands − 1 df), the leave-one-band-out range and the bands above and below 0. Any improvement is
  built on; undecided is not failed.
- **No fixed render limit.** Each render stage has a declared, evidence-based stopping rule, an
  expected count, and reports what it used.

**Status:** reviewed 2026-10-17 by an independent agent: approved with 10 required changes, all
made (the sections below are revised; [amendment 1](#amendment-1-2026-10-17-review-before-any-analysis-training-or-render)
lists them and governs where anything differs); re-reviewed the same day: **approved**, no required
changes. The only work done before the review's changes
were in: the probe build and its checks (zero renders, no scores read) and the C′ phase check on
PR12 crops (item 10, zero renders).

## Why

- **Local ranking fidelity** (cross-half local Spearman over Σ's 3,456 settings, band-weighted,
  [results](local-objective-results.md)):

  | DI / reference | Fidelity |
  |---|---|
  | True (measure) DI / amp track: the ceiling | 0.864 |
  | **C′ rebuilt from the amp track / amp track (1b, a perfect stem)** | **0.541** |
  | C′ rebuilt from Mega-53 / Mega-53 (1c) | 0.398 |
  | C′ rebuilt from the htdemucs stem / that stem (today) | 0.289 |

- **More than half the gap sits in the rebuild itself:** with a perfect stem the rebuild still
  loses 0.323 [0.132, 0.514] (ceiling − 1b, re-derived from the stored scores; the review
  reproduced it).
- **What hasn't explained it:**
  - the ladder: C′'s error is fine structure (< 10 ms), not tilt or slow dynamics
    ([ladder](rank-margin-ladder-results.md));
  - a fine-structure retrain fixed gap fill and treble but didn't steer better
    ([experiment 4](di-fine-structure-results.md));
  - the separator-robust fine-tune's envelope gain didn't carry to ranking (1d), so envelope and
    coherence metrics have not predicted ranking. **Rebuild changes must be judged on rendered
    ranking.**
- **Measured for this plan (zero renders), C′'s rebuild of the amp track against the true DI**
  (aligned within ±100 samples of each part's `judge_lag` by the analytic correlation in 80 Hz–2
  kHz):
  - the waveform match is poor: |c| 0.51–0.88, coherence in 80 Hz–2 kHz 0.32–0.78 (1–3 kHz: median
    0.39), waveform SNR median 1.1 dB;
  - **the rebuild carries a per-part constant phase rotation** of the whole 80 Hz–2 kHz band,
    spread round the circle (14 of 24 parts at 90° or more). Removing it raises the SNR to a median
    of 3.3 dB. A constant rotation keeps the spectrum but changes the waveform's shape, and an
    asymmetric amp responds to shape once it drives; nobody has tested whether it moves ranking;
  - the rebuild's long-term spectrum is 3.3 dB (median LSD) from the true DI's.
  - (An earlier draft read the rotation as a polarity flip on 15 parts; that came from GCC-PHAT's
    lag, which lands near 0 instead of near `judge_lag` on 13 parts. The review caught it.)

## The questions

1. **Where** does the rebuild lose ranking information from a perfect stem: which knobs and
   settings are mis-ranked, and which properties of the rebuilt DI cause it?
2. **Can a training change judged on ranking** close part of the gap?

## Stage A: the stored data (zero renders, CPU)

### A1. Which knobs are mis-ranked

From the stored scores of experiments 1 and 1b on all of Σ. For the matched cell (1b), today's
objective and the truth's own cross-half order (the ceiling):
- **Knob families.** Input gain; amp gain staging (PR12 Volume; SW50R Volume, Level, Input Mode;
  AC20 Volume, Power); amp tone (Treble, Bass, Mid, Bright, Treble Boost, Cut, Bass/Treble); cab
  and mic (mic types, positions, distances, right mic level, right cab on/off).
- **Per knob, on S's ±1/8 neighbourhood** (each pair differs in one knob only): the 3-way
  agreement of `local_objective.three_way`, objective on one half against the truth on the other
  (cross-half), with each knob's chance, and the truth's own cross-half agreement beside it.
  Aggregated per family; the gap per family is truth − matched.
- **On all of Σ:** pairwise cross-half concordance by dominant family (the family holding more
  than half the pair's squared unit-scale move; otherwise "mixed").
- **By drive:** concordance on pairs whose two settings both sit above S's input gain against both
  below; per class (clean, crunch: 5 parts, descriptive).

### A2. Every stored rebuild scored against the amp track

The renders of 1c (`cprime_mega53`) and 1d (`csep_stem`, `csep_mega53`) are rescored from their
stored FLACs against `reference.wav`, at the rebuild's native lag (−52), own mask with the record
fallback (1b's matched configuration). First an identity check: rescoring one cell of 1b's own
renders must reproduce its stored matched scores within 1e-9. With experiment 1's C′/reference and
1b, that gives **five rebuilds of different sources and networks, all against the amp track**, on
all 72 cells. About 10.4k FLACs at 2 judge calls each: about 0.5 CPU-hours, one worker.

### A3. Which DI properties track rendered ranking

Per (rebuild, part), against the measure DI (aligned as in stage R, the rebuild's own rotation
kept): waveform SNR, before and after removing the rotation; |c|; |rotation|; LSD (80 Hz–8 kHz);
coherence in 80 Hz–1 kHz, 1–3 kHz and 3–8 kHz; crest error at 1, 5 and 10 ms; quiet-frame level
error; and stage B0's proxy fidelity. Reported, all descriptive:
- **within part:** across the five rebuilds of A2, the Spearman of each metric with the rendered
  fidelity, per part, band-weighted with its interval (n = 5 per part, and the five differ in
  source as well as network, so this is noisy and confounded);
- **across parts:** each metric against 1b's per-part gap to the ceiling (24 parts);
- **A4, the rotation split:** 1b's fidelity on the parts rotated 90° or more against the rest, and
  by class.

## Stage B0: a differentiable proxy amp bank, and is it any use? (zero renders, CPU)

Morgan is not differentiable. A learned Morgan surrogate needs its own fidelity study (hours of
training on the 18.8k PR12 POC renders, whose sensitivity to DI fine structure is the open
question), so stage T uses a **hand-built differentiable proxy bank**, declared now and not tuned on
the 24 parts. **Stage T is a bet on this proxy, and rendered ranking (stage TR) judges it; B0 does
not gate T.**
- **The chain** (torch, CPU, zero-phase FFT filters): input normalised to RMS 0.1 (as each DI is
  levelled before rendering); gain g; a pre-emphasis shelf at 700 Hz with a fixed 60 Hz high-pass
  and 8 kHz low-pass; an asymmetric tanh stage with bias; a 6 kHz interstage low-pass; a second
  tanh stage; a three-band tone stack (low shelf 120 Hz, bell 600 Hz, high shelf 2.5 kHz); a cab
  low-pass and an 80 Hz high-pass.
- **Seven unit-scale knobs** θ ∈ [0, 1]⁷: g from −6 to +30 dB (clean to heavy, split 0.6/0.4
  across the stages), pre-shelf ±6 dB, bias 0–0.3, the three tone gains ±9 dB, cab corner 3–7 kHz.
- **The distance** D is judge-like, in the judge's order: 64-band log-mel (50 Hz–16 kHz,
  2,048-point frames, hop 512); the level difference taken out first; both sides floored 40 dB
  under the reference's loudest band per frame; what is left of the mean removed; frames within
  40 dB of the reference's loudest; mean |ΔdB| (a smooth absolute value).
- **A proxy local set** mirrors Σ: a target θ* drawn uniformly; a start S displaced from θ* by
  ±0.15–0.35 on three random knobs (clipped); candidates S and S ± 1/8 on each knob (15). The
  reference is P(true DI, θ*). Proxy fidelity is the Spearman between D(P(x, θ_k), reference) for
  the DI x under test and for the true DI, averaged over draws.

**B0 (zero renders):** proxy fidelity per part of A2's five rebuilds and of the built probes (32
draws per part, the same draws for every variant of a part), on the 10-s crops, against the measure
DI. Reported as an A3 metric, and after stage R against the probes' rendered fidelity (14 more
variants per part).

## Stage R: the oracle probes (renders, queued behind the Mega-53 song test)

**Design.** Each probe replaces one component of 1b's rebuild with the true DI's and renders on a
subset of Σ. Every probe is a DI on the **measure DI's timeline**, levelled to −22.9 LUFS and
scored exactly as the truth is scored: against `reference.wav`, at the part's `judge_lag`, with
**the measure DI as the activity mask** (declared), so that the only thing differing from the truth
is the DI the plugin plays. The own-mask score with the record fallback is a diagnostic.
Substituting everything gives the truth itself (its stored renders); substituting nothing gives the
rebuild.

**Alignment (zero renders, logged and checked per part).** r = 1b's stored rebuild of the amp
track (`rebuilt-ref/<part>.npy`), t = the measure DI. Both band-passed to 80 Hz–2 kHz
(4th-order Butterworth, zero-phase) and made analytic; the lag is the one within ±100 samples of the
part's `judge_lag` that maximises the magnitude of their normalised complex correlation, and the
rotation φ is that correlation's angle (r ≈ rotate(t, φ) after the shift, with rotate(x, φ) =
Re{(x + iH(x)) e^{iφ}}, H the Hilbert transform). r̃ = rotate(r on t's timeline, −φ).
- **Checks (each part, before any render):** |c| ≥ 0.3 and coherence in 80 Hz–2 kHz ≥ 0.3 at
  the chosen lag, and the lag not at the window's edge. Measured: |c| 0.51–0.88, coherence
  0.32–0.78, the lag −21 to +17 samples from `judge_lag`. All 24 pass.
- **Mixes can't cancel:** every blend of t and r̃ in frequency is done per STFT bin in
  log-magnitude and phase (|T|^m |R̃|^(1−m), the phase interpolated), not by adding waveforms.
- STFT: Hann 1,024, hop 256, `scipy.signal.stft/istft` (round trip of t within 1e-9, checked).

| Probe | The DI | Paired against | What it tells |
|---|---|---|---|
| `reb` | r on t's timeline, its own rotation | (the anchor) | the rebuild through this pipeline; also against 1b's stored scores (plumbing) |
| `rot` | r̃ (the rotation removed) | `reb` | **does the rebuild's phase rotation cost ranking?** |
| `t_rot` | rotate(t, φ): the true DI carrying the rebuild's rotation | the truth | **do Morgan and the judge care about a constant rotation at all?** Free of every other rebuild error |
| `mag` | the true STFT magnitude with r̃'s phase (8 Griffin–Lim iterations from r̃'s phase; the realised magnitude error is logged: median 1.5 dB) | `rot` | the true magnitude (21-ms resolution) |
| `phase` | r̃'s magnitude with t's phase | `rot` | the true phase (fine structure, transients) |
| `low` | t below 500 Hz, r̃ above (⅓-octave raised-cosine crossovers) | `rot` | the true low band |
| `mid` | t in 500–2,000 Hz | `rot` | the true mid band |
| `high` | t above 2,000 Hz | `rot` | the true treble |
| `onset` | t in attack windows (onsets from the true DI's spectral flux; −2 to +15 ms, 2-ms fades), r̃ elsewhere | `rot` | **true transients** (coverage 10–26% of samples, median 24%; logged per part) |
| `sustain` | t outside those windows | `rot` | the rest; with `onset`, attacks against the rest at their coverage |
| `half` | halfway between t and r̃ in log-magnitude and phase per bin, made consistent (8 iterations) | `rot` | half the error: dose response |
| `noise` | t + N, N random-phase with \|R̃ − T\|'s STFT magnitude, scaled per band (16 log-spaced, 50 Hz–16 kHz) so that its band-level error to t equals r̃'s (reached within 3e-8 dB) | `rot` | the same spectral error, unstructured: **does the error's structure or its size cost ranking?** |
| `dep_eq` | r EQ'd to the average spectrum by the measure DI's own rule (`eq_to(r, avg − own shape)`) | `reb` | deployable: the measure DI's normalisation applied to the rebuild (LSD 3.3 → 0.8 dB) |
| `dep_rot` | r rotated by the angle a render chooses (below) | `reb` | deployable: the rotation chosen without the true DI |

- **`dep_rot`'s rule (deployable, declared).** Per probe cell, S renders through r rotated by
  k · 45° (k = 0…7) after one warm-up: 9 renders. The rotation whose S render the judge scores
  closest to the amp track on the search half (half A; reference.wav, −52, own mask with the
  fallback) is kept. 216 renders. Where it keeps k = 0, `dep_rot` is `reb` exactly and reuses its
  renders and scores (none rendered twice). Its agreement with the oracle rotation (within 45°) is
  reported.
- **Every probe is built and checked before any render (zero renders):** each within 0.05 LU of
  its part's measure DI (all set by `to_lufs`); band masks summing to 1 within 1e-9; `reb` equal to
  r shifted, exactly; the alignment checks; `noise`'s calibration within 0.5 dB per band; and **no
  mix comb-filters or cancels**: for `low`, `mid`, `high`, `onset`, `sustain` and `half`, in every
  third-octave band from 80 Hz to 8 kHz (the crossover regions included), the mix's long-term level
  within 3 dB of the range spanned by t's and r̃'s. A failure stops the render stage
  (`probes/check.json`). **Built 2026-10-17 before the review's changes were final: all 24 parts
  pass** (the first build, with waveform mixing, failed this check on 4 parts' `half` and one part's
  `mid`, which is why mixing moved to log-magnitude and phase).
- Realised metrics per probe (SNR, LSD, coherence bands, crest errors) are logged in
  `probes/log.json`.

**The probe cells.** One amp per part, 8 parts per amp: the 24 parts sorted, the amps in a list of
8 × (PR12, SW50R, AC20) shuffled by `random.Random("rebuild-gap|cells")`. 24 cells, all 14 bands,
all 48 of Σ's settings in each. On the stored scores this subset's half-width for a paired
contrast is 0.13–0.18; all 72 cells give 0.11–0.19 (the review reproduced both).

**Renders, stage R1 (fixed set):**
- 14 probes × 24 cells × (48 + a warm-up) = **16,464** at most (fewer where `dep_rot` keeps k = 0);
- `dep_rot`'s choice: **216**; the comparator: per cell, the measure DI at S (warm-up and S)
  against experiment 1's stored true d at S, within 0.005 (log) on both halves: **48**;
- **at most 16,728, about 3.4 h** at 3 processes (5k/h), then about 0.3 h of scoring.

**Guards (as the local-objective experiments):** `knob_ceiling.Renderer` with `isolate=True`; each
cell's S against its warm-up within 0.005 (log) on the declared configuration; FLAC against float
at S; the comparator; a shared stop file (`rebuild-gap/STOP.json`; every shard checks it and
`local_objective`'s); the disk guard (31 GB, all shards' remaining renders counted at the start);
the swap guard; at most 3 render processes machine-wide, counting `local_objective`'s patterns,
`learn.arm_a_mega53 search` and this module's. **This module's render commands are added to
`local_objective.RENDERS`** (which `arm_a_mega53.RENDERS` inherits), so other jobs' caps count
them. `OMP_NUM_THREADS=1`, `setopt no_bg_nice`, `nohup`, `caffeinate`.

**Queued behind the Mega-53 song test.** Only lines after the latest `start pid` line of its
`logs/run.log` count (the log is appended). Stage R starts when one of the runner's terminal lines
has appeared (`all done`, `stage F not started`, `STAGE F: a shard failed`, `REPORT F FAILED`,
`DECIDE-X FAILED`) and no `learn.arm_a_mega53` process or `arm_a_mega53_run.zsh` remains.
`STAGE D: a shard failed`, `REPORT D FAILED` and `REBUILD X FAILED` are not terminal. If the
runner's processes are gone with no terminal line, an `ALERT.json` is written and nothing starts.

**Stopping rule, R1 → R2 (evidence-based).** R1 is a fixed set: every probe needs all 14 bands
for its paired interval. The other 48 cells are the other two amps of the same parts and bands, so
they narrow a band-clustered interval only a little. The rule therefore uses the narrowing the
stored data show: `narrowing_ratio` is the median, over six stored paired contrasts of experiments
1–1d, of (all-72-cell half-width) / (R1-cell half-width). A probe extends to the other 48 cells
(with its anchors) **only if its estimate against its anchor is positive, its R1 interval contains
0, and the interval narrowed by that ratio would exclude 0** at the same estimate. A family
contrast (`mag` − `phase`, the bands, `onset` − `sustain`, `noise` − `rot`, `half` − `rot`) that
meets the same rule in either direction extends both members. 2,352 renders per probe; expected
0–2 probes (0–5k renders, up to 1 h); at most all 14 (32.9k). R2's contrasts are reported on all 72
cells, R1's beside them.

## Stage T: a training change judged on ranking (GPU)

**The change: a proxy-ranking loss.** Each fold's final C′ is fine-tuned on the PR12 pair cache
with C′'s own loss plus two terms through the proxy bank:
- **ranking:** per crop, 8 of the 15 proxy candidates; d_r,k = D(P(rebuild, θ_k), P(true DI, θ*))
  and d_t,k the same through the true DI (no gradient); the term is 1 − Pearson(d_r, d_t) over the
  8. It asks the rebuild to rank the proxy settings as the true DI does;
- **output match:** mean_k D(P(rebuild, θ_k), P(true DI, θ_k)): the rebuild should sound like the
  true DI through the proxy at each setting.
- **Weights,** fixed before training by the share rule experiment 4 used: on 50 training batches
  of C′ at step 0 (their own generator), each new term's weighted mean is a quarter of C′'s loss.
- The proxy terms use a 1.5-s sub-crop of 6 of the batch's 12 crops and run on the **CPU**
  (`torch.stft`'s backward is wrong on MPS above 65,536 samples); the network runs on MPS. Measured
  for this plan: about 0.32 s per step for the proxy terms at 2 threads.

**The arms (per fold, seed 0):**
- **`rank`:** as above; batch 12; 200-step warm-up to 1e-4, cosine to 2e-5 over 4,000 steps;
  validation every 250 steps.
- **`ctl`:** the same run with both weights at 0 (C′'s loss only), the same data stream (the proxy
  draws use their own generator) and the same schedule, **stopped and saved at `rank`'s best step**
  (a matched-step control). It separates the loss from "more fine-tuning" (1d couldn't).
- **Selection and stopping (zero renders):** every 250 steps, proxy fidelity on 96 fixed crops of
  two **held-out training-fold bands** (cprime-sep's per fold, for comparability: fold 0 Eat The
  Feeder, Zeno; fold 1 Adam Buckley, Starnes And Shah; fold 2 Starnes And Shah, Swatkins; fold 3
  Swatkins, Zeno), each crop with 2 seeded draws of 9 candidates. Those bands leave training in
  both arms (rows and bleed). `rank` keeps its best checkpoint (a gain of at least 0.005) and stops
  1,500 steps after it (at least 1,500 steps, at most 4,000). Step 0 (C′ itself) is logged. If
  `rank`'s best is step 0 on a fold, that fold's `rank` and `ctl` are C′ and are reported so.
- **MPS guards:** the hand clip and non-finite-step skip and recovery of `direc.fit` (torch's
  `clip_grad_norm_` gives NaN on MPS); every STFT on the CPU.
- **Leaks:** the training pool is the PR12 cache's rows outside fold f and outside the two
  validation bands; `config.json` lists the cache and fold so that 1b's leak assertion
  (`di_fine_structure.assert_no_leak` over `train_pool_bands`) runs per part at rebuild time; no
  Guitar-TECHS P3 row (asserted); the 24 parts are never trained on or selected on.
- **The domain-shift question (review item 10, zero renders):** `phasecheck` measures C′'s own
  rotation, |c| and coherence on 96 PR12 validation crops per fold against their true DIs. If C′ is
  phase-correct on PR12 renders, the rotation on real amp tracks comes from the real recording
  chain, which a PR12-only fine-tune can't learn to remove; stage T is read with that in mind.
  **Run 2026-10-17:** on PR12 crops C′'s rotation is modest (median |φ| 20–36° per fold; 15–40% of
  crops beyond 45°), with |c| about 0.8 and 80 Hz–2 kHz coherence 0.43–0.61. On the real amp
  tracks 14 of 24 parts sit at 90° or more. So the large rotations are mostly a real-chain domain
  shift that stage T cannot address; the coherence deficit (similar on both) is C′'s own.
- **Hours:** about 1.1 s per step for C′'s loss with validation, about 1.4 s with the proxy terms.
  Per fold `rank` runs 1,500–4,000 steps (0.6–1.6 h) and `ctl` up to `rank`'s best step (0–2,500
  steps, 0–0.8 h). **About 4–6 h of MPS expected for the 4 folds, at most about 10 h.**
- **Queued:** T is invoked as `-m learn.rebuild_gap_train train`, which other jobs' training gates
  see. It starts only when the Mega-53 runner's current run shows `lane A done:` (lane A's
  separations refuse to run beside any training job; the coordinator's gate), with no other
  training job and at least 25% free memory. If lane A fails instead (`LANE A FAILED` or
  `DECIDE-X FAILED`), an `ALERT.json` is written and T waits for the coordinator's word.

**B1: stage T on the proxy, zero renders.** Proxy fidelity of `rank`, `ctl` and C′ on the 24
parts' amp-track rebuilds (as B0), and the validation curves. Descriptive.

## Stage TR: judging stage T on rendered ranking (renders, after stage T and R1)

- **The rebuilds:** each arm's network rebuilds every part's `reference.wav` exactly as 1b did
  (`local_objective.rebuild_from`: re-EQ'd by fold 2's average − fold f's, −22.9 LUFS, 2a's checks:
  within 3 samples of C′'s stem rebuild and at −22.9 ± 0.05 LUFS; experiment 4's leak assertion).
- **Renders, TR1 (fixed):** both arms on the 24 probe cells: 2 × 24 × 49 = **2,352**, plus the
  comparator (C′'s 1b rebuild at S against 1b's stored score at S, warm-up and S): 48. About 0.5 h.
- **Scored as 1b's matched cell:** `reference.wav`, −52, own mask with the record fallback; paired
  cell by cell with 1b's stored C′ scores.
- **Primary (two, both reported):** `rank` − C′ (does the change help?) and `rank` − `ctl` (is it
  the loss?). Also `ctl` − C′, per fold (descriptive: 3–10 parts each), per class and amp.
- **Stopping, TR1 → TR2:** by R2's rule on `rank` − C′ (positive, undecided, and decided once
  narrowed by the stored ratio), both arms extend to the other 48 cells: **4,704** renders, about
  1 h. Otherwise TR stops at TR1. The product cell (the arms rebuilding the htdemucs stem, scored
  against it) is not declared here; it follows a positive TR reading with the user's yes.

## Measures and reading (declared now)

- **The measure** is the cross-half local Spearman per cell (its own objective on one half against
  the true d on the other, averaged over halves), with reliable-pair accuracy as co-primary;
  cells → parts (over amps) → bands; band-weighted mean with the 90% band-clustered t interval
  (bands − 1 df), the part-weighted interval, the leave-one-band-out range, bands +/−, per amp and
  class (crunch descriptive). The truth's own cross-half Spearman on the same cells is beside every
  figure.
- **Each probe:** its paired contrast with its anchor; for `rot`'s probes and the deployable ones,
  its **share of the anchor's gap** (probe − anchor) / (truth − anchor) on the same cells,
  band-weighted ratio with Fieller's interval (`local_objective_1c.share`); the realised DI metrics
  beside it. `t_rot` is read against the truth (no share).
- **Families** (paired): `mag` − `phase`; `low`, `mid`, `high` against each other; `onset` −
  `sustain`; `noise` − `rot` (structure against size); `half` − `rot` (dose); `rot` − `reb` and
  `dep_rot` − `reb` (rotation, oracle and deployable); `t_rot` − truth; `dep_eq` − `reb`.
- **Where, per probe:** A1's knob-family 3-way breakdown on each probe's renders and against its
  anchor, so a probe that recovers ranking can be traced to the knobs it fixes.
- **What would follow (estimates, not bars):**
  - a probe with a positive estimate is a lead for the rebuild's training target (`mag` or `phase`,
    a band, transients) and is built on;
  - `t_rot` below the truth, or `rot` above `reb`: the rotation matters; then the rebuild needs a
    rotation fix (a training augmentation over rotations, a rotation-invariant objective, or
    `dep_rot`'s render rule); `dep_rot` positive: a 9-render product fix to test on a fresh draw.
    `t_rot` at the truth: the rotation is harmless and the rest of the gap lies elsewhere;
  - `noise` close to the truth while `rot` isn't: the error's structure, not its spectral size,
    costs ranking, so a spectral loss alone won't close the gap and a ranking-aware loss is the
    route; `noise` as low as `rot`: the spectral error itself costs;
  - `half`: whether ranking recovers gradually with the error (losses pay off steadily) or only
    near zero error;
  - `dep_eq` positive: a free fix (the measure DI's own normalisation) for the product rebuild;
  - stage T: a positive `rank` − C′ is built on (a learned surrogate, more seeds, the product
    cell); positive against C′ but not against `ctl` points to the extra fine-tuning.
- **Multiplicity:** 14 probes and two stage-T primaries share the parts and Σ. A single interval
  excluding 0 is read with that in mind; the families, not single probes, carry the reading.

## Machine order, hours and disk

| Stage | Renders | Hours | Starts |
|---|---|---|---|
| Probes built and checked | 0 | minutes (done) | now |
| T's phase check | 0 | minutes (CPU) | now |
| A1, A3 | 0 | minutes (CPU) | after the review |
| A2 rescoring | 0 | about 0.5 CPU-h, 1 worker | after the review |
| B0 | 0 | about 1–1.2 h (torch, 2 threads; measured 8.3 s per draw for 18 variants at 1 thread) | after A2 |
| T (8 fine-tunes) | 0 | about 4–6 h MPS (at most about 10) | after Mega-53's lane A |
| B1 | 0 | minutes | after T |
| R1 | at most 16,728 | about 3.4 h + 0.3 h scoring | after the Mega-53 runner ends |
| R2 | 0–32,928 (expected 0–5k) | 0–7 h (expected 0–1 h) | after R1's report, by its rule |
| TR1 | 2,400 | about 0.5 h | after T and R1 |
| TR2 | 0 or 4,704 | about 1 h | by its rule |

- **Renders expected:** about 19–24k; at most about 57k (every extension firing).
- **CPU before the Mega-53 test ends:** A2, A3 and B0 run one after another (one worker, then 2
  threads), so this study adds at most 2 threads beside lane A's 4-thread separation; no render.
- **Disk:** 50 GB free (the review's reading). Probes 1.1 GB (built), checkpoints about 1 GB;
  16-bit FLAC at 0.48–0.7 MB: R1 8–11.7 GB, TR1 1.2–1.7 GB; the Mega-53 test needs about 1.5 GB.
  That leaves about 33 GB after R1 and TR1, above the 31 GB guard. **R2 and TR2 may reach the
  guard**: rendering then stops (resumable) and the user is asked what to delete; this plan deletes
  nothing.
- **One chained runner** (`learn/rebuild_gap_run.zsh`) runs A, B0 now; waits for lane A and B0
  and runs T; waits for the Mega-53 runner and runs the rotation choice and R1 (3 shards), scoring, the R1
  report and R2 by its rule; then the arms' rebuilds, B1, TR1 when T has ended, TR2 by its rule,
  and the reports.

## Seeds

- Probe cells: `random.Random("rebuild-gap|cells")`.
- `noise`'s phase: `numpy.random.default_rng(<sha256 of "rebuild-gap|noise|<part>">)`.
- B0 draws: `rebuild-gap|b0|<part>` (shared by every variant of a part); the phase check's crops:
  `rebuild-gap|phasecheck|<fold>`; stage T's validation draws: `rebuild-gap|val|<fold>`; training:
  seed 0 for the data stream (as C′), 1 for the proxy draws, 2 and 3 for the weight calibration.
- Nothing else is random: cells sorted, shards `i::3`, fixed render order.

## Ledger

The entry `rebuild-gap` in [dev-test-ledger.json](dev-test-ledger.json) is entered with this plan,
before any analysis, training or render. It is a further unblinded development use of step 3's 24
parts and Σ, read after experiments 1–1d; every figure is a development reading. Stage T trains
only on the PR12 cache's training-fold rows and selects on held-out training-fold bands, never on
the 24 parts. Any fix that is to ship is scored on a fresh draw of parts outside the 24 first.

## Limits

- 24 parts, 14 bands, 19 clean; crunch (5 parts) descriptive. One amp per part in R1.
- The probes are oracle diagnostics on the measure DI's timeline and level. Their components
  (21-ms magnitude, band edges, 17-ms attack windows, the rotation measured in 80 Hz–2 kHz) are
  choices, and a modified STFT is not consistent (the realised metrics are logged).
- The proxy bank is a crude stand-in for Morgan. B0 and the probes measure how far it tracks
  rendered ranking; a learned surrogate is the follow-up if the loss helps and the proxy doesn't
  track.
- One seed per fold in stage T; PR12 renders only (the SW50R and AC20 caches were deleted).
- The truth is the judge, not listening.

## Amendment 1 (2026-10-17, review, before any analysis, training or render)

The independent review approved the plan with 10 required changes. All are made in the sections
above, in code and in tests (`tests/test_rebuild_gap.py`, `tests/test_rebuild_gap_train.py`):

1. **Alignment.** GCC-PHAT replaced by the judge_lag-anchored analytic correlation in 80 Hz–2 kHz,
   with the |c| and coherence checks and the lag's distance from `judge_lag` logged. The "Why"
   bullet is rewritten: the polarity figures were artefacts of GCC's lag.
2. **Rotation, not polarity.** `pol` became `rot` (the rebuild's constant phase rotation removed);
   `dep_pol` became `dep_rot` (8 rotations chosen by the S render, 216 renders); `t_rot` added (the
   true DI with the rebuild's rotation, against the truth, 1,176 renders). `dep_rot` reuses `reb`'s
   renders where it keeps no rotation.
3. **Mix checks.** Declared and run: no third-octave of any mix below or above the range of t and
   r̃ by more than 3 dB. They caught real cancellation in the first build, so mixing in frequency
   moved to log-magnitude and phase, and `half` is now the halfway point in log-magnitude and
   phase (made consistent), not the waveform average.
4. **`noise`** is calibrated per band to r̃'s band-level error, not its waveform energy.
5. **Extensions** are decided by the narrowing the stored data show (all cells against the R1
   cells), so they fire only when more cells could plausibly change the reading; family contrasts
   count. Expected R2 renders fell from 7–14k to 0–5k.
6. **Stage T's hours** corrected (4–6 h expected, at most about 10); `ctl` stops at `rank`'s best
   step.
7. **Wait conditions** list the runner's terminal lines exactly, read only the current run, and
   alert instead of starting if the runner vanishes. (The review asked to release T on
   `DECIDE-X FAILED` too; the coordinator's gate, given while this amendment was written, is
   stricter: T starts only on `lane A done:`, and a lane-A failure waits for the coordinator.)
8. **Visibility:** T is `train`; this module's render commands are in `local_objective.RENDERS`
   (a one-line change to that file).
9. **Disk:** 50 GB free; R1 and TR1 fit above the guard; R2 and TR2 may stop at it, and the user
   is asked (nothing is deleted by the plan).
10. **The domain-shift check** (`phasecheck`, zero renders) is added and was run: C′ is roughly
    phase-correct on PR12 crops (median |φ| 20–36°) against 90°+ on 14 of 24 real amp tracks, so
    the rotation is mostly a real-chain shift that stage T can't learn (stage T above).

**The re-review** (approve, no required changes) left three notes, taken: lane T also waits for
B0 to end, so the study never adds more than 2 threads beside the Mega-53 test; if lane A fails,
T (and so TR) waits for the coordinator indefinitely, by design (`ALERT.json`); and the
`local_objective.RENDERS` line counts this study's renders only for jobs launched from a checkout
that has it (the running Mega-53 test has its own copy, which doesn't matter since R waits for it),
so it needs merging before other jobs rely on it.

Also taken from the review's suggestions: A3 is descriptive and its confounds stated; `mag` gets 8
consistency iterations; R2 counts family contrasts; B0 does not gate T, said plainly; the CPU
sequencing beside lane A is stated. Other changes made while implementing, before any render:
- the attack windows narrowed from −5/+30 ms to −2/+15 ms: at 30 ms they covered a median 46% of
  the samples (dense parts), so `onset` was not a transient probe; now 10–26%;
- B0 uses the same draws for every variant of a part (paired), not a draw per variant;
- A2 first checks that rescoring 1b's renders reproduces its stored scores (1e-9);
- the proxy distance removes the level in the judge's order (before flooring), found by a test;
- B0 computes the true DI's proxy distances once per draw for all of a part's variants (identical
  results, about half the compute; B0's hours above are measured, not the first draft's 0.3 h).
