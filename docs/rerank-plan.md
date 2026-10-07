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

## Result, 2026-10-07: no reranker passes

Run: `learn/rerank.py`, output `~/ndsp-presets/learn/rerank/result.json`. The 100
recomputed oracle and `flatref` scores match phase2's `result.json`. CPU only: 510 s of
CPU for features (989 clips), 140 s for picks and scoring, 260 s wall.

Log ratio to template+R, band median (parts closer than template+R; sign-flip p):

| Row | recording bands | union bands |
|---|---|---|
| oracle | −0.171 (25/25) | −0.146 (24/25) |
| `flatref` | −0.034 (16/25) | −0.034 (17/25) |
| `net` | −0.089 (20/25) | −0.088 (20/25) |
| `mel_ref` | −0.096 (16/25; 0.24) | −0.046 (14/25; 0.43) |
| `panns_ref` | −0.026 (16/25; 0.27) | −0.010 (12/25; 0.45) |
| `flatstem` | −0.042 (13/18) | −0.042 (14/18) |
| `netstem` | −0.038 (15/18) | −0.067 (15/18) |
| `mel_stem` | −0.056 (13/18; 0.19) | −0.057 (12/18; 0.27) |
| `panns_stem` | −0.011 (10/18; 0.33) | −0.016 (9/18; 0.37) |

Paired, band median of the difference (parts where the reranker is closer; p):

| Pair | recording bands | union bands |
|---|---|---|
| `mel_ref` − `flatref` | +0.044 (10/25; 0.42) | +0.054 (10/25; 0.51) |
| `mel_ref` − `net` | +0.009 (8/25; 0.98) | +0.034 (8/25; 0.88) |
| `panns_ref` − `flatref` | 0.000 (12/25; 0.32) | +0.012 (9/25; 0.57) |
| `panns_ref` − `net` | 0.000 (11/25; 0.65) | 0.000 (11/25; 0.82) |
| `mel_stem` − `flatstem` | −0.020 (10/18; 0.55) | −0.012 (8/18; 0.72) |
| `mel_stem` − `netstem` | 0.000 (7/18; 0.64) | 0.000 (7/18; 0.67) |
| `panns_stem` − `flatstem` | +0.000 (8/18; 0.65) | +0.028 (5/18; 0.88) |
| `panns_stem` − `netstem` | +0.042 (5/18; 0.03) | +0.038 (2/18; 0.11) |

**Gate:** none of the four passes; none beats `flatref`/`flatstem` paired under either
band set. The log-mel row on the amp track has the best unpaired band median under the
recording bands (−0.096, about 9% closer), but it falls to −0.046 under the union bands
and is worse than `flatref` paired under both. PANNs is near template+R and does no
better than the log-mel baseline; on stems it is worse than `netstem` (p 0.03, recording
bands). The network's picks (`net`) remain the best chooser on this set.
