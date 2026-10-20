# X-LANCE against Mega-53 fast: separator screen results (2026-10-21)

Run under the [plan](xlance-screen-plan.md) (cb04445, declared and reviewed before any download).
Development data only. Ledger entry `xlance-screen`.
- **Code:** `learn/xlance_screen.py`, tests `tests/test_xlance_screen.py`.
- **Data:** `~/ndsp-presets/learn/xlance-screen/` (`report.json`, `audit-per-clip.json`,
  `stagef-per-part.json`, `repro.json`, `time-mega53.json`, `xlance-log.json`, `stems/`).
- **Tools:** `~/ndsp-presets/tools/xlance/` (`manifest.json`; weight hashes match Hugging Face's).
- **Compute:** 227 X-LANCE separations on the CPU (2 threads, nice 10), about 2.3 h wall; 16 Mega-53 fast
  separations (6 reproduction clips at 4 threads, 10 timing clips at 2). **Renders: 0. No MPS.**
- **Checks passed:**
  - all 164 gate 1 audit stems match their stored hashes;
  - all 6 reproduction clips match gate 1's stems at 328 dB or better;
  - every X-LANCE stem lies within ±3 samples of its reference (worst: −3, on 2 audit clips).

## Verdict: PASS, OVER BUDGET (the user decides)

- **Tone: X-LANCE is clearly better.** On the 164 audit mixes, X − Mega-53 for LSD over the
  mel range is **−1.82 dB [−3.09, −0.54]**. It is lower in 5 of 6 bands and in 125 of 164
  clips, and the leave-one-band-out range is −2.34 to −1.48.
- **SNR is a tie, leaning to X-LANCE:** **+0.14 dB [−0.11, +0.39]**, leave-one-band-out
  +0.07 to +0.21.
- **Cost fails the declared check.** On the same 10 clips and 2 threads, X-LANCE takes 52.6 CPU s
  per 10-s clip and Mega-53 fast 29.7: **1.78×**, against a 1.5× limit (wall 1.74×). Scaled, the
  build's 13–17 h of separation for the rest becomes about 23–30 h. X-LANCE's speed on the MPS
  is not measured; the build separates there.
- So both quality conditions hold and the cost condition does not. Under the declared rule
  Mega-53 stays unless the user accepts the cost.

## Audit mixes (decides; 164 clips, 6 bands, exact rendered guitar as reference)

Band-weighted means; 90% band-clustered t intervals (5 df), with the band bootstrap beside them.

| X − M_f | All 164 | Bootstrap | Without MUSDB18 (139, 5 bands) |
|---|---|---|---|
| **SNR (dB)** | **+0.14 [−0.11, +0.39]** | [−0.05, +0.32] | +0.19 [−0.11, +0.48] |
| **LSD, mel range 30 Hz–16 kHz (decides)** | **−1.82 [−3.09, −0.54]** | [−2.70, −0.80] | −1.88 [−3.53, −0.24] |
| LSD, 80 Hz–12 kHz | −0.52 [−1.97, +0.92] | [−1.60, +0.55] | −0.66 [−2.50, +1.18] |
| Brightness difference (dB) | −1.86 [−5.89, +2.16] | [−5.50, +0.61] | −2.41 [−7.43, +2.61] |
| SI-SDR (dB) | +0.19 [−0.80, +1.17] | [−0.58, +0.92] | +0.31 [−0.93, +1.55] |

**Levels:**

| | SNR | mel LSD | full LSD | brightness diff |
|---|---|---|---|---|
| M_f | 2.74 | 9.46 | 6.92 | +0.99 |
| X | 2.88 | 7.64 | 6.40 | −0.88 |
| mix (floor) | 0.57 | 12.25 | 9.37 | +4.71 |

- **Most of the gain lies outside 80 Hz–12 kHz.** The full LSD gains only −0.52 and its interval
  crosses 0, so most of X-LANCE's advantage is at the extremes (below 80 Hz, 12–16 kHz). That is
  where the 2026-10-08 screen found Mega-53's largest losses.
- **Darkening spread** (the mean gain-removed error above 3 kHz):
  - Mega-53: median −4.66 dB, SD across clips 5.86.
  - X-LANCE: −3.39 dB, SD 7.29.

  X-LANCE darkens less on average but less consistently. A fixed brightness correction would
  suit Mega-53's stems a little better.
- **The average hides one band.** On Death Of A Romantic, X-LANCE is 11.5 dB darker than Mega-53
  on the 3–10 kHz brightness ratio (5.9 dB on the mean error above 3 kHz). That band drives the
  wide brightness interval; in the other five bands the brightness difference is −1.6 to +1.8 dB.
- **Without Cambridge sessions** (Eggy, Renesans; 2 bands, point estimates only):
  - SNR: +0.48 and −0.01.
  - Mel LSD: −1.19 and −2.48.

  The tone gain does not depend on Cambridge material.

## Stage F (descriptive; against the amp track)

| X − M_f, band bootstrap | 19 parts with another guitar (10 bands) | All 21 (12 bands) | Without MUSDB18 (18) |
|---|---|---|---|
| SNR | +0.04 [−0.01, +0.08] | −0.37 [−1.18, +0.06] | −0.51 [−1.58, +0.07] |
| mel LSD | −1.07 [−2.45, +0.71] | −0.25 [−1.84, +1.50] | +0.26 [−1.76, +2.45] |
| full LSD | −0.75 [−1.81, +0.50] | −0.04 [−1.29, +1.32] | +0.50 [−0.96, +2.12] |

- **One failure drives the all-21 rows.** On She's Gone (Bernard Purdie Tribute, the only guitar
  in its mix), X-LANCE gets 0.36 dB SNR against Mega-53's 5.21, and its mel LSD is 15.1 against
  8.3. The other single-guitar part ties (6.29 against 6.28).
  X-LANCE's stem there follows the mix (correlation 0.52) more than the guitar (0.28), at 2.7×
  the guitar's level: it lets the backing through. This is a real separation failure, not an
  alignment error (lag 0).
  No audit clip loses SNR like this (worst −1.8 dB), though one (27360, Death Of A Romantic) is 12.0 dB
  worse on mel LSD (29670, same band, 5.75). A song-specific failure of this size is a risk for the
  product, and a reason to keep Mega-53 as the fallback.
- **On the 19 multi-guitar parts it ties,** as on 2026-10-08. The class anchor G is only +0.44
  above Mega-53 here: the other guitars set the limit.
- **Variants:**
  - gtr_mss alone is the same as the chain (SNR identical to 0.01 dB; mel LSD −1.34 on the 19 parts,
    against −1.07 for the chain).
  - The 30-s context does not help (mel LSD −1.21 on the 19 parts).
  - Skipping `denoise` would save about 44% of X-LANCE's time:
    on stage F, 12 s of 28 s wall per clip (21 of 48 CPU s). It is descriptive here and not tested on the audit mixes.
- **The class job:** SNR against G is 7.13 for Mega-53 and 6.72 for X-LANCE.

## What this means

- **X-LANCE gives a better tone at equal SNR on the audit mixes,** which matters for the direct
  model because it reads the stem's spectrum.
- **The costs:**
  - 1.78× the CPU time;
  - one bad song-level failure on stage F;
  - a re-separation of the whole build: the pilot's 7,720 examples if reused, the rest's 15,311,
    and V_sep's 1,720, each with a re-render.
- **Before a switch:**
  - X-LANCE's MPS speed (one clip, when the MPS is free);
  - `gtr_mss` alone on the audit mixes, which could make the cost fit: tested under
    [amendment 1](xlance-screen-plan.md#amendment-1-gtr_mss-alone-on-the-audit-mixes-2026-10-21)
    (reviewed), results below.
- The pilot is unchanged and stays on Mega-53.

**Caveats:**
- The audit mixes are training-style mixes: renders with real session backings, unmastered.
- 5 of their 6 bands are high-gain sessions; only Eggy is in scope.
- X-LANCE trained on MoisesDB and RawStems, whose overlap with these sessions is unknown. The
  no-Cambridge points agree with the full set.

## Audit of these results

A fresh-context auditor recomputed the deciding numbers from the per-clip files and checked the
code: confirmed with corrections (run time, the denoise saving, one claim scoped to SNR), all
applied.
