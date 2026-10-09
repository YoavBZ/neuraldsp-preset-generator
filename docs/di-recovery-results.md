# Song to preset by rebuilding the DI: results (clean PR12, Phase 2)

Run as declared in [di-recovery-plan.md](di-recovery-plan.md), with its amendments.
- **Material:** K1's 25 parts in 9 bands, the 21 clean PR12 factory presets plus
  template+R, and four DI-rebuilding networks, one per K3 fold. Each was trained on
  18,843 PR12 renders of other folds' bands for 4 hours. Fold 2 got about half its
  updates after scattered non-finite steps on MPS.
- **Measure:** the average-guitar measure, validated by listening (23 of 24,
  [avg-measure-listening-results.md](avg-measure-listening-results.md)).
- **Verification:** an independent reviewer re-scored all 25 parts with its own code.
  - Every pick and value matched to 1e-9.
  - Each part's rebuilt DI matched a re-run of its own fold's model, to 3e-7.
  - No leakage was found.

## Verdict: not passed

Band median of log(distance / template+R's distance) on half B, under recording / union
bands:

| choosing on half A through… | amp track | closer than template+R | separated stem (18 parts) |
|---|---|---|---|
| the measure's own DI (oracle) | −0.171 / −0.146 | 25 / 24 of 25 | — |
| **the network's rebuilt DI** | **−0.089 / −0.088** (p 0.03 / 0.02) | 20 / 20 | **−0.038 / −0.067** |
| `flatref` / `flatstem`, no training | −0.034 / −0.034 | 16 / 17 | −0.042 / −0.042 |
| K1's constant preset | +0.037 / +0.036 | 13 / 10 | — |

| gate (both band sets) | amp track | stem |
|---|---|---|
| paired against the stand-in: band median ≤ log 0.95 (−0.051) | **fail** (−0.014 / −0.028; p 0.047 / 0.070) | **fail** (−0.005 / −0.010) |
| against template+R: band median ≤ log 0.9 (−0.105) | **fail** | **fail** |
| closer than template+R and the constant on more than half the parts | pass (15 / 16 of 25)* | pass |

\* The constant was K1's, chosen under the true-DI judge. Re-chosen leave-band-out
under the measure, the amp-track count falls to 13 of 25 under recording bands, which
fails.

## What it shows

- **The network helps, but not enough.**
  - On amp tracks its picks are closer than template+R on 20 of 25 parts.
  - It captures 52–60% of the menu oracle's gain.
  - It beats the stand-in in 6 of 9 bands and loses in 1.
  - The gain is concentrated: Atlantis Bound, Eat The Feeder and Eggy. Dom McLennon, 8
    parts in one band, is slightly worse.
- **The ceiling is low here.** The oracle over 21 clean presets is only 15–17%, so the
  10% bar needs about 62% of it.
- **Stems add almost nothing over the stand-in.** On clean, multi-guitar sessions the
  separator's leftovers dominate.

## What follows

1. **Heavier tones.** The set-3 network trains on all three amps. Set 3's development
   test, already declared, is the next decision: settings matter more there than on
   clean PR12, where the player's guitar moves the sound about as much as the preset.
2. **Beyond the menu.** Phase 3's search through the rebuilt DI can exceed the menu's
   oracle. Its positive control comes first.
3. **Stems.** In multi-guitar songs the stem holds every guitar. The test's reference is
   one part's amp track, which a stem of all guitars cannot match.
