# Separator screen: results (DI-recovery experiment 1, 2026-10-16)

Run under the [plan](separator-screen-plan.md) and its environment notes. The run:
- **Cells:** 10, from the 5 set-3 check parts × PR12 and SW50R. Every cell is informative.
- **Renders:** 136.
- **Separation:** Mega-53 on the CPU, alone. Its first two attempts were stopped by the swap guard while arm B trained; the third passed, with a peak RSS of 17.1 GB.
- **Data:** `~/ndsp-presets/learn/separator-screen/`.
- **Independent audit:** every margin was recomputed from `scores/`, and the integrity checks were re-derived.

## Integrity

- **The fakes match the control's:** their line-up errors are at most 6e-8, their loudness equals the reference to 0.001 LU, and the control repeat agrees to 1e-3.
- **Pruned Mega-53:** identical to the full model (maximum difference 0.0).
- **htdemucs's re-separation:** equals the stored crops exactly.
- **Rebuilds:** fold-correct, with DONE markers and lags within ±1. The leak assertion passes, trivially: no set-3 band is in any C′ cache.
- **Repeat render:** within 3e-7.

## The screen

The margin m_sep is taken through the **true** measure DI, against each stem, on the full window.

| Row | m_sep > 0 | Mean m_sep | Real-song coherence (1–3 kHz) |
|---|---|---|---|
| The clean fake (reference) | 10 / 10 | 0.221 | — |
| htdemucs_6s | 9 / 10 | 0.113 | 0.131 |
| Mega-53 | 10 / 10 | 0.110 | 0.154 |
| Blend | 7 / 8 (2 stopped) | — | 0.143 on its 4 parts |

- **The reading: separation isn't what breaks the search.** htdemucs inverts 1 of 10 (get-out-of-bed PR12, −0.024), so the "≤ 1" branch applies. The reading holds under every fragility check.
  - Separation roughly halves the gap between the right and wrong settings: htdemucs keeps a median 63% of the clean margin. The loss is larger where other guitars are loud (0.074 against 0.140).
  - Removing the other guitars barely moves the mean (htdemucs −0.008, Mega-53 +0.011). Here they don't look like the bottleneck.
- **Mega-53 "advances" by the declared rule, but on one cell.** It rescues get-out-of-bed PR12 (+0.023). Per cell it is better on 5 of 10, with mean −0.003 against htdemucs. Leaving out get-out-of-bed undoes the advance.
  - So it earns the full switching test, but this is **no evidence that it separates better.** Its real-song coherence is higher on all 5 parts (+0.002 to +0.065), which is consistent with the 2026-10-08 test's small gain.
- **The blend does not advance under rule 1.** Even with its two stopped magilla cells counted as positive, it would match htdemucs, not beat it.
  - The report labels those cells "flips" and "coherence fails". The plan's wording only covers a stop for htdemucs, so that labelling is harsher than the plan. The stops come from a ±1-sample relative lag, probably estimator jitter. Over its 4 parts, its coherence (0.143) would pass.
- **m_both, through C′'s rebuild of each stem:**
  - from the clean fake: 7 of 10 positive, mean 0.127;
  - through htdemucs: 6 of 10, mean 0.034;
  - through Mega-53: 7 of 10, mean 0.008.

  So the rebuild is the bigger break. Separation shrinks what is left, and the two separators can't be told apart through C′.

## What it decides

- **The DI-recovery effort stays on the rebuild** (experiment 4).
- **Separation is a second-order problem here:** it halves the margin but rarely flips it.
- **Mega-53's switching test** (the merged report's re-test design) is optional and low priority. Its edge rests on one cell, and the margin is only a weak screen (step A, 14/18).
- **Small code fixes:**
  - a stopped cell in an eligible row should read "not judged", not "flip";
  - leave-one-part-out coherence should allow a missing part.

## Stated limits

- 5 parts in 5 bands, so there are no band intervals (a dated deviation, as declared). The 5 parts are being used repeatedly.
- The margin is a weak screen, not search success.
- **The "other mask" check carries almost no information:** the measure DI and the stem select the same frames in 179 of 192 windows.
- **The Mega-53 SNR sanity check** (1.4–7.1 dB per part) uses a gain-fitted SNR on 5 parts. It may not be comparable with the 2026-10-08 median of 1.48 dB.
