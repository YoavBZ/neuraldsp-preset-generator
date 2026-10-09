# Song to preset by rebuilding the DI: results on heavier tones (set 3, development)

> **Review 2026-10-09** ([codex-continuation-review.md](codex-continuation-review.md)): the development edge over 'a constant' used a leave-band-out constant chosen after the run. Against the constant later declared for the held-out test (median raw distance over all development parts), SW50R is −0.023 (p 0.09–0.11, closer on 12 of 32) and PR12 is about 0. The held-out test failed consistently.


**Current status, 2026-10-08:** this is the historical development result, with an
ambiguous constant definition. The subsequent [reserved confirmation](set3-heldout-confirmation-results.md)
fixed that definition before execution and failed on both SW50R and PR12. The
development gains below do not override that decision. The old "What follows"
section is superseded by [ROADMAP.md](ROADMAP.md) and the
[development diagnostic](set3-development-diagnostic-plan.md); no constant preset
has been validated for automatic shipping from song inputs.

Run as declared in [di-recovery-plan.md](di-recovery-plan.md), "Phase 2 on set 3"
(2026-10-08).
- **Material:** 33 development parts in 11 bands, mostly crunch to high gain.
- **Menus:** three amp menus (factory presets plus template+R).
- **Network:** one DI-rebuilding network trained on all three amps. It never heard a
  set-3 DI or K3 fold 2.
- **Measure:** the average-guitar measure on half B.
- **Verification:** an independent reviewer re-scored 13 parts across all 11 bands
  exactly. It confirmed that the network never heard a set-3 band and that no held-out
  part was touched.

## Against template+R and the no-training stand-in: large, clear gains

Band median of log(distance / template+R's), under recording / union bands (parts
closer than template+R):

| menu | **network, amp track** | network, stem (12 parts) | `flatref` | measure oracle |
|---|---|---|---|---|
| PR12 | **−0.415 / −0.415** (26/32) | −0.182 / −0.124 (10/12) | +0.053 | −0.605 / −0.589 |
| SW50R | **−0.703 / −0.703** (29–30/32) | −0.586 / −0.477 (12/12) | −0.049 / −0.068 | −0.745 / −0.737 |
| AC20 | **−0.174 / −0.178** (27/32) | −0.167 / −0.163 (10/12) | +0.038 | −0.452 / −0.435 |
| best of 3 amps | **−0.303 / −0.242** (27–30/32) | −0.268 / −0.278 | +0.046 | −0.672 / −0.654 |

- **Against the stand-in, paired:** the network beats `flatref` on every menu (−0.22 to
  −0.65, p ≤ 0.004).
- **Stems:** `netstem` beats `flatstem` (p ≤ 0.08).
- **Capture:** on SW50R the network reaches 94% of the oracle's gain.
- **One refused part:** the judge refused Colour Me Red ElecGtr03 through the rebuilt DI
  (51% pauses). It is counted as a loss below.

## Against a constant preset: the deciding comparison, and not robust

On distorted material template+R (a clean template) is a strawman. Choosing a
well-driven preset is most of the gain: a leave-band-out constant preset alone reaches
−0.29 (AC20) to −0.58 (SW50R) against template+R.

The declared gate requires closer than template+R **and** the constant on more than
half the parts, band-weighted. **The constant's definition for set 3 was not declared
before the run.** The reviewer computed three reasonable definitions. Figures are the
band-weighted share of parts closer than both, refusal counted as a loss, recording /
union bands:

| constant chosen by… | PR12 | SW50R | AC20 |
|---|---|---|---|
| median half-A log ratio to template+R on other bands' parts (chosen after the run) | 0.59 / 0.59 | 0.76 / 0.68 | 0.39 / 0.37 |
| median raw half-A distance (K1's precedent, `kill_tests.py`) | 0.48 / 0.45 | 0.64 / 0.50 | 0.39 / 0.40 |
| band medians | 0.48 / 0.42 | 0.36 / 0.36 | 0.39 / 0.37 |

| verdict | |
|---|---|
| **SW50R** | **conditional pass.** It beats the constant under two of three definitions. Paired it is −0.17 to −0.20 (p 0.001–0.02), steady when each band is left out in turn. It fails under the band-median choice (−0.023, p 0.11). |
| **PR12** | **not passed.** It beats the constant only under the definition chosen after the run (−0.196, p 0.024). Under K1's precedent it is −0.096, p 0.35. It loses on all 6 Eat The Feeder parts. |
| **AC20** | **failed.** It loses to the constant under every definition. This fits the network rebuilding AC20 worst (waveform correlation 0.48, against 0.65–0.72). |
| **best of 3 amps** | **not passed.** It does not beat the constant paired under any definition (p 0.13–0.55). |

## What it shows

- **Rebuilding the DI clearly works on heavier tones,** where the settings matter more
  than the guitar. It beats the clean default and the training-free stand-in by large
  margins, from amp tracks and from stems.
- **Most of the gain over a clean default comes from simply being driven.** A good
  constant preset per amp is a strong baseline. Beating it is the real bar, and the
  network clears it robustly only on SW50R.
- **Clean PR12 and heavy PR12 tell a consistent story:** the network helps, partly.

## What follows

1. **Declare the constant now:** K1's precedent, median raw half-A distance,
   leave-band-out. Then run the one-time confirmation on set 3's **held-out** bands (27
   parts, 6 bands) for SW50R and PR12. That spends the held-out set, so it is the
   user's call.
2. **Ship the constant preset as a baseline.** A per-amp "typical driven preset" is a
   cheap, real improvement on distorted songs.
3. **Improve the DI network where it is weakest:** AC20, and longer multi-amp training.
4. **The search beyond the menu,** which can exceed a single constant per song.
