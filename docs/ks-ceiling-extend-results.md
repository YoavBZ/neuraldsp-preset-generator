# The knob-search ceiling, searched to a stop: results (2026-10-17)

Run under the [plan](ks-ceiling-extend-plan.md) and its amendment 1 (whose list of what is
reported governs). Development data, the true DI (the measure DI), no model. The search is
"K_S plus iterated 150-evaluation rounds", continued from each stored K_S final.

- **Scope:** 24 scored parts (19 clean, 5 crunch), 14 bands, 3 amps, both directions.
- **Data:** `~/ndsp-presets/learn/ks-ceiling-extend/`:
  - `report.json` (from `learn.ks_extend report`), `check.json` (the zero-render checks);
  - `cells/<part>/<amp>/<half>.json`, one per run direction.
- **Where the numbers come from:** most are in `report.json` or `check.json`. Those marked
  *(recomputed)* were computed here from the stored direction files and `report.json`'s inputs,
  with the module's own functions (`estimate_rows`, `song_readout.bw`), zero renders.

All figures are held-half log ratios, per part, then band-weighted with 90% band-clustered
intervals. Negative means closer to the record. "Bands better" counts bands whose mean is below 0.

## The headline

- **The ceiling at the stop: −0.293 [−0.378, −0.207]** against S, better in 13 of 14 bands;
  h = 0.009 beside it (the search-half error from the 72 directions not run, 90%).
  - At 150 renders (the stored K_S) it was −0.269 [−0.341, −0.196], 14 of 14.
  - Leaving out each band in turn: −0.315 to −0.258.
- **The extension's own gain, paired: −0.024 [−0.042, −0.006]**, 12 of 14 bands better.
  - Leaving out each band in turn: −0.027 to −0.016.
  - On the search half: −0.031 [−0.047, −0.015], 14 of 14.
- **Renders:** 17,550 extra renders over 72 directions, plus 72 warm-ups.
- **The 72 run directions alone, at the stop:** −0.280 [−0.360, −0.200] against S, 14 of 14
  bands (no imputation; these are a different set from the estimate above, so not comparable
  one to one).
- **Converged by the declared rule:** all 72 run directions stopped flat. **Stopped by the 600
  guard: 0 (0%).** But two reached 600 extra renders, where the flat rule and the guard both held;
  the rule records flat first (see Renders).
- **By stop reason:** every direction stopped flat, so the extension gains above are the flat
  figures; the guard and other groups are empty.
- **It is still a lower bound.** The rule says each search's own curve went flat, not that the
  best settings were found (see Limits).

## The ceiling curve

All 24 parts, 14 bands. A direction that has stopped carries its final value forward.

| Total renders | Against S | Bands better | Clean (bands better of 9) | Crunch (of 5) | Still running (of 72) |
|---|---|---|---|---|---|
| 150 (stored K_S) | −0.269 [−0.341, −0.196] | 14 / 14 | −0.260 (9) | −0.284 (5) | 72 |
| 200 | −0.276 [−0.354, −0.198] | 13 / 14 | −0.270 (8) | −0.287 (5) | 72 |
| 250 | −0.281 [−0.362, −0.199] | 14 / 14 | −0.278 (9) | −0.285 (5) | 72 |
| 300 | −0.290 [−0.375, −0.204] | 13 / 14 | −0.290 (8) | −0.288 (5) | 44 |
| 350 | −0.291 [−0.377, −0.205] | 13 / 14 | −0.293 (8) | −0.288 (5) | 31 |
| 400 | −0.292 [−0.378, −0.206] | 13 / 14 | −0.294 (8) | −0.288 (5) | 24 |
| 450 | −0.293 [−0.378, −0.207] | 13 / 14 | −0.295 (8) | −0.289 (5) | 14 |
| 500–750 | −0.293 [−0.378, −0.207] | 13 / 14 | −0.295 (8) | −0.289 (5) | 8, 6, 4, 2, 2, 0 |
| **at the stop** | **−0.293 [−0.378, −0.207]** | **13 / 14** | **−0.295 (8)** | **−0.289 (5)** | 0 |

Clean and crunch intervals are in the next section (at 150 and at the stop) and in `report.json`
for every point.

- **Most of the gain comes in the first 150 extra renders** (to 300 total): −0.021 of the
  −0.024. After 450 the estimate doesn't move at three decimals.
- **The band that isn't better is Zeno** (clean): −0.011 at 150, +0.001 at the stop. It was
  the band closest to S already *(recomputed)*.

## Clean and crunch

| | At 150 | At the stop | Bands better (stop) | Leave one band out (stop) |
|---|---|---|---|---|
| Clean (19 parts, 9 bands) | −0.260 [−0.369, −0.151] | −0.295 [−0.427, −0.163] | 8 / 9 | −0.332 to −0.240 |
| Crunch (5 parts, 5 bands; descriptive) | −0.284 [−0.397, −0.170] | −0.289 [−0.407, −0.170] | 5 / 5 | −0.333 to −0.256 |

The extension's gain by class *(recomputed)*:
- **Clean:** held −0.035 [−0.061, −0.008], 8 of 9 bands better; search half −0.038 [−0.062,
  −0.014].
- **Crunch:** held −0.005 [−0.013, +0.003], 4 of 5 (Magician's Nephew +0.0001, a tie); search
  half −0.019 [−0.037, −0.000].
- So the extra search moved clean more than crunch (−0.035 against −0.005 held; crunch is 5
  bands and descriptive). On crunch the stored K_S was already close to where this search stops.

## Where the gain sits

Per band, at the stop against 150 *(recomputed)*:
- **Two clean bands carry most of it:** Turbosauro −0.134 (−0.604 to −0.739) and The Travelling
  Band −0.066.
- **Then:** Timo And The Timezone −0.032, Eggy and Atlantis Bound −0.027 each, Diesel13 −0.020,
  Adam Buckley −0.020.
- **The rest are within ±0.012:** Doom Flamingo, Dom McLennon, Eat The Feeder, Wall Of Death,
  Starnes And Shah, Magician's Nephew and Zeno (+0.012).

Per direction, the held change at the stop against 150 *(recomputed)*:
- 38 of 72 better by more than 0.005, 26 within ±0.005, 8 worse by more than 0.005;
- median −0.006, largest gain −0.396 (magilla elecgtr1dt, SW50R, search half B; Turbosauro),
  largest loss +0.040 (Signs ElecGtr2, SW50R, search half A; Zeno).

The held gain (−0.024) is smaller than the search-half gain (−0.031). Some of what the search
finds is specific to the half it searched on.

## The batch rule

| After batch | Directions run | h (search half) | Decision |
|---|---|---|---|
| 1 | 24 | — (needs 2 batches) | continue |
| 2 | 48 | 0.0154 | continue |
| 3 | 72 | **0.0090** | **stop** (h ≤ 0.01) |

- **Applied as declared:** h was computed only from finished directions' search-half gains. The
  held half was not read. Recomputed here independently from the stored direction files: the
  same h at both steps *(recomputed: pooled within-part variance 0.0047 on 24 df, then 0.0032 on
  48 df)*.
- **So 72 of the 144 directions ran (3 of 6 batches).** The other 72 enter at their stored 150
  value plus their part's mean held gain from its run directions (amendment 1's estimate). Every
  part has 3 run directions, one per batch, so no part was left out.
- **What h covers:** the error from the directions not yet run, on the search half, at 90%. It
  is not the band-clustered interval above, which is much wider (its width is the spread between
  bands).

## Renders

- **Extra renders per direction:** min 150, quartiles 150 / 200 / 300, median 200, max 600;
  total **17,550**. Plus 72 warm-ups (one recorded per direction). Settings already rendered (by the
  stored search or earlier in the continuation) were looked up, not rendered, and aren't counted.
- **By batch** *(recomputed)*: 6,550, 6,050 and 4,950. **By class:** clean 13,950 over 57
  directions, crunch 3,600 over 15 (median 200 each).
- **Stops by reason:** flat 72. Guard 0, exhausted 0, round limit 0. At most 5 rounds per
  direction.
- **Two directions reached 600 extra renders** and read flat at that same check: Passing Ships
  ElecGtr6 (SW50R, half B) and Bloomlight (SW50R, half A). The rule reports flat first when both
  hold. Each gained less than 0.005 on the search half over its last 150 renders (0.001 and
  0.002) *(recomputed)*. So they converged by the rule, but only just inside the guard.
- **Against the plan's expectation** (2 to 4 batches, about 7,200 to 57,600): 3 batches, 17,550.
- **Repeat check:** the largest repeat deviation was 1.3e-4 (log), against the 0.005 limit. No
  direction was marked `repeat_failed`.
- **Refused held halves:** none. No direction was dropped, at any reported point.
- **Replays (`check.json`):** all 144 stored K_S searches replay to their stored finals with zero
  renders, 0 mismatches.
- **Pauses:** the operator held the first launch before it started and paused the run twice
  after (for the local-objective experiments); the fourth launch ended with no note. After its
  first start the run was restarted three times (`launch3.log` to `launch5.log`), each time resuming from the
  directions' saved logs (zero renders, setting keys checked). Two things this leaves out of the
  counts: a direction resumed after a restart warmed up again, but its warm-up flag is a yes/no,
  so the 72 can undercount by at most 9 (3 processes × 3 restarts); and renders made after a
  direction's last 50-render save were lost and rendered again (at most 49 per interrupted
  direction). The 17,550 counts each direction's own log, so neither changes any figure. The
  `run-*.log` files cover only the last launch; the direction files are the record.

## Step 3's view (142 directions)

The same estimate without step 3's two dropped directions (Gym Hours GTR 1 and Sculptor's
Request GTR 1, PR12):
- **At 150:** −0.269 [−0.342, −0.196], 14 of 14. This reproduces step 3's K_S.
- **At the stop:** −0.293 [−0.379, −0.207], 13 of 14; leaving out each band −0.316 to −0.259.
- **Clean / crunch at the stop** *(recomputed)*: −0.295 [−0.427, −0.163] and −0.289 [−0.407,
  −0.170] (at 150: −0.261 and −0.284).
- None of the 142 directions' held halves was refused, so the two drops are the only difference.

### Step 3's shares, restated against −0.293

Descriptive only. Nothing is re-decided: step 3's readings, arm A's control failure and the
adoption of arm A's current best all stand.

| | Against S | Share of −0.269 | Share of −0.293 |
|---|---|---|---|
| Arm A (step 3) | −0.078 | 29% | **27%** |
| Arm A, clean *(recomputed)* | −0.062 | 24% of −0.261 | **21%** of −0.295 |
| Arm A, crunch *(recomputed)* | −0.106 | 37% of −0.284 | **37%** of −0.289 |
| Arm A's current best (3-C′ shrunk halfway, [levers](arm-a-levers-results.md)) | −0.083 | 31% ("about a third") | **28%** |
| Arm B (step 3) | +0.035 | −13% | **−12%** |
| K_S after 50 renders | −0.222 | 82% | **76%** |
| K_S after 100 renders | −0.241 | 89% | **82%** |

- Shares are the ratio of band-weighted means, as step 3's readout computes
  `share_of_K_S_gain`. Step 3's figures are from `song-settings/readout/report.json`; arm A's
  current best is the rounded −0.083 from its results.
- **Every share shrinks by about 8%** (0.269 / 0.293). Arm A is about a quarter of the true-DI
  search rather than 29%; its current best is 28% rather than "about a third".
- **K_S's own early renders** carry about three-quarters of the ceiling in 50 renders, not 82%.

## The zero-render checks (`check.json`)

These say whether the stored searches were cut short. Any follow-up gets its own plan.
- **The stored K_S (150 renders):** over its last 50, the held half gained a band-weighted −0.028
  [−0.041, −0.016], 13 of 14 bands; 72% of directions were still gaining ≥ 0.005 on the search
  half; none would have read flat at 150.
  - The whole extension then added −0.024 held, about the size of that last-50 tail. That is the
    slack this search found before its own curve went flat; it is not a bound on what else a
    different search could find (see How it is read).
- **Knob ceiling 2, stage 1 (200 renders per cell):** over its last 50, held −0.006 [−0.008,
  −0.004], 13 of 14 bands; 21% of cells still gaining ≥ 0.005 on the search half; the rule would
  have stopped 15 of 48 cells by 200. A little slack, about a fifth of K_S's tail.
- **Knob ceiling 2, stage 2 (24 renders per effect):** the median effect search gained 0.0003
  over its last 12 renders; 20% were still gaining ≥ 0.005. Cut to 12 renders per effect, 2 of
  48 cell choices change, and the held change of the chosen result is −0.001 [−0.003, +0.001].
  So halving stage 2's budget would have changed its result by about −0.001.

## How it is read

- **−0.293 [−0.378, −0.207] replaces −0.269 as the true-DI search's reference.**
- **"Converged by the declared rule"** applies to the 72 run directions, all of which stopped
  flat. It doesn't apply to the 72 not run: they enter through their parts' mean gain.
- **It is still a lower bound** on the best reachable settings:
  - the rule stops when one search's own curve flattens; a different start or search could go
    further;
  - only the knob space was searched (no pedals; [knob ceiling 2](knob-ceiling-2-results.md)
    found pedals add a little more);
  - the search half and the held half disagree a little (search −0.031, held −0.024).
- **A development reference, not a fresh estimate.** These held halves were read by earlier
  steps (knob ceiling, knob ceiling 2, step 3, arm A levers).
- **Step 3's shares** are restated above, descriptively. Nothing is re-decided.

## Stated limits

- Development data only, one take per part, one judge.
- Crunch has 5 parts and 5 bands; its figures are descriptive.
- The extension ran on half the directions; the other half is imputed per part (h = 0.009 on the
  search half, 90%).
- Clean's gain leans on two bands (Turbosauro and The Travelling Band).

---

Audited 2026-10-17 by an independent agent; changes: every number was recomputed from
`report.json`, `check.json`, the direction files and step 3's `song-settings/readout/report.json`
(all matched, including h, the pooled variances, the per-band and per-direction figures, renders by
batch and class, the two 600-render directions and the restated shares); added h beside the
headline, the run directions' own figure against S (amendment 1, item 5) and an explicit
by-stop-reason line; reworded the guard line (0 stopped by the guard, 2 reached 600 where both
held); added clean and crunch to the ceiling curve (amendment 1 asks for them at every point);
named the largest per-direction gain and loss; added the operator pauses and what they leave out
of the warm-up and render counts; softened three readings ("a lot more", "not open-ended",
"wasn't binding") to the effect sizes behind them.
