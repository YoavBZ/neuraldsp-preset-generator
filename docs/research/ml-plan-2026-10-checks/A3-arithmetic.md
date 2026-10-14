# A3: arithmetic checks behind the plan

Recomputed on 2026-10-14 with Python 3 and SciPy 1.18. Script: [`arith.py`](arith.py), beside this note; every number below is its output.

## Power for a band-level test

One-sample t on band means, band SD 0.101, one-sided α = 0.05 (a 90% interval whose upper end is below 0). The SD 0.101 is a crude figure: the spread of about 4 band means on set 5 crunch (`docs/stem-test-power.md:19-20`).

| Bands | −0.05 | −0.08 | −0.10 | −0.13 |
|---|---|---|---|---|
| 3 | 0.15 | 0.24 | 0.32 | 0.44 |
| 4 | 0.19 | 0.34 | 0.45 | — |
| 5 | 0.24 | 0.43 | 0.57 | 0.76 |
| 8 | 0.35 | 0.65 | 0.81 | 0.95 |
| 10 | 0.42 | 0.75 | 0.89 | 0.98 |
| 11 | 0.45 | 0.79 | 0.92 | — |
| 12 | 0.49 | 0.82 | 0.94 | 0.99 |
| 15 | 0.57 | 0.90 | 0.98 | 1.00 |
| 20 | 0.69 | 0.96 | 1.00 | — |
| 25 | 0.78 | 0.99 | 1.00 | — |

- Bands needed for 80% power: **27** at −0.05, **12** at −0.08, **8** at −0.10.
- Report A's table (9 bands 0.39/0.86; 12 bands 0.49/0.94) is reproduced exactly.
- The project's own table (`docs/stem-test-power.md:24-30`) gives 9/18% at 3 bands and 32/80% at 8. At 8 or more bands the two agree within 3 points. The project's lower figures at 3 bands come from its choice of test, which is more conservative at very small N.
- An exact sign-flip test on k bands cannot reach p below 2^−k: 0.125 (3), 0.031 (5), 0.016 (6), 0.0078 (7).

## Listening trial counts

Decided trials needed for 80% power, one-sided exact binomial test against 0.5 at α = 0.05:

| True agreement | 0.90 | 0.80 | 0.75 | 0.70 | 0.65 | 0.60 |
|---|---|---|---|---|---|---|
| Trials | 8 | 18 | 23 | 37 | 69 | 158 |

These match Report A. The ceiling on agreement for a listener with repeat consistency c is (1 + √(2c − 1)) / 2, which is 0.887 at c = 0.8.

Checks of reported p-values: 17/21 gives one-sided p 0.0036 (the project reports 0.004). 23/24 gives 1.5e-6.

## Log ratios as "% closer"

1 − e^r: −0.023 → 2.3%, −0.05 → 4.9%, −0.087 → 8.3%, −0.10 → 9.5%, −0.104 → 9.9%, −0.129 → 12.1%, −0.131 → 12.3%, −0.15 → 13.9%, −0.19 → 17.3%.

## Render counts

| Item | Arithmetic | Result |
|---|---|---|
| Report A's ladder | 13 non-optional versions × 30 parts × 111 | **43,290** (A said "≈40k"; 39,960 if the true-DI rung is reused; 46,620 with the optional symbolic rung) |
| Report A's ranker bank | 200 × 111 + 100 × 111 + 10,000 | 43,300 (correct) |
| Report B's bank | 60,000 × 4 s | 66.7 h of audio (correct) |
| Report B's headroom search | 16 × 12 × 3 per part per tier; × 20 parts | 576; 11,520 (correct) |
| Report B's product search | 16 × 10 × 4 | 640 (correct) |
| Knob ceiling | 25 × 111 + 75 × 2 × 450 | 70,275 (matches its plan) |
| Mega-53 on 21k clips | 21,000 × (102 s / 3) | 198 h (correct) |
| htdemucs on 10k clips | 10,000 × (15 s / 3) | ~14 h CPU (estimate; assumes linear scaling from a 30-s context) |

## Disk

| Item | Size |
|---|---|
| 10 s, 48 kHz, 16-bit mono WAV | 0.96 MB (40k clips: 38.4 GB) |
| 10 s, 44.1 kHz, 16-bit mono WAV | 0.88 MB |
| 6 s, 44.1 kHz, 16-bit mono WAV | 0.53 MB |
| Log-mel 128 × 1,000 frames (10 s, 10 ms hop), float32 | 512 KB (43.3k clips: 22.2 GB) |
| Same, float16 | 256 KB (43.3k: 11.1 GB) |
| Log-mel 128 × 400 (4 s), float16 | 102 KB (43.3k: 4.4 GB) |

**Correction to Report A:** "log-mels ~50 KB per clip" holds only for about 64 bands × 400 frames in float16. A 10-s, 128-band log-mel at 10 ms is about 256 KB in float16. Report A's "~4 GB" for the ranker holds only for 4-s crops in float16.

The usable disk is about **35 GB**: 65 GB free minus the 30 GB floor the project keeps in practice (`docs/validation-set4-plan.md:329-331`; `docs/residual-di-plan.md:92-93`).

## Other constants

- 65,536 samples is 1.486 s at 44.1 kHz and 1.365 s at 48 kHz. That is the MPS `torch.stft` gradient limit.
- DAC 44 kHz: hop 512, so 86.13 latent frames/s, 1,024-d, 9 codebooks. Verified in B2.

## Added after the review: can F1's "futile" outcome be reached?

With band SD 0.101, the standard error of a band mean is 0.101/√k. With a flat prior and a posterior mean of exactly 0, the most that P(|θ| < c) can reach is:

| Bands | c = 0.03 | c = 0.05 |
|---|---|---|
| 8 | 0.599 | 0.839 |
| 9 | 0.627 | 0.862 |
| 11 | 0.675 | 0.899 |

A "futile" rule of P(|θ| < 0.03) > 0.8 can never fire. P(|θ| < 0.05) > 0.8 is reachable only near a zero mean, with 8 or more bands. The plan uses the 0.05 version.
