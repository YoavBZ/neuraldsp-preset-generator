# Rank margin and the degradation ladder: results (DI-recovery experiment 2, 2026-10-15)

Run under the [plan](rank-margin-ladder-plan.md) and its implementation notes.
- **Scope:** the 12 known-target control cells (9 informative), development only.
- **Renders:** 840 in the run, plus 81 in the audit, all `isolate=True`.
- **Data:** `~/ndsp-presets/learn/rank-margin/` (`report.json`, `scores/`, `variants/`). The
  audit's scripts and renders are in `audit/`.
- **Independent audit:** every count was recomputed from `scores/`, and every variant measured
  from its file. The repeat rows match the stored figures within 3e-4.

## Step A: the rank margin is a screen only

The margin m (log d(S) − log d(T) through a DI) agrees with search success on 14 of 18
informative searches. The bar was 15, so it is a **screen**.
- Within the C′ run it gets 5 of 9 right, which is a coin flip (Spearman 0.00).
- It is positive on 3 searches that failed.
- So a positive margin doesn't mean the search will work. Don't use it to pass or stop a rebuild:
  only the full known-target control can.

## Step B: what flips the ranking

Read on the full 1–10 s window with the measure-DI mask. Every other window and the other mask
give the same readings.
- **The masks agree everywhere:** no frame of any measure DI is 40 dB below its peak, so the
  activity mask doesn't change anything here.

| Rung (applied to the true DI unless stated) | Cells inverted |
|---|---|
| Placebo smear | 0 of 9 |
| Crest −3 dB (a static compressor, spectrum held within 0.14 dB) | 1 of 7 |
| C′'s long-term spectrum | 1 of 9 |
| Shelves −2 and −4 dB, bells +1 and +3 dB | 0 of 9 each |
| Bell +5 dB, envelope smear 10 and 30 ms | 1 of 9 each |
| C′'s envelope (correlation 0.76–0.98 with C′'s) | 0 of 9 |
| Compressed to C′'s own crest | 1 of 4 |

- **D1, neither:** neither lost dynamics nor C′'s tone balance flips the ranking on its own.
- **Description only:** crest −5 never reached 5 dB. It achieved 3.0–3.8 dB, so it repeats
  crest −3.

**D2, the oracle envelope on C′:**

| Variant | Positive | Mean m |
|---|---|---|
| The true DI | 9 of 9 | 0.244 |
| C′ | 5 of 9 | 0.053 |
| C′ with the true 5-ms envelope | 8 of 9 | 0.060 |
| C′ with the true 10-ms envelope | 8 of 9 | 0.064 |
| C′ with oracle EQ | 7 of 9 | 0.063 |
| C′ with oracle EQ and the 10-ms envelope | 7 of 9 | 0.065 |

- **By the declared count, the transplant "restores".** But the audit shows the count is
  misleading. Three of C′'s margins sat at −0.01 to −0.02, and the transplant nudged them
  across zero.
- **On average it recovers only about 6% of C′'s loss** (0.053 to 0.064, against 0.244). Oracle
  EQ alone passes the same count.
- **Not noise:** a placebo on C′ moves m by at most 0.013.
- **Not a pitch-ripple leak:** a 50-ms transplant gives the same result.
- **The reading:** no slow-envelope or tone fix restores C′ in substance. The rule was too
  lenient, and that is stated, not hidden.

**D3:** no cheap proxy is adopted. LSD (ρ 0.51) and onset error (0.48) are close to coherence
(0.46), and none clears the bar.

## Where C′'s error is

- **What the oracle corrections leave:** about 94% of C′'s loss in margin remains after
  correcting its long-term spectrum, its 5–50 ms envelope, or both.
- **A static expander is an upper bound with no effect:** the audit fitted the best monotonic
  level curve from C′'s envelope to the true DI's, using the oracle. It stays at 5 of 9 positive,
  with a mean m of 0.035.
- **C′'s crest loss is fast:** 3.6–5.5 dB, mostly at timescales under 10 ms, beyond what a
  compressor or a transplant on that scale reaches.
- **C′'s quiet passages are 15–20 dB too loud:** frames 20–40 dB below the DI's peak sit only
  6–8 dB below C′'s own peak.

So C′'s error is in **fine structure and transients**: waveform detail under about 10 ms. It is
not tilt, and not slow dynamics.

## What it decides

- **Experiment 3** (a fitted expander and tilt correction of C′) is **not run.** Its oracle
  ceiling barely moves the margin, and an oracle-fitted expander does nothing.
- **The main effort moves to experiment 4,** a C′ successor aimed at fine structure and
  transients. Its design comes from new research first: losses, architecture, and training on
  separated stems.
- **The gate for any rebuild is the full known-target control,** not the margin. A rebuild must
  close at least half the gap on two-thirds of the informative cells.
- **The separator screen still runs** (its own plan). Through the true DI, its margin reads the
  separator's own effect. As a screen it is weak, so its result is descriptive.

## Stated limits

- 12 cells from 6 bands, used for the second time.
- One amp family (Morgan).
- Clean renders, not stems.
- **Smaller defects in the run:**
  - crest −5 mislabelled;
  - two crest −5 variants 0.8 dB under level (pyloudnorm's gate on a very quiet signal);
  - the C′ 1-h checkpoint dropped on 7 cells by the lag check (lags of 44–59 samples, worth a
    look before that checkpoint is reused).
