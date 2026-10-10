# A better DI-rebuilding network: pilot results (set 3, development)

Run 2026-10-10 as declared in [di-network-v2-plan.md](di-network-v2-plan.md) (plan
committed 00:54:38, training started 00:54:42). An independent reviewer re-derived
every number with their own code, re-built the data pool and spot-checked 40 distances
on stored renders. They found no leakage and no harness fault
(`tmp/v2-pilot-review.md`, local).

**Outcome under the declared rule: neither arm helps.**

## Runs

Both arms continue `models-set3/fold2.pt` for 180 minutes on MPS, learning rate 1e-4 →
1e-5 (cosine), seed 20261010.

- **B, longer** (the same data): one automatic recovery at step 541, then clean.
- **A, more guitars** (plus 11,986 pairs rendered from 38 set-3 development DI tracks
  in 11 bands, with fold 2's bands excluded):
  - **First attempt:** fell into repeated MPS non-finite gradients (5 recoveries). It
    was restarted in a fresh process, as the stage script allows.
  - **Restart:** clean, with no skipped steps.
  - **Data check:** none of the extra data came from fold 2's bands or the held-out
    split.
- **Validation loss** stayed flat at about 58 in both runs (59 to 60 before). That is
  per 8 batches: about 7.3 per batch.

## Picks

Pooled over the three amps; mean log ratio of the pick's half-B distance (negative is
closer), with wins / ties / losses. All picks use the reference-proxy fallback; the
current network is re-scored the same way.

| comparison | parts | recording bands | union bands |
|---|---|---|---|
| **B vs current network** | all 33 | **−0.012** (10 / 85 / 4) | −0.007 (9 / 86 / 4) |
| **A vs current network** | fold 2 (12) | **−0.015** (7 / 28 / 1) | −0.004 (3 / 32 / 1) |
| A vs B | fold 2 (12) | +0.021 (2 / 31 / 3) | +0.023 (0 / 34 / 2) |
| B vs fixed driven preset | all 33 | −0.049 (40 / 19 / 40) | −0.059 (43 / 18 / 38) |
| current network vs fixed driven preset | all 33 | −0.037 (38 / 19 / 42) | −0.053 (41 / 18 / 40) |
| B vs clean template | all 33 | −0.40 (85 / 0 / 14) | −0.38 (87 / 0 / 12) |
| oracle vs B | all 33 | −0.19 | −0.19 |

The rule needs −0.05 or lower and more wins than losses. Both arms fail on the mean.

(The fixed driven presets were chosen on these same 33 parts, so the comparison
against them leans in the presets' favour.)

## Why nothing moved: most of the network was dead

The reviewer found that in every DI network trained so far, the bottom of the U-Net
does nothing.
- **The gate:** the decoder's first GLU gate is shut (pre-activation about −6,000,
  output exactly 0).
- **What it cuts off:** `enc.4`, the dilated bottleneck that carries ±0.3 s of context,
  and `dec.0`. That is 8.4M of the 9.8M weights, with zero gradient.
- **The evidence:** those weights are bit-identical before and after both arms. The
  networks rebuild DIs with their shallow levels alone.

That matches what was measured:
- The rebuilt DIs of both arms correlate with the current network's at 0.97–0.995.
- Their spectral distance to the true DI did not improve (6.1–6.3 dB).

**Correction to the plan.** Its "loss 7 against 60" was not memorising. The validation
figure in the log is summed over 8 batches.

## Next

Repair the bottom first ([v3 plan](di-network-v3-plan.md)), and only then revisit data
and training length.
