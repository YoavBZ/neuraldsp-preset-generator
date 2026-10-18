# Arm A with Mega-53: results (2026-10-17)

Run under the [plan](arm-a-mega53-plan.md) and its amendment 1, on development data only. These are
estimates with intervals, not pass/fail bars. Code: `learn/arm_a_mega53.py` (main at b645155).
Data: `~/ndsp-presets/learn/arm-a-mega53/` (`report-D.json`, `report-F.json`, `x.json`, `logs/`).

Every figure is a held-half log ratio of true-DI judge distances, averaged per part over amps and
directions, then band-weighted, with a 90% band-clustered t interval. Negative means closer to the
record. **H** is arm A's adopted recipe with the htdemucs stem, **M** the same recipe with the
Mega-53 stem, **T** the amp track as the stem (a perfect separator; stage D only), and **S** the
starting preset. Arm X was not added: `decide-x` applied the declared rule to 1d's report before
any render (P1's lo90 −0.256 and P2's −0.166 are both below 0; rule 3).

## Headline

- **The decision row, P_F (fresh draw, full mixes with vocals), M − H: −0.017 [−0.039, +0.004]**,
  12 bands, 8 better and 4 worse. The interval contains 0, so by the plan's declared reading this
  is a tie and **the cheaper separator, htdemucs, stays.**
  - The estimate leans toward Mega-53. Leave-one-band-out runs from −0.023 to −0.010, and
    part-weighted it is −0.022 [−0.040, −0.004].
  - What that lean is worth: a held-half distance about 1.7% smaller, or about 8% of the 0.21
    that separates H from the true-DI search's ceiling (−0.293) on step 3's parts (a stage-F
    estimate set against a stage-D gap; on fresh parts H − S is smaller, so the gap would be
    larger), for about 6× the separation wall-clock time (below). The plan says to build on a negative estimate rather than drop it
    (for example a stronger separator, or a blend). It is not a switch.
- **The development reading, P_D (step 3's 24 parts, instrumental context): −0.008 [−0.024,
  +0.009]**, 14 bands, 7 better and 7 worse. 1c's local-fidelity gain (+0.109) did not show up at
  the song level on the parts where it was measured.
- **The more important finding is about the recipe itself. Arm A's adopted recipe on fresh full
  mixes reads H − S −0.028 [−0.064, +0.008]**, against −0.083 [−0.135, −0.032] on the parts it was
  chosen on. That is about a third of the development figure, and its interval contains 0. The
  data can't say why with any confidence; the candidate explanations are set out
  [below](#the-adopted-recipe-on-fresh-full-mixes-h--s).
- **On step 3's instrumental stems, even a perfect stem gains little over htdemucs:** on stage D,
  T − H is −0.026 [−0.050, −0.002], and T reaches −0.109 [−0.153, −0.066] against S. There, most
  of the distance to the −0.293 ceiling lies in the rebuild and the search, not in the separator.
  This may not carry to full mixes, whose stems are much poorer (see the caveat under
  [stage D](#stage-d-development-24-parts-14-bands-142-directions-instrumental-context)).

## Stage F: the fresh draw (21 parts, 12 bands, 126 directions, full mixes with vocals)

No direction was dropped and no arm fell back to S (H 0, M 0). No search used its activity
fallback.

| Contrast | Estimate [90%] | Bands better / worse | Leave one band out | Part-weighted |
|---|---|---|---|---|
| **P_F: M − H** | **−0.017 [−0.039, +0.004]** | 8 / 4 | −0.023 to −0.010 | −0.022 [−0.040, −0.004] |
| H − S | −0.028 [−0.064, +0.008] | 9 / 3 | −0.037 to −0.012 | −0.017 [−0.046, +0.013] |
| M − S | −0.046 [−0.091, −0.000] | 8 / 4 | −0.053 to −0.023 | −0.039 [−0.072, −0.005] |
| H unshrunk − H | +0.022 [−0.009, +0.054] | 6 / 6 | +0.011 to +0.028 | +0.023 [−0.005, +0.051] |
| M unshrunk − M | +0.035 [+0.008, +0.061] | 4 / 8 | +0.027 to +0.041 | +0.029 [+0.003, +0.056] |

M − S's upper bound is −0.0001: it touches 0.

**Rows** (each row is its own band-weighted estimate; the declared row is "all"):

| Row | Parts / bands | M − H | H − S | M − S |
|---|---|---|---|---|
| **All (declared)** | 21 / 12 | **−0.017 [−0.039, +0.004]** | −0.028 [−0.064, +0.008] | −0.046 [−0.091, −0.000] |
| No high bleed (direction rule; the cell rule gives the same) | 18 / 10 | −0.017 [−0.044, +0.010] | −0.047 [−0.095, +0.001] | −0.064 [−0.122, −0.006] |
| No moderate or high bleed (both rules the same) | 17 / 10 | −0.022 [−0.049, +0.005] | −0.046 [−0.094, +0.003] | −0.068 [−0.123, −0.012] |
| Cambridge only | 17 / 9 | −0.020 [−0.050, +0.010] | −0.034 [−0.082, +0.014] | −0.053 [−0.115, +0.008] |
| Telefunken only | 4 / 3 | −0.010 [−0.029, +0.008] | −0.012 [−0.092, +0.068] | −0.022 [−0.087, +0.043] |
| Without the MUSDB18-train bands | 19 / 10 | −0.025 [−0.048, −0.003] | −0.028 [−0.073, +0.017] | −0.053 [−0.108, +0.001] |
| Without any MUSDB18 song (also Zeno) | 18 / 9 | −0.031 [−0.054, −0.008] | −0.029 [−0.080, +0.021] | −0.060 [−0.120, −0.000] |
| SNR ≥ 1 dB | 2 / 2 | +0.005 [−0.119, +0.129] | −0.021 [−0.041, −0.001] | −0.016 [−0.160, +0.128] |
| F-song: new songs only (descriptive) | 8 / 4 | −0.037 [−0.077, +0.003] | +0.018 [−0.032, +0.069] | −0.018 [−0.051, +0.015] |

- **The MUSDB18 rows lean further toward Mega-53** (−0.025 and −0.031, intervals below 0). For
  the MUSDB18-train row that is the direction the plan anticipated (htdemucs trained on those
  mixes, which flatters H), but it drops 2 bands out of 12 and the rows are descriptive. Dropping
  Zeno as well (MUSDB18 test) guards against a Mega-53 leak instead; Zeno reads M − H +0.025, so
  there is no sign of one.
- **The SNR ≥ 1 dB row is nearly empty:** only 2 of the 21 fresh parts reach 1 dB (Signs ElecGtr3,
  Strangest Places). It can't bridge the two stages as the review hoped.
- **Post-hoc, per part:** M − H falls as Mega-53's SNR gain over htdemucs rises (Spearman −0.43,
  p ≈ 0.05, 21 parts). Where Mega-53's stem is cleaner, M tends to land closer. One unplanned
  correlation, not a test.
- **F-band parts** (listed per part, amendment 1): let's dance elecgtr3 −0.041, elecgtr4 −0.132,
  She's Gone −0.019 (M − H).

**Per amp (M − H):** AC20 −0.030 [−0.048, −0.013], PR12 −0.021 [−0.049, +0.007], SW50R −0.001
[−0.043, +0.041]. **Per class:** clean −0.024 [−0.049, −0.000] (7 bands), crunch −0.007
[−0.059, +0.044] (5 bands).

**Per band** (M − H; H − S; M − S):

| Band | Parts | M − H | H − S | M − S |
|---|---|---|---|---|
| Atlantis Bound | 1 | −0.003 | −0.029 | −0.032 |
| Bernard Purdie Tribute All-Stars | 1 | −0.019 | +0.041 | +0.022 |
| Diesel13 | 2 | −0.043 | −0.040 | −0.082 |
| Dom McLennon | 2 | +0.002 | −0.052 | −0.050 |
| Doom Flamingo | 1 | −0.014 | −0.024 | −0.038 |
| Eat The Feeder | 5 | −0.032 | −0.016 | −0.048 |
| Magician's Nephew | 1 | +0.007 | −0.073 | −0.066 |
| Szymon Skiba | 2 | −0.087 | +0.068 | −0.019 |
| The Travelling Band | 3 | −0.003 | +0.040 | +0.038 |
| Turbosauro | 1 | −0.092 | −0.206 | −0.297 |
| Wall Of Death | 1 | +0.052 | −0.032 | +0.020 |
| Zeno | 1 | +0.025 | −0.018 | +0.007 |

Within a band the parts can disagree widely. The Travelling Band's M − H is −0.003 overall, but
its parts read −0.262 (Passing Ships ElecGtr2), +0.161 (ElecGtr4) and +0.093 (Quicksand ElecGtr2).

## The adopted recipe on fresh full mixes (H − S)

This is the first fresh-draw estimate of the recipe the user adopted on 2026-10-16. The levers'
results said one was needed before shipping.

| | Development (stage D) | Fresh (stage F) |
|---|---|---|
| H − S, all | −0.083 [−0.135, −0.032], 12/14 bands | −0.028 [−0.064, +0.008], 9/12 bands |
| H − S, clean | −0.052 [−0.118, +0.015] (9 bands) | −0.039 [−0.099, +0.022] (7 bands) |
| H − S, crunch | −0.141 [−0.233, −0.048] (5 bands) | −0.014 [−0.063, +0.035] (5 bands) |
| H − S, no high bleed | −0.085 [−0.136, −0.034] | −0.047 [−0.095, +0.001] |
| H unshrunk − S | −0.085 [−0.164, −0.006] (the levers' 3-C′) | −0.006 [−0.051, +0.039] |
| Median htdemucs instrumental SNR | 2.13 dB (18 of 24 parts ≥ 1 dB) | 0.59 dB (2 of 21 ≥ 1 dB) |
| Median SNR of the stem H actually used | 2.13 dB (instrumental) | 0.43 dB (full mix) |

- **The two estimates are not compared by a test** (different parts and contexts; the plan does
  the same for P_F and P_D). Their intervals overlap from −0.064 to −0.032. The levers' corrected
  expectation after selection, about −0.07 [−0.13, −0.01], overlaps the fresh interval from
  −0.064 to −0.01.
- **On the 10 bands both stages share** (post-hoc, descriptive): H − S is −0.097 on stage D's parts
  and −0.045 on stage F's. So the shrinkage is not just a change of bands.
- **Candidate explanations the data can speak to.** None is settled; they are not exclusive.
  1. **Selection and reuse optimism.** The recipe (52 renders, shrink 0.5) was picked as the best
     of several variants on stage D's parts, by step 3 and the levers (the later uses of those
     parts chose nothing about the recipe). Some drop on fresh parts is expected: the levers'
     corrected expectation is about −0.07 [−0.13, −0.01], which overlaps the fresh interval from
     −0.064 to −0.01. Selection optimism alone is compatible with the data.
     - **A freshness gradient points the same way** (post-hoc, descriptive). The 13 fresh parts
       that share a song with a step-3 part (9 bands) read H − S −0.050 [−0.091, −0.009]; the 8
       new-song parts (F-song, 4 bands) read +0.018 [−0.032, +0.069]. The parts least connected
       to step 3 show no gain, which fits the plan's note that same-song parts carry part of the
       selection's luck. It rests on 4 bands.
  2. **Poorer stems in the fresh pool.** The fresh parts' htdemucs stems are much worse: median
     0.59 dB SNR (instrumental; 0.43 dB from the full mix H actually used) against 2.13 dB on
     stage D. Step 3 had selected its parts partly by SNR. On stage D, the 6 parts below 1 dB read
     H − S −0.019 [−0.109, +0.071] (5 bands; post-hoc split), against −0.092 for the 18 above.
     That fits the fresh figure, but it is a post-hoc split of 6 parts. On stage D those 6
     low-SNR parts are also where a perfect stem helps most (T − H −0.091 [−0.177, −0.004] against
     −0.014 above 1 dB), which points the same way. Against it, weakly: stage F's SNR ≥ 1 dB row
     reads H − S −0.021, but on 2 parts.
  3. **Bleed in the truth.** Three fresh parts read high bleed on both halves (Russian Cream
     GTR_1, She's Gone, Strangest Places); their held-half truth is partly other instruments, which
     pulls every ratio toward 0. Stage D has 4 such parts too (First Offering GTR_1, Gym Hours
     GTR_1, Long Way Home, Sculptor's Request GTR_1). Like for like, the no-high-bleed row reads
     −0.085 on stage D and −0.047 [−0.095, +0.001] on stage F: the gap narrows from 0.055 to 0.038,
     so bleed accounts for about a third of it.
  4. **Class mix.** Not the explanation: the fresh pool has more crunch (10 of 21 parts against 5
     of 24), and crunch was where stage D gained most, yet fresh crunch reads only −0.014. The
     drop is concentrated in crunch (−0.141 to −0.014); clean moves little (−0.052 to −0.039).
     Stage D's crunch figure rests on 5 parts, of which colour-me-red elecgtr01 (−0.30) and Today's
     The Day ElecGtr10 (−0.16) are the largest; without colour-me-red it is still −0.101 [−0.151,
     −0.051] (4 bands), far from fresh crunch's −0.014.
  5. **Vocals.** Weak evidence either way. The vocals cost htdemucs little SNR on these parts: its
     full-mix stems read on average 0.08 dB below the label table's instrumental stems (worst
     −0.31 dB). But C′ never saw stems from vocal mixes, and residual vocals could bias the
     objective without moving the SNR much. The only fresh parts without vocals (let's dance ×2,
     magilla elecgtr1) are too few to compare.
  6. **S may sit closer to the record on the fresh parts.** Not supported: the mean log S distance
     is 1.53 on stage D's directions and 1.55 on stage F's.
- **Shrinking looks more useful on fresh data.** On stage D the unshrunk best and the shrunk
  output tie for every arm (H −0.002, M +0.002, T −0.003). On stage F the unshrunk best reads
  worse: M's interval lies above 0 (+0.035 [+0.008, +0.061]), H's contains it (+0.022 [−0.009,
  +0.054]). The change from stage D is not tested. Without the shrink, H's fresh estimate against
  S is −0.006 [−0.051, +0.039]. This fits a search that overfits a noisier objective on poorer
  stems, but the data doesn't test that.
- **Reading, hedged.** On fresh full mixes the adopted recipe's gain over S is smaller than the
  development figure suggested. The declared row, −0.028 [−0.064, +0.008], is compatible with
  anything from no gain to about −0.06; the descriptive rows run from +0.018 (F-song) to −0.047
  (no high bleed). The development −0.083 lies outside the fresh interval. It is the current best
  estimate of what the recipe does on a product-like input, with 12 bands behind it.

## Stage D: development (24 parts, 14 bands, 142 directions, instrumental context)

No direction was dropped; no arm fell back to S (H 0, M 0, T 0); no M or T search used its
activity fallback. H is the stored 3-C′ search shrunk halfway, so H − S reproduces the levers'
figure exactly.

| Contrast | Estimate [90%] | Bands better / worse | Leave one band out | Part-weighted |
|---|---|---|---|---|
| **P_D: M − H** | **−0.008 [−0.024, +0.009]** | 7 / 7 | −0.011 to −0.003 | −0.017 [−0.035, −0.000] |
| H − S | −0.083 [−0.135, −0.032] | 12 / 2 | −0.092 to −0.065 | −0.055 [−0.095, −0.015] |
| M − S | −0.091 [−0.137, −0.046] | 13 / 1 | −0.100 to −0.075 | −0.073 [−0.109, −0.036] |
| T − H | −0.026 [−0.050, −0.002] | 10 / 4 | −0.031 to −0.019 | −0.039 [−0.066, −0.013] |
| T − S | −0.109 [−0.153, −0.066] | 13 / 1 | −0.122 to −0.096 | −0.095 [−0.124, −0.066] |
| M − T | +0.018 [+0.002, +0.034] | 4 / 10 | +0.015 to +0.023 | +0.022 [−0.004, +0.047] |
| H unshrunk − H | −0.002 [−0.038, +0.035] | 9 / 5 | −0.015 to +0.007 | +0.004 [−0.019, +0.027] |
| M unshrunk − M | +0.002 [−0.027, +0.030] | 7 / 7 | −0.006 to +0.010 | +0.008 [−0.013, +0.029] |
| T unshrunk − T | −0.003 [−0.030, +0.025] | 9 / 5 | −0.014 to +0.005 | +0.000 [−0.018, +0.018] |

**M's share of T's gain**, (M − H) / (T − H): **0.30, Fieller 90% [−2.90, +0.79]** (bounded, 13
df; leave-one-band-out 0.11 to 0.39). The interval is wide enough to say little. Of the other
rows, only "without the MUSDB18-train bands" (0.38 [−31.5, +1.21]) and "without any MUSDB18 song"
(0.38 [−0.65, +0.84]) are bounded; the rest are unbounded (no high bleed 0.37, no moderate or
high 0.65 by the cell rule (0.64 by the direction rule), SNR ≥ 1 dB 0.61 and Telefunken only
0.74: the whole line; Cambridge only 0.12: two rays).

**Rows:**

| Row | Parts / bands | M − H | T − H | H − S |
|---|---|---|---|---|
| **All (declared)** | 24 / 14 | **−0.008 [−0.024, +0.009]** | −0.026 [−0.050, −0.002] | −0.083 [−0.135, −0.032] |
| No high bleed (direction and cell rules the same) | 20 / 14 | −0.008 [−0.024, +0.009] | −0.021 [−0.045, +0.002] | −0.085 [−0.136, −0.034] |
| No moderate or high, cell rule | 14 / 12 | −0.013 [−0.036, +0.011] | −0.019 [−0.047, +0.008] | −0.098 [−0.157, −0.038] |
| No moderate or high, direction rule | 16 / 13 | −0.011 [−0.032, +0.010] | −0.017 [−0.043, +0.009] | −0.094 [−0.149, −0.040] |
| Cambridge only | 13 / 11 | −0.003 [−0.020, +0.015] | −0.023 [−0.053, +0.006] | −0.098 [−0.163, −0.032] |
| Telefunken only | 11 / 3 | −0.026 [−0.099, +0.048] | −0.035 [−0.105, +0.036] | −0.030 [−0.065, +0.004] |
| Without the MUSDB18-train bands | 21 / 12 | −0.011 [−0.029, +0.007] | −0.028 [−0.057, −0.000] | −0.091 [−0.152, −0.031] |
| Without any MUSDB18 song | 20 / 11 | −0.013 [−0.032, +0.006] | −0.035 [−0.064, −0.006] | −0.101 [−0.165, −0.037] |
| SNR ≥ 1 dB | 18 / 11 | −0.009 [−0.031, +0.014] | −0.014 [−0.033, +0.005] | −0.092 [−0.155, −0.029] |

**Per amp (M − H):** AC20 +0.004, PR12 −0.011, SW50R −0.017 (all intervals contain 0). **Per
class:** clean −0.015 [−0.037, +0.007] (9 bands), crunch +0.006 [−0.024, +0.035] (5 bands).

**Per band** (M − H; T − H; H − S):

| Band | Parts | M − H | T − H | H − S |
|---|---|---|---|---|
| Adam Buckley | 1 | −0.014 | −0.061 | −0.012 |
| Atlantis Bound | 2 | −0.013 | −0.019 | −0.012 |
| Diesel13 | 1 | +0.026 | +0.042 | −0.301 |
| Dom McLennon | 6 | −0.020 | −0.081 | −0.008 |
| Doom Flamingo | 2 | +0.015 | +0.000 | −0.034 |
| Eat The Feeder | 1 | +0.000 | −0.046 | −0.155 |
| Eggy | 3 | −0.072 | −0.023 | −0.049 |
| Magician's Nephew | 1 | +0.012 | −0.017 | −0.114 |
| Starnes And Shah | 1 | −0.044 | −0.104 | −0.074 |
| The Travelling Band | 2 | −0.067 | −0.113 | +0.027 |
| Timo And The Timezone | 1 | −0.013 | −0.023 | −0.059 |
| Turbosauro | 1 | +0.033 | +0.044 | −0.328 |
| Wall Of Death | 1 | +0.034 | −0.002 | −0.060 |
| Zeno | 1 | +0.015 | +0.040 | +0.012 |

**What stage D's T says.** A perfect stem, through the same rebuild, search and shrink, gains
−0.026 over htdemucs at the song level, and M gets about 0.3 of that (with an interval that says
little). So:
- The local-fidelity gains (1c's Mega-53 +0.109, 1b's amp track +0.252 over the current stem) translate
  into small song-level gains. The plan's null-anchor reading applies in its weak form: T does beat
  H, but by little, so on these instrumental stems the separator is not the main limit on arm A.
- **Caveat: this may not carry to full mixes.** On the 6 stage-D parts whose stem is below 1 dB
  SNR, T − H is −0.091 [−0.177, −0.004], against −0.014 on the 18 above (post-hoc split). Fresh
  full-mix stems are almost all below 1 dB (htdemucs median 0.43 dB; 2 of 21 parts at or above
  1 dB), and Mega-53's stem is only a median +0.13 dB better there. So M − H says little about
  what a much better separator would do on product inputs, and the separator may matter more
  there than stage D's T suggests.
- T reaches −0.109 against S, against −0.293 for the true-DI search to its stop on the same
  directions. **About 0.18 of the gap remains with a perfect stem**, so it lies in the rebuild
  (C′'s local bias near S, the levers' finding) and the search (52 renders and shrink, against the
  ceiling's search to a stop). This plan doesn't separate those two.

## Plumbing checks (all passed)

- **Held-out data, fail closed:** `check-inputs` ran the held-out assertion over all 21 stage-F
  sessions (both catalogues) before any stage-F render and recorded no problem
  (`F/inputs.json`: ok, no problems). The pool rule, C′ leak assertions, context, separation,
  identity and paired-rebuild checks are in the same record, all ok. Stage D's inputs: ok.
- **The S judge against the label table** (stage F, every half, every part and amp): largest
  deviation 1.3e-4 in log, tolerance 0.005.
- **M's and T's first evaluation is S:** the search-half objective matched 1c's and 1b's stored S
  scores within 9.7e-5 (M) and 9.4e-5 (T), tolerance 0.005.
- **Repeat check:** 6 directions drawn by seed 20261034; H's stored shrunk setting re-rendered
  through the measure DI reproduced its stored held-half judge within 1.3e-4 (tolerance 0.005).
- **Identity check** (amendment 1, item 7): the generalised rebuild reproduced step 3's stored
  htdemucs rebuilds within 1.8e-7 and 1c's Mega-53 rebuilds exactly (tolerance 1e-6), 24 parts
  each.
- **Contexts:** 21 full-mix contexts; every crop slice equals the crop folder's `mix.wav` exactly.
- **Separation:** every Mega-53 crop within ±1 sample of the htdemucs crop (tolerance ±3); 480,000
  samples each; no part failed. **Rebuilds:** every H and M rebuild at −22.9 LUFS, paired checks ok.
- **Fixed sets complete:** 142 and 126 directions, every arm scored on every one, nothing dropped.

## Separation timings and the stems (stage F, CPU)

| | htdemucs_6s (2 threads) | Mega-53 (4 threads, pruned head) |
|---|---|---|
| Per 30-s context | 13.4–16.8 s (median 14.1) | 89.5–92.0 s (median 89.8) |
| 21 contexts | 303 s | 1,888 s |
| Peak memory | — | 7.2 GB |

- **Mega-53 takes about 6.4× htdemucs's wall-clock time** per context (median; 6.2× in total),
  a little more than the plan's 5–6×: htdemucs ran faster than the plan assumed (15–28 s). The
  thread counts differ (4 against 2), so in thread-seconds it is about 12.7×.
- **Stem SNR against the amp track:** Mega-53 higher on 18 of 21 parts, median +0.13 dB (mean
  +0.63, driven by She's Gone +5.1 and Strangest Places +3.7). Both are low on this pool: medians
  0.70 dB (Mega-53) and 0.43 dB (htdemucs, full mix).
- **Mega-53 is darker:** its level above 6 kHz is a median 12.3 dB below htdemucs's.

## Renders, hours and power

- **Renders:** stage D 15,990 (cap 16,500) and stage F 14,112 (cap 14,600), each equal to the
  plan's table; **30,102 in all.** The running total is about 231k (about 201k before this test).
- **Hours:** 12:03 to 17:11, about 5.1 h against the plan's 4.8 h. Lane A (contexts, separations,
  rebuilds, checks) took 40 minutes; stage D 3.0 h; stage F 2.1 h.
- **Power, as declared:** at a band SD of 0.06 the plan expected an 80%-power detectable effect of
  about 0.046 on P_F (and 0.042 on P_D). The observed band SDs were lower (P_F 0.042, P_D 0.034),
  which puts the detectable effect at about 0.032 (P_F) and 0.024 (P_D). The 90% half-widths came
  out at 0.022 and 0.016. The plan's rough prior was about −0.03; the readouts (−0.017 and −0.008)
  are smaller.

## What it teaches

- **On step 3's instrumental stems, the separator is not what holds arm A back.** Swapping
  htdemucs for Mega-53 gives a small lean on fresh mixes and nothing on the development parts. A
  perfect stem gains only −0.026 on the development parts; the larger losses there are downstream,
  in the rebuild's local bias and the search. On full-mix stems, which are much poorer, a perfect
  stem's gain is not measured (no song gives an amp track), and the low-SNR stage-D parts hint it
  could be larger.
- **The adopted recipe's gain over S on fresh full mixes is smaller than its development figure:**
  −0.028 [−0.064, +0.008], and the shrink looks more useful there. Selection and reuse optimism
  (with the freshness gradient), poorer stems in the fresh pool and bleed in the truth are all
  candidates; none is settled. This is the
  figure to carry forward for product-like inputs until a larger fresh draw sharpens it.
- **The rebuild-gap study** ([results](rebuild-gap-results.md)) has since run; it targets where the data says the gap is.

Audited 2026-10-17 by an independent agent, which recomputed every figure from the raw
per-direction records with its own scripts (all match; its units equal the report's exactly;
pairing, direction sets, the pool, renders, hours, the held-out check before the first stage-F
render, and the identity, S-judge, repeat, separation and rebuild checks verified; `decide-x`
applied correctly); changes: the crunch explanation now names the right parts (colour-me-red and
Today's The Day) and gives crunch without colour-me-red; selection optimism is no longer
dismissed (the levers' −0.07 [−0.13, −0.01] overlaps the fresh interval); the freshness gradient
(same-song −0.050 against new-song +0.018) was added; bleed is compared like for like (about a
third of the gap); the hedged reading gives the interval rather than two rows' estimates; the
"separator is not the limit" reading is restricted to instrumental stems, with the low-SNR caveat;
the CPU ratio is stated as wall-clock (about 12.7× in thread-seconds); the shrinkage wording no
longer implies a test; leave-one-band-out columns were added; and several smaller wording fixes
(the Zeno row's purpose, the full-mix SNR, the stage-D gap behind the 8%, a post-hoc SNR-gain
correlation).

## Amendment 2: the oracle-DI arm on stage F (2026-10-18)

**Question:** in the product setting (a separated full-mix stem, no DI), does a *perfect* rebuild
help arm A much? XO is stage F's H with one change: the search renders through the part's true
measure DI instead of C′'s rebuild of the htdemucs stem. It still scores against that stem, at the
judge's lag (the stems sit on `reference.wav` within ±1 sample). The seed, recipe, shrink, fallback
and judge are H's. Code `learn/oracle_di_arm.py`; data `~/ndsp-presets/learn/arm-a-mega53/F-oracle/`
(`report.json`).

| Contrast | All (declared), 12 bands | No high bleed (direction rule), 10 bands | F-song, new songs only (descriptive), 4 bands |
|---|---|---|---|
| **XO − S** | **+0.012 [−0.088, +0.112]** | +0.011 [−0.108, +0.129] | −0.027 [−0.162, +0.109] |
| **XO − H** | **+0.040 [−0.043, +0.123]** | +0.057 [−0.042, +0.157] | −0.045 [−0.149, +0.059] |
| H − S (stored, for reference) | −0.028 [−0.064, +0.008] | −0.047 [−0.095, +0.001] | +0.018 [−0.032, +0.069] |
| XO unshrunk − XO | +0.047 [−0.003, +0.097] | +0.041 [−0.023, +0.105] | +0.024 [−0.029, +0.077] |

- **Bands:** 5 of 12 lean negative on each primary. Leaving one band out gives −0.008 to +0.060
  (XO − S) and +0.009 to +0.077 (XO − H). Part-weighted: +0.023 [−0.077, +0.124] and +0.040
  [−0.052, +0.132]. No fallbacks; no activity fallbacks.
- **Share of the true-DI ceiling gap:** XO − S is −0.04 of K_S's −0.293 (that is, none). H's is
  +0.10. The −0.293 comes from other parts, a target with no other instruments in it and a longer
  search, so it is only a scale.
- **Why a perfect DI doesn't help here.** The objective is the problem. Measured against the
  full-mix stem, S rendered through the true DI scores a median 6.40 on the search half; through
  C′'s rebuild it scores 4.10. The rebuild comes from the stem, so it carries the stem's leftover
  mix, and the objective rewards that. Through the true DI the search chases what is left of the
  mix in the stem (median SNR 0.43 dB), not the guitar. Per class, XO − H is +0.086 on clean and
  −0.024 on crunch.
- **Reading, hedged.** Both intervals contain 0 and are wide (band SD about 0.15). A perfect
  rebuild gives arm A no measurable gain in the product setting. Point estimates lean worse than H
  (+0.040) and than S (+0.012); only the F-song row, on 4 bands, leans the other way. What limits
  arm A on full mixes is the stem objective, not the rebuild. Better rebuilds aren't worth building
  for arm A until the objective (separation quality, or an objective that tolerates bleed) gets
  better.
- **Renders:** 6,994 counted (63 priming renders, plus 1 more after a pause-and-resume; 126 × 55),
  plus up to 54 uncounted from the direction in flight at the pause. At most 7,048, against a
  declared 6,993 and a cap of 7,100. One process beside part C's two, about 3 h.
