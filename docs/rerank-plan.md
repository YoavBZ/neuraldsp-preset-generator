# DI-free reranker on clean PR12: declaration

Step 3 of the 2026-10-07 checkpoint in `docs/di-recovery-plan.md`. Declared before any
result is computed. Code: `learn/rerank.py`; output: `~/ndsp-presets/learn/rerank/`.
CPU only (`device='cpu'`, `PYTORCH_ENABLE_MPS_FALLBACK=0`), no renders.

## What is compared

- **Parts:** K1's 25 clean PR12 parts (`k-judge-pr12-clean.json`, bands and lags from it).
- **Menu:** the 22 candidates phase2 chooses from: template+R and the 21 clean factory
  presets of `runs/kill/pr12-clean/index.json`.
- **A candidate's sound for part p:** its panel renders through the DIs of every
  development part (of 43) whose band is in a K3 fold (`learn/train.py` `k3_folds()`)
  other than p's. p's own part, band and fold never enter.
- **Inputs:** the amp track (`reference.wav`, 25 parts) and the htdemucs_6s guitar stem
  (usable parts per the stems manifest, 18).

## Features (half A, 1.0–5.5 s, of the recording and of each render, mono)

Each clip is loudness-normalised to −22.9 LUFS (pyloudnorm) first.

- **mel:** power STFT (Hann, n_fft 4096, hop 480) at 48 kHz → 64-band mel (librosa,
  50 Hz–16 kHz) → dB. Frames kept if their total mel power is within 40 dB of the
  clip's loudest frame. Feature: per-band mean and std over kept frames (128-d).
- **panns:** resampled to 32 kHz; PANNs CNN14 (`Cnn14_mAP=0.431.pth`, Zenodo 3987831,
  CC BY 4.0) in eval mode; 2048-d embedding of 1-s windows at a 0.5-s hop (8
  windows), mean-pooled.

## Picks

For part p, each candidate's feature is the mean over its other-fold renders.
- **mel:** Euclidean distance after z-scoring each dimension with mean and std fitted on
  all other-fold renders (all candidates) for p.
- **panns:** cosine distance.

The pick is the nearest candidate. Four rerankers: `mel_ref`, `panns_ref` (amp track),
`mel_stem`, `panns_stem` (stem).

## Scoring

Exactly as `learn/phase2.py` `score()`: the pick's render through the measure DI
(`learn/direc/phase2/measure/<part>/`), half B (5.5–10 s) against the amp track at the
part's lag, `aligned_distance` under both band sets (`recording`, `union`), log ratio
against template+R. A pick whose distance is undefined is missing. Summaries with
`research/kill_tests.py` `band_stat`.

Rows reported side by side: template+R (0), `flatref`, `flatstem`, `net`, `netstem`
and the measure's oracle (read from `learn/direc/phase2/result.json`; flatref and the
oracle are recomputed as a check of the scoring code), and the four rerankers. Paired
rows: reranker − `flatref` and reranker − `net` (amp track); reranker − `flatstem` and
reranker − `netstem` (stem), each with `band_stat`.

## Gate

A reranker earns a place only if, under **both** band sets, it beats `flatref` (stem
rerankers: `flatstem`) paired: band median of the difference ≤ log 0.95 (−0.0513) and
band sign-flip p < 0.1. Four rerankers are tested with no multiplicity correction;
whatever comes out is reported.

## Amendment before any result (data check)

A data check found that 8 of the 43 development parts are silent or near-silent over half
A: their template+R render reads −∞ LUFS (Drag Me Down ElecGtr3, Prodigal ElecGtr1 and
ElecGtr4, Passing Ships ElecGtr3, Nosso Mundo ElecGtr03) or −39 to −56 LUFS (Prodigal
ElecGtr2 and ElecGtr3, Hikikomori). The next quietest reads −19.5 LUFS. Loudness
normalisation would blow their noise floor up to −22.9 LUFS, so a part whose template+R
render over half A is quieter than −35 LUFS is dropped whole from every candidate's
sound (all candidates lose the same parts). None of the 25 K1 parts is affected; no
K1 recording is quieter than −32 LUFS. Nothing else changes.
