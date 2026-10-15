# Rank margin and the degradation ladder: plan (DI-recovery experiment 2)

Declared 2026-10-15, before any compute. **Review:** reviewed 2026-10-15
(`tmp/rank-margin-ladder-plan-review.md`, local): approved with changes, all folded in. It is
experiment 2 of the DI-recovery report
([`research/di-recovery-2026-10.md`](research/di-recovery-2026-10.md),
"The ladder that tells the project what to fix" and "Rank margin, not coherence"). Development
data only, on step 3's known-target control cells. No held-out data is read (not Guitar-TECHS
P3, not sets 5 or 6). No training.

## Why

Arm A's known-target control failed
([song-settings-plan.md](song-settings-plan.md), "Recorded outcome (2026-10-15)"). With the
measure DI the search closed ≥ 50% of the gap on 9 of 9 informative cells. Through C′'s rebuild it
did so on 3 of 9. Through C′, the search objective ranks the target T worse than the start S on 7
of 12 cells. The audit blames dynamics: crest factor 3–5 dB low on 10 of 12 cells, and frame
envelope correlation 0.09–0.84 ([audit](audits/song-settings-control-2026-10-15/README.md),
`diag4.out`). That cause is likely, not tested. Coherence, the current rebuild measure, has never
predicted picks.

This plan answers three questions:
1. **Does the rank margin predict search success?** If so, it becomes the cheap gate for every
   new rebuild (2 renders per cell instead of a 3.6k-render control). Here it can only become a
   provisional gate (step A).
2. **Is it dynamics?** Does crest loss alone, rather than tilt, flip the ranking?
3. **Can a render-free proxy stand in for the margin?**

## The rank margin

- **Definition:** for a cell, a DI variant v and a window w,
  m_w(v) = log d_w(S; v) − log d_w(T; v).
  - d_w(x; v) is the judge distance (`analysis/aligned.py` `aligned_distance`, flat, bands
    "recording", `render_latency` 52) between the cell's fake recording (`<cell>-fake.npy`) and
    settings x rendered through v, over window w.
  - **Windows:** A (1.0–5.5 s) is the search half the stored control searches used. B (5.5–10 s)
    is the held half. **Full** is 1.0–10 s.
  - **Primary:** step A uses m_A (what the stored searches saw). Step B fits nothing, so its
    primary is m_full; m_A and m_B are robustness readings.
  - m > 0 means "T ranks above S through v".
- **The mask** (the judge's DI argument sets only which frames are playing and scored):
  - **Step A and experiment 3's gate:** v itself, as a recovered DI would be (realistic). On an
    activity refusal, the fake recording stands in (`rebuilt_judge.rebuilt_distance`'s fallback).
  - **D1 and D2 (the causal ladder):** the measure DI, so that only the render changes, not the
    scored frames.
  - Every render is scored both ways (zero extra renders). The other reading is reported.
- **A refusal** (no distance after the fallback) leaves that cell × variant undefined. It is
  dropped and counted.
- **The 0.25-s fade-in** of isolated renders doesn't matter: every window starts at 1.0 s.
- **The lag is fixed per variant** (the judging-lag fix from the recorded outcome):

| Variant | Judge lag | Why |
|---|---|---|
| Measure DI and every rung built on it | 0 | The fake was rendered from the raw DI; the measure DI is a zero-phase EQ of it. Every rung is zero-phase or sample-aligned. |
| C′ and every network rebuild (1-h checkpoint, seeds, C, R, L) | 0 | Rebuilds of the fake align to the input DI, not to the recording (`diag1.out`: rebuild against raw DI, GCC lag −1 to +3 samples). Not −52, which `rebuilt_distance` assumes for rebuilds of real recordings. |
| Rows derived from C′ (oracle EQ, transplants) | 0 | Zero-phase or sample-wise steps on C′. |
| Step A only: the stored C′ search | −52 and 0 | The search optimised the −52 objective; 0 is the corrected definition. Both are read. |

  **A lag check in code:** every variant's GCC lag against the raw DI must be within ±3 samples,
  or that variant stops and is reported. For the phase-scramble rung, GCC is band-limited to
  below 1 kHz; its alignment by construction is also covered by a unit test.
- **Informative cells:** amendment 2's rule, d_S − d_T ≥ 0.1 on half B through the measure DI,
  from the stored `result.json` files. That gives 9 of 12. The 3 uninformative cells are Today's
  The Day PR12 and SW50R, and Blind Spots PR12. They are reported, not scored, in step A, D1 and
  D2. They count for D3.

**Why the measure DI is the base.** The fake was rendered from the raw DI, so the raw DI would
reproduce it exactly: d(T) ≈ 0, which is degenerate. The measure DI is the project's "true DI"
(equalised to the average guitar), and the search through it succeeds. Each rung degrades it.

## Step A: does m predict the stored searches? (zero renders)

- **Data:** the 12 control cells × 2 stored searches (measure-DI run, C′ run), 150 renders each,
  searched on half A, scored on half B.
  - m_A through the measure DI comes from each `result.json` (S and target, lag 0, both halves).
  - m_A through C′ comes from `diag3.json` (`reb/S`, `reb/T`, lags −52 and 0, both halves).
  - The activity fallback fired on none of the 12 stored searches (`fallback` 0), so diag3's
    distances, judged without it, are what the search saw. No renders.
- **The predictor is m_A,** the half the search saw. **The outcome is the gap closed on half B
  ≥ 50%.** So predictor and outcome don't share data. m_B is reported beside it.
- **Reported:** the 2×2 table over the 18 informative searches (9 cells × 2 runs), m_A > 0 or ≤ 0
  against gap closed ≥ 50% or < 50%, overall and per run; the Spearman ρ of m_A against the gap
  closed **within each run** (not pooled); the 3 uninformative cells' m_A and shortfall.
- **Provisional adoption** (declared, entered in the ledger). All must hold, at lag 0 **and** at
  lag −52:
  1. agreement (m_A > 0 with ≥ 50%, or m_A ≤ 0 with < 50%) on **≥ 15 of 18**;
  2. **within the C′ run:** m_A > 0 on **≥ 2 of its 3** successes, **and** m_A ≤ 0 on **≥ 4 of its
     6** failures. This beats the run-identity baseline: "m ≤ 0 on every C′ search" alone would
     score 15 of 18.
  - If the two lags disagree, the reading is undecided.
  - **Undecided (13–14 of 18, or row 2 fails):** m is a screen only. It can stop a rebuild (m ≤ 0
    on most informative cells means no control re-run). It cannot pass one.
  - **Not adopted (≤ 12 of 18):** experiment 3 goes straight to the full control re-run (about
    3.6k renders per arm). Step B still runs, read as "what flips the ranking", not "what breaks
    the search".
- **Why only provisional.** On the measure-DI run, the informative rule nearly builds in
  agreement. The audit already saw C′'s lag −52 margins (the 7-of-12 inversion), so the C′ half is
  not blind. Nothing in step B measures search success.
- **The confirming test is pre-registered now.** Before each of experiment 3's control re-runs,
  m_A (mask v, lag 0) is computed for the corrected rebuild on every cell, and the prediction
  "this search closes ≥ 50% of the gap iff m_A > 0" is written to the ledger before the search
  runs. m becomes a final gate only if those predictions agree on **at least two-thirds** of the
  informative searches, pooled over experiment 3's re-runs. No prospective searches are run in
  this plan.

## Step B: the degradation ladder (about 0.9k renders)

Per cell, S and T are rendered through each variant (`knob_ceiling.Renderer`, `isolate=True`,
one warm-up render of S first): 3 renders per variant per cell. Every variant is 10 s, mono,
float64 and finite. Seed for every draw: **20261017**. "Measure DI" is
`knob_ceiling.measure_di(part)`. Envelopes e_w are centred moving RMS over w ms (zero-phase).
Gain ratios are floored at −60 dB below each signal's RMS and clipped to ±30 dB.

**Re-EQ for dynamics rungs.** Compression, envelope smear, envelope swaps and transplants also move
the long-term spectrum (the review measured up to ±2.4 dB per band at crest −3). So each of those
rungs ends with `eq_to` back to its **source's** mean-removed `smoothed_spectrum` (the measure DI,
or C′ for C′-based rows), then `to_lufs` to −22.9 LUFS. Every other rung ends with `to_lufs`. The
achieved band shifts (80–200 Hz, 200–1000 Hz, 2–8 kHz), crest change and envelope correlation are
recorded for every rung.

**Rungs on the measure DI (18 variants, all 12 cells):**

| # | Variant | Exact construction |
|---|---|---|
| 1 | base | The measure DI. A repeat check: S and T within 0.005 (log) of `result.json`, else stop. |
| 2–4 | crest −1.5, −3, −5 dB | A static compressor on e₁₀ in dB: g = −(1 − 1/R)·max(0, e₁₀ − θ), applied sample-wise, R = 4, then the re-EQ and LUFS. θ is bisected on [e_max − 60, e_max] **on the final signal**, so the crest (20·log10 of the 99.9th-percentile \|x\| over the RMS, whole 10 s, as `diag4.py`) falls by the rung's amount ± 0.2 dB. If R = 4 can't reach it, R = 10. If that fails too, the rung is unreachable on that cell; −5 is then rendered at R = 10's lowest θ, and the achieved value is recorded. **Expected:** −1.5, −3 and −5 are unreachable on Passing Ships (crest 8.9 dB; at most 0.85 dB reachable), so its cells drop from the crest rungs and are not rendered there. −5 reaches 3.9–4.9 dB on most parts. |
| 5 | placebo smear | `di_robustness`'s "mild" smear: the audio convolved with a normalised 10-ms exponential, 50/50 dry. It is about a 16-Hz low-pass on half the signal (envelope correlation 0.997–1.000 with the base), so it is a **placebo**. Expected inversions: 0. |
| 6–7 | envelope smear 10, 30 ms | x · s_τ(e₁)/e₁, with e₁ the 1-ms RMS envelope and s_τ a causal one-pole on that envelope (τ = 10 or 30 ms); then the re-EQ and LUFS. Attacks are slowed; the fine structure is kept. |
| 8–9 | treble shelf −2, −4 dB | Zero-phase gain G / (1 + (2000/f)^4) dB (half the gain at 2 kHz, about the full gain by 4 kHz), with `direc_check.eq_to` on `SPEC_N` bins. |
| 10–12 | bell +1, +3, +5 dB | Zero-phase gain G from 200 to 1000 Hz, raised-cosine skirts half an octave wide each side in log frequency, 0 elsewhere; `eq_to`. These and rows 8–9 bracket C′'s measured tilt (`diag2.out`: +1 to +6 dB at 200–1000 Hz, −1 to −6 dB at 2–8 kHz). |
| 13 | phase scramble > 1 kHz | STFT (1024-sample Hann, hop 256, `scipy.signal`). Phases of bins ≥ 1 kHz replaced by uniform random phases (`numpy.random.default_rng(20261017 + cell index)`). Inverse STFT, then `eq_to` back to the measure DI's long-term spectrum, so only fine structure changes. |
| 14–15 | bleed −20, −10 dB | The bleed part's measure DI added at −20 or −10 dB RMS relative to the cell's. **The bleed part:** `random.Random(20261017)` picks a band among knob ceiling's in-scope bands outside the 6 control bands (Honey excluded), then a part in it. The draw gives **Magician's Nephew, `cambridge-get-out-of-bed-elecgtr1`** (crunch, a set-3 development part among knob ceiling's 24; not P3, not sets 5 or 6). The same part for every cell. |
| 16 | C′-envelope swap | The measure DI × e₁₀(C′) / e₁₀(measure DI), then the re-EQ and LUFS. It puts **C′'s 10-ms envelope, its squash and its shape (timing errors included),** on the true DI. |
| 17 | C′ spectrum | `eq_to` the measure DI by (C′'s mean-removed `smoothed_spectrum` − the measure DI's), then LUFS. C′'s tilt and nothing else; the complement of row 21. **D1's deciding tilt reading.** |
| 18 | C′ crest | The row 2–4 compressor, bisected so the crest equals C′'s crest on that cell (`diag4.out`). Where C′'s crest is not lower than the measure DI's (Passing Ships: 11 against 8.9 dB) or unreachable, the rung is dropped on that cell. |

**Real rebuilds and derived rows (all 12 cells, 6 variants):**

| # | Variant | Source |
|---|---|---|
| 19 | C′ | The stored `<cell>-rebuilt.npy` (the cell's fold, re-equalised to fold 2). A repeat check against `diag3.json` lag 0, within 0.005 (diag3 rounds to 3 decimals, about 3e-4 log). |
| 20 | C′ 1-h checkpoint | `models-cprime-1h-f{f}/fold{f}.pt` (fold 2: `models-cprime-1h/fold2.pt`). Same training pool as C′, so leak-free; a weaker real rebuild. Rebuilt on the CPU as `song_settings.control_rebuild`. |
| 21 | C′ + oracle EQ | `diag3.py`'s `rebEQ`: C′ equalised to the measure DI's long-term spectrum. A repeat check against `diag3.json`. |
| 22–23 | transplant 5 ms, 10 ms | C′ × e_w(measure DI) / e_w(C′), w = 5 or 10 ms, then `eq_to` back to C′'s spectrum and LUFS. C′'s waveform detail and tilt, with the true DI's envelope. |
| 24 | C′ + oracle EQ + 10-ms transplant | Row 21 × e₁₀(measure DI) / e₁₀(row 21), then `eq_to` to the measure DI's spectrum and LUFS. Experiment 3's "both" ceiling. |

**Fold-2 extras (descriptive):** C′ seeds 1 and 2 (`models-cprime-s1`, `-s2`), C
(`models-set3/fold2.pt`), R (`models-resid/fold2.pt` with its FIR) and L
(`models-linear/fold2.pt`), on the 2 Today's The Day cells. **Both cells are uninformative, so these
rows feed D3 only.** Each is used only if its existing load path runs unchanged and the code's leak
assertion passes (the cell's band is not in that network's training pool). Otherwise it is dropped
and listed.

**Not included,** and why:
- **E0b** (and E0, E1): its codec and code live on `ml/egvae-lite` and its stored outputs are amp-track
  rebuilds, so it would need its own worktree, a new rebuild of the fakes and a leak check. It is
  the most diagnostic "coherence fails, m works" case, so it is a candidate for a follow-up.
- `flatref`: not a network rebuild of the fake.
- Other folds' C′ on a cell: they trained on that cell's band (a leak).
- Panel agreement (τ_panel, about 1.4k renders) and the zero-render judge rows (per-frame level
  judge, embedding guard): left for a later plan.

## Declared decisions

**Shared reading rules.**
- **Primary:** m_full, with the measure-DI mask for D1 and D2.
- **Base set.** An "inversion" (m ≤ 0) counts only on informative cells whose base m > 0 in that
  window; "restores" is counted on the same set. The plan reports each denominator n. The
  thresholds below are stated for n = 9 and rescale to ceil(fraction × n).
- **Fragile, not undecided:** a decision is reported as fragile if it changes under m_A or m_B
  instead of m_full, under the other mask, or when any one of the 6 bands is left out (thresholds
  rescaled). The declared reading still stands, and the fragility is stated beside it.
- **Per part:** every count is also shown per part. PR12 and SW50R share one DI, so the 9
  informative cells come from 5 DIs.
- **Placebo first:** if the placebo smear (row 5) inverts more than 1 cell, the margin is too
  fragile to read D1, and D1 is undecided.

**D1, dynamics against tilt.**
- **The crest reading:** the crest −3 dB rung inverts ≥ half (rounded up) of the base-set cells
  where it is reached, with at least 5 reached. Passing Ships is expected to drop (unreachable).
  If fewer than 5 are reached, D1 is undecided.
- **The tilt reading:** the C′-spectrum rung (row 17).
- **Readings:**
  - **Dynamics confirmed:** the crest reading holds, and C′ spectrum inverts ≤ 1.
  - **Dynamics and tilt:** the crest reading holds, and C′ spectrum inverts ≥ 2.
  - **Tilt, not dynamics:** the crest reading fails, and C′ spectrum inverts ≥ half.
  - **Neither:** otherwise. Then D2, the envelope smears and the phase-scramble rung are read.
- **Dose-response, descriptive:** crest −1.5 and −5 (at its achieved value); the five generic tilt
  rungs, with "≤ 1 inversion each" reported; the envelope smears.
- **Supporting, not deciding:** C′ crest (row 18) and the C′-envelope swap (row 16). If either
  inverts ≥ half, C′'s own dynamics are enough to flip the ranking.

**D2, the oracle-envelope transplant.** A transplant "restores" if m > 0 on ≥ two-thirds (rounded
up) of the base set, **and** on more cells than C′ itself. Read for the 5-ms and 10-ms transplants
(rows 22–23) and for the oracle-EQ transplant (row 24).
- **A plain transplant restores:** dynamics is the fixable part. Experiment 3's expander is the
  right first tool.
- **Only the oracle-EQ transplant restores:** dynamics and tilt must both be corrected; experiment
  3's "both" arm is required.
- **None restores:** one inference is that waveform detail, not dynamics, is the target. The
  alternatives are stated with it: the transplant's 5–10-ms gain modulation adds sidebands, which
  would bias towards "doesn't restore". Experiments 3 and 4 then target fine structure (transients,
  phase, top-octave content), and the expander alone is not expected to pass.

**D3, intrinsic proxies.** Each is computed between variant v and the measure DI over the full
window (and per half, reported), with the sign set so that higher means better:
1. crest error: \|crest(v) − crest(measure)\| (row 2's crest);
2. envelope correlation: Pearson of 10-ms log-RMS frames, on frames within 40 dB of the measure
   DI's loudest. **Floor:** defined only where the measure DI's own log-envelope standard deviation
   on those frames is ≥ 3 dB, evaluated per window. The review measured 1.4–1.6 dB for Passing
   Ships (dropped in every window) and 2.5 dB for colour me red on half A only (dropped there);
   every other part is 4.7–8.2 dB. Dropped cells are counted;
3. P90–P10 RMS spread error (as `learn/sound_desc.py` `describe`);
4. onset-flux error: 1 − Pearson of the half-wave-rectified log-magnitude spectral flux (STFT 1024,
   hop 256), v against the measure DI;
5. band level error at 200–1000 Hz: \|mean dB difference\| of mean-removed `smoothed_spectrum`;
6. band level error at 2–8 kHz, the same way;
7. **baseline:** coherence, 1–3 kHz (`learn/residual_eval.py` `_coherence`, `nperseg` 4096);
8. **baseline:** log-spectral distance (STFT 2048, hop 512, RMS dB difference over 80 Hz–10 kHz,
   mean over frames).

- **Statistic:** within each cell, the Spearman ρ between the proxy and m_full (mask v, as for a
  gate) across that cell's variants. All 12 cells are used: ordering needs no gap. Cell ρs are
  averaged within band, then across the 6 bands.
- **Interval:** a band-clustered bootstrap (resample the 6 bands with replacement, 10,000 draws,
  seed 20261018), 90% percentile interval.
- **Coherence is exactly 1 for every pure-EQ rung** (the placebo smear, both shelves, all bells,
  C′ spectrum): these are linear filters of the measure DI. So any tilt-sensitive proxy gains on
  coherence whenever the tilt rungs move m. ρ is therefore also reported **without the pure-EQ
  rungs**, and **on the real-rebuild rows only** (rows 19–24 and the fold-2 extras), within cell
  and pooled.
- **Adoption** for development screening, all three:
  1. band-weighted ρ ≥ **0.6**;
  2. the paired bootstrap lower 90% bound of (its ρ − coherence's ρ) is above 0;
  3. it **beats coherence in at least 5 of 6 bands** (the bootstrap is anti-conservative with 6
     clusters).
  - If several pass, the one with the highest ρ is adopted and the rest are reported. Picking the
    best of 6 is a mild winner's curse, which the next point covers.
- **Binding:** an adopted proxy is not yet a training loss. It must first be confirmed on other
  development cells (knob ceiling's realistic-control cells), in the plan that would use it.

**Power, stated plainly.** 12 cells from 6 bands, and the 9 informative cells come from 5 DIs. A
count of 5 of 9 against 4 of 9 is one cell. D1 and D2 are decisions about what to try next, not
estimates. "Undecided is not failed": an undecided D1 or D2 means experiment 3 runs all its
ablation arms, not that dynamics is ruled out.

**Repeat development use.** These 12 cells were used by step 3's control and by its audit
(`diag1`–`diag4`). This is their second use, declared as such. Experiment 3's control re-run on the
same cells would be a third, declared in its own plan.

## What the result decides

**Experiment 3 (fitted expander and tilt correction of C′):**
- **Its gate:** if step A adopts m provisionally, each correction arm (tilt only, expander only,
  both) must have m_A > 0 (mask v, lag 0) on ≥ 6 of 9 informative cells before its control re-run
  is spent. The sign per cell is then the pre-registered prediction for that re-run (step A). If
  step A is undecided, m can only stop an arm. If not adopted, every arm goes straight to the
  control re-run.
- **Its arms:** "dynamics confirmed" with a plain transplant restoring: expander first, tilt as an
  ablation. "Dynamics and tilt", or only the oracle-EQ transplant restoring: the "both" arm is
  required. "Tilt, not dynamics": the expander is dropped. No transplant restoring: experiment 3
  still runs (it is cheap), but a pass is not expected, and experiment 4 is planned in parallel.
- **The ceilings:** no fitted expander is expected to beat rows 22–23, and no "both" arm row 24.

**Experiment 4 (dynamics-aware retrain),** only if experiment 3 fails:
- after D1 "dynamics": a gain head, and envelope and crest terms in the loss;
- after D2 "none restores": transient or onset terms and a phase-aware loss, not only dynamics;
- an adopted D3 proxy becomes its pre-check metric and a candidate loss term, after confirmation.

**Arm A comes back only through the original control.** A corrected or retrained rebuild must pass
song-settings' known-target control as declared (amendment 2's rows, 150-render searches,
measure-DI and rebuilt runs) before arm A is re-run. A good m is a reason to run that control,
never a replacement for it.

## Order

1. This plan, the review (done), the ledger entry, then commit. No number before that.
2. `learn/rank_margin.py` and its tests; the tests pass.
3. Step A (zero renders). Written into the results file before step B renders.
4. Build the variants (numpy), and the 1-h and fold-2 rebuilds (torch interpreter, CPU). Run the
   lag check and the achieved crest, band-shift and envelope table.
5. Render step B: Morgan, `isolate=True`, 4 processes, `setopt no_bg_nice`. The repeat checks run
   first (rows 1, 19, 21 on all cells). A failure stops the run.
6. Decisions D1–D3, leave-one-band-out, per part, an independent audit, then
   `docs/rank-margin-ladder-results.md`, the ledger outcome, and the roadmap.

## Budget

| Part | Renders |
|---|---|
| Step A | 0 (no fallback fired) |
| Rungs on the measure DI: 18 variants × 12 cells × 3 (fewer where a crest rung is unreachable) | ≤ 648 |
| Real rebuilds and derived rows: 6 × 12 × 3 | 216 |
| Fold-2 extras: up to 5 × 2 × 3 | 30 |
| **Total** | **≈ 0.9k (hard stop at 1.2k)** |

**The running total.** song-settings-plan.md declares about 138k through step 3: knob ceiling 70k,
knob ceiling 2 about 15.7k (its actual), step 4 6.5k, and step 3's 46k. That includes arm C's
7.2k, which is no longer run. This plan uses the declared **138k** (an upper bound), so it brings
the total to at most about **139k**, against the 200k limit. At about 2 renders/s on 4 processes,
rendering takes about 10 minutes. CPU: the C′ 1-h rebuilds (12) and fold-2 extras (10), minutes
each. No MPS.

## Stated limits

- **The fake recording is a clean render** from the raw DI, C′'s training domain. The ladder says
  nothing about separation or real amp tracks.
- **The base is the measure DI, not the raw DI.** On 3 cells, T through the measure DI is not
  clearly closer than S. Those are the uninformative cells.
- **The ladder rungs are one family each.** A 10-ms static compressor is not C′'s squash. Rows 16
  and 18 are the closest stand-ins, and they are supporting evidence only.
- **The crest rungs miss one part:** Passing Ships' DI is already flat (crest 8.9 dB).
- **Envelope transplants modulate the waveform** at 5–10 ms, which adds sidebands. That would bias
  D2 towards "doesn't restore", which is stated.
- **Step A is small and partly seen.** 18 searches, one seed each, and the C′ margins were seen in
  the audit. Hence a provisional gate and a pre-registered prospective check.
- **12 cells, 6 bands, 5 DIs on the informative cells, 2 amps (PR12, SW50R), no AC20.** Clean and
  crunch are not reported apart.
- **The judge is the only reader.** No listening is needed: nothing here is a preset choice.

## Ledger entry (entered before any result)

```json
{
  "test_id": "rank-margin-ladder",
  "plan": "docs/rank-margin-ladder-plan.md",
  "entered": "2026-10-15, before any rank-margin compute",
  "repeat_use": "second development use of song-settings' 12 known-target control cells (first: step 3's control and its audit, docs/audits/song-settings-control-2026-10-15/)",
  "parts": [
    "cambridge-Today's_The_Day-ElecGtr10",
    "cambridge-Prodigal-ElecGtr5",
    "cambridge-just-don-t-talk-elecgtr3",
    "telefunken-Blind_Spots-GTR",
    "cambridge-Passing_Ships-ElecGtr6",
    "cambridge-colour-me-red-elecgtr01"
  ],
  "bands": "Diesel13, Doom Flamingo, Eat The Feeder, Starnes And Shah, The Travelling Band, Timo And The Timezone (song_settings.control_cells)",
  "audio_only": "bleed source cambridge-get-out-of-bed-elecgtr1 (Magician's Nephew, set 3, development), drawn by random.Random(20261017)",
  "gate": "Step A (provisional; m_A, mask v, lags 0 and -52 must agree): >= 15 of 18 informative searches agree with gap closed >= 50%, AND within the C' run m_A > 0 on >= 2 of 3 successes and m_A <= 0 on >= 4 of 6 failures -> provisional gate; 13-14 or the C' row fails -> screen only; <= 12 -> not adopted. Final only if the pre-registered per-cell predictions for experiment 3's control re-runs agree on >= two-thirds of informative searches. Step B (primary m_full, measure-DI mask for D1/D2; inversions counted on informative cells with base m > 0; halves, other mask and leave-one-band-out reported as fragility): placebo smear inverts > 1 -> D1 undecided. D1: crest -3 dB inverts >= half (rounded up) of reached cells with >= 5 reached, and the C'-spectrum rung inverts <= 1 -> dynamics confirmed; crest holds and C'-spectrum >= 2 -> dynamics and tilt; crest fails and C'-spectrum >= half -> tilt, not dynamics; else neither. D2: a transplant (5 ms, 10 ms, or oracle-EQ + 10 ms) restores if m > 0 on >= two-thirds of the base set and on more cells than C'. D3: a proxy is adopted if band-weighted within-cell Spearman rho >= 0.6, the paired band-clustered bootstrap lower 90% bound of (rho - coherence's rho) > 0, and it beats coherence in >= 5 of 6 bands; confirmation on other development cells is binding before any use as a loss.",
  "outcome": null
}
```

## Code to be written

**`learn/rank_margin.py`** (numpy and scipy, plus torch only in `rebuild`):
- `envelope(x, w)`, `crest_db(x)`, `match_spectrum(x, source)`, `compress_to_crest(x, delta_db)`
  (bisection on the re-EQ'd, LUFS-matched output), `placebo_smear(x)`, `envelope_smear(x, tau)`,
  `shelf(x, gain_db)`, `bell(x, gain_db)`, `phase_scramble(x, seed, ref)`, `bleed(x, other, db)`,
  `envelope_swap(x, donor, w)`, `spectrum_swap(x, donor)`, `transplant(x, ref, w, eq_to_ref)`: the
  rungs, each ending as declared.
- `variants(slug, amp)`: the declared list for a cell, with the leak assertion for every network
  and the unreachable-rung drops.
- `gcc_lag(x, ref, below_hz=None)`: the lag check, band-limited for the phase-scramble rung.
- `margin(fake, y_s, y_t, mask, lag, window)`: m_w, with the activity fallback and the refusal
  count; called with both masks.
- `proxies(v, measure, window)`: the 8 proxies, with the per-window envelope floor.
- `informative()`: the 9 cells from the stored `result.json` files.
- Steps (`python -m learn.rank_margin <step>`): `step-a`, `predict` (writes experiment 3's
  pre-registered signs), `build`, `rebuild` (torch interpreter), `render --shard i/n` (a render
  counter that stops at 1,200), `report`.
- Outputs under `~/ndsp-presets/learn/rank-margin/` (variants as `.npy`, a manifest with sha256s,
  per-cell distances as JSON). Nothing large in git.

**`tests/test_rank_margin.py`:**
- the compressor hits each crest target within 0.2 dB on a synthetic plucked signal, and
  `compress_to_crest(x, 0)` returns x;
- every dynamics rung changes the long-term spectrum by < 0.5 dB in every band;
- every rung keeps the length, stays finite, lands at −22.9 LUFS within 0.05, and has GCC lag 0
  (phase scramble: band-limited below 1 kHz, and aligned by construction on an impulse train);
- shelf and bell gains, measured with `smoothed_spectrum`, are within 0.3 dB of the declared curve;
- the placebo smear keeps envelope correlation ≥ 0.99 on a synthetic signal;
- phase scramble changes the long-term spectrum by < 0.5 dB and is deterministic for a seed;
- `transplant(x, x, w)` returns x, and transplanting a known envelope recovers it;
- `margin` signs, both masks, and the fallback on fixtures;
- step A's 2×2, the run-identity row and the lag-disagreement row on a fixture;
- `informative()` returns 9 cells from the stored files;
- the bleed draw returns `cambridge-get-out-of-bed-elecgtr1`;
- the leak assertion refuses another fold's C′;
- the render counter stops at its cap.

## Implementation notes (2026-10-15, before any compute)

- **Crest −5:** rendered at its achieved value, and only where crest −3 was reached. The plan
  also drops Passing Ships from every crest rung, so where the two said different things, this
  follows the drop.
- **Phase-scramble lag check:** ±3 samples below 1 kHz, as declared. Band-limited GCC reads 1–2
  samples even on aligned test signals.
- **No `predict` CLI yet:** only `predictions()`. Experiment 3's code adds the command.
- **Render cap:** each of the 4 shards stops if renders on disk plus 3 would pass 1,200, so the
  run can stop up to 9 renders short of the cap.
- **Leak check:** C is assumed trained with `cache-set3` as well, which is the conservative
  reading.
- **Coherence:** reimplemented to match `residual_eval._coherence` (1–3 kHz, `nperseg` 4096).
- **C′ + oracle EQ:** uses diag3's one-pass construction, so its repeat check against
  `diag3.json` holds.
