# A guitar tone encoder, trained on crossed renders: declaration

Step 2 of round 5's ranked list (`docs/research/round-5-guitar-models.md`), after the
DI-free reranker failed with general features (`docs/rerank-plan.md`). Declared on
2026-10-07, before any screening result is computed. Code: `learn/render_crossed.py`
(renders) and `learn/tone_encoder.py` (cache, training, screens). Output:
`~/ndsp-presets/learn/tone-encoder/`.

**Open source only.** The method is the Open-Amp Fx-Encoder's (Wright et al.):
SimCLR-style contrastive learning, the same device on different clips = positives, a small
residual conv stack with batch norm, ReLU and global pooling to a 64-d embedding. Its code
was read for the method only. Its checkpoint (no licence) is never loaded; the clone used
for reading was deleted. Everything below is trained from scratch on our renders.

## Data

**Crossed renders (new).** 300 blocks, each one amp, 8 sampled settings and 7 DI windows:
- **Windows:** one from each of 7 different bands drawn from the 14 of
  `learn/di_pool.py` (set 2's 13 development bands and Guitar-TECHS P1; windows with
  loudness ≥ −40 LUFS; 8 s, 2 s of pre-roll dropped, 6 s kept). Every window is checked
  with `learn/set3.py` `is_held_out` (must be false). Half the windows go through
  `render_pairs.pre_eq` (a mild guitar EQ, the same for every setting of the block).
- **Settings:**
  - PR12, 175 blocks: `learn/pr12.py` `sample` (half coverage, half jittered factory
    presets), rendered with the PR12 rule set;
  - SW50R and AC20, 63 and 62 blocks: `learn/render_pairs.py` `settings` (a factory base
    with R, knobs redrawn).
- Every setting of a block is rendered through every window of the block: 2,400
  settings, 16,800 renders. Peak-normalised 16-bit FLAC; renders that are silent, or that
  needed more than 60 dB of gain, are dropped.
- 3 render workers; the licence daemon is only read, never touched.

**Panels (reused).** `runs/kill/{pr12,sw50r,ac20}` (and `pr12-clean`, whose files are
the same): every factory preset with R, and template+R, through the 43 development
parts' DIs (10 s). The shipped template (without R) is left out. The 8 development parts
silent over half A (the rerank amendment) are left out of training, as of every
candidate's sound.

**Positives and negatives.** A training batch has 6 groups, drawn without replacement.
Each group is a crossed block (probability 2/3) or one amp's panel (1/3): 8 settings, each heard through the same 3 DIs
(windows or parts) of that group. Views of the same setting are positives (SupCon); the
other settings through the same DIs are hard negatives; other groups are easy negatives.

## Folds and guards

One encoder per K3 fold (`learn/train.py` `k3_folds`); all four are needed, since K1's 25
parts span all four folds. The fold-f encoder:
- trains on no clip whose DI comes from a band in fold f: no window, no panel part;
- takes bleed only from the instrumental backings of other folds' development crops;
- Guitar-TECHS P1 (no K1 part) trains in every fold.

Held-out sessions and set 3 are never read.

## Features, augmentation, model, training

- **Frontend:** 48 kHz mono, power STFT (Hann 2048, hop 480 = 10 ms), 128 triangular
  mel bands, 30 Hz–16 kHz. Cached as dB.
- **Augmentation**, per view and independently. It is applied to mel power, an
  approximation of the waveform-domain version in `learn/direc.py` that ignores cross
  terms:
  - post-amp EQ: tilt ±3 dB and a ±4 dB, half-octave bell at 200 Hz–6 kHz;
  - bleed, probability 0.5: a random 3-s stretch of another fold's backing, 12–30 dB
    below the clip;
  - white noise, probability 0.5: 45–75 dB below the clip.
- **Level:** each view is loudness-normalised (mean total mel power over frames within
  40 dB of its loudest frame), then turned to dB at absolute level: (dB + 40)/20, floored
  at −100 dB. There is no per-frequency normalisation.
- **Model:** 487k parameters. The 128 mel bands are the input channels of a 1-D
  residual conv stack over time:
  - an input conv, then 4 residual blocks, each ReLU(x + BN(conv(ReLU(BN(conv(x)))))),
    kernel 3, width 128, pooling time by 2 after each of the first three;
  - mean and std over time, a 256→128→64 head, and L2 normalisation.

  A 2-D conv over the mel image was measured at 11–17 s a step on this CPU, too slow.
  The 1-D form sees absolute spectral shape directly.
- **Training:**
  - SupCon (NT-Xent with several positives), temperature 0.1;
  - batch 6 groups × 8 settings × 3 views (≤ 144);
  - 3-s random crops;
  - AdamW, weight decay 1e-4, one-cycle schedule peaking at 1e-3 (`pct_start` 0.05);
  - **4,000 steps per fold**, seed 20261008. The last weights are used: no early
    stopping and no selection.
  - Monitoring only: 8-way leave-one-DI-out identification on 5% of the crossed blocks,
    held back from training (training-fold DIs).
- **Device:** CPU for every fold (`PYTORCH_ENABLE_MPS_FALLBACK=0`): another job holds
  MPS until at least 02:00.
- **Fixed in advance:**
  - The monitoring numbers and loss logs cannot change the steps, the seed or any
    hyperparameter.
  - A fold that crashes is re-run from scratch with the same seed.
  - A fold whose loss goes non-finite is re-run once with seed + 1, and this is reported.
  - The checkpoint records its steps, seed and fold. The screens assert them.

## Screen 1: the identification test (gate)

- **Trials:** for each K1 part p (the 25 of `k-judge-pr12-clean.json`) and each of the 22
  menu candidates c (template+R and the 21 clean factory presets of `pr12-clean`): the
  pr12-clean panel render of c through p's DI, half A (1.0–5.5 s). 550 trials.
- **Candidate sound:** the mean over the renders of that candidate through the DIs of
  development parts in K3 folds other than p's, without the 8 silent parts.
  - Encoder: the fold(p) encoder. Distance: cosine to the re-normalised mean of the
    embeddings.
- **Score:** each trial ranks the 22 candidates by distance. Ties count against the true
  candidate. Reported: top-1 accuracy
  pooled over the 550 trials, top-3, mean rank, top-1 per fold, the band mean, and a
  band-cluster bootstrap 95% interval. Chance is 1/22 = 4.5%.
- **Baselines**, recomputed the same way from `learn/rerank.py`'s cached features:
  - log-mel: z-scored with all other-fold renders' mean and std, Euclidean;
  - PANNs CNN14: cosine.
  - The rerank review reported 13.5% and 12.7% for them.
- **Gate:** pooled top-1 ≥ 30% to proceed to screen 2.

**Secondary, descriptive, not gating.** A "no-menu" encoder per fold is trained by the
same recipe, without any render of the 22 menu candidates. It also leaves out every
crossed PR12 setting jittered from one of them (each setting's base is re-derived from its
seed). It is scored on screen 1 only, to show whether identification carries beyond
presets the encoder trained on.
It runs after the primary encoders, as CPU time allows.

## Screen 2: the reranker test (only if screen 1 passes)

Exactly as `learn/rerank.py` and `docs/rerank-plan.md`, with two rows added:
- **Rows:** `enc_ref` (amp track, 25 parts) and `enc_stem` (htdemucs_6s stem, the 18
  usable parts).
- **Picks:** half A of the recording, through the fold(p) encoder; the pick is the
  candidate whose mean embedding (as in screen 1) is nearest by cosine.
- **Scoring:** `rerank.score`: the pick's render through the measure DI, half B, the
  average-guitar measure, log ratio to template+R, under both band sets. Reported beside
  `flatref`, `flatstem`, `net`, `netstem`, the oracle, and the log-mel and PANNs rows,
  all recomputed.
- **Gate:** under both band sets, beats `flatref` (`enc_stem`: `flatstem`) paired:
  band median of the difference ≤ log 0.95 and band sign-flip p < 0.1. Two rows, with no
  multiplicity correction.

## Review before commit

An independent reviewer read the plan and code before any screen was run. It found no
fold leakage and no held-out data. Its fixes, applied before this commit:
- the step default set to the declared 4,000;
- the no-menu exclusion of jittered menu presets;
- the standard residual form;
- panel embeddings tied to the model files' hashes;
- ties counted against the true candidate;
- groups drawn without replacement;
- asserts that the panel and bleed parts are development parts and that the 8 silent
  parts match rerank's.
