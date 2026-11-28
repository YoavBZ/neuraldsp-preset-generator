# The `vc-own` search row `fs-own`: results (`phase_scratch_own_outcome`)

Plan: [scratch-own-plan.md](scratch-own-plan.md). Ledger `preset-ladder` `phase_scratch_own`, `_answers`, `_outcome`. Run 2026-11-28; audited 2026-11-28 (independent, Opus): CONFIRMED WITH CAVEATS. The audit recomputed every figure from the stored score records, and all of them match to within 1e-12. Every number is by the score (J0), from one search with one seed. Nothing here is by ear.

## The code: XW-part, shrunk-sensitive, by the score

The row repeats build 2's search with one change. The dry guitar is the stored `vc-own` (the true DI gated by our played notes, through the part's own finish) instead of the bank guitar `tr-di`. On the 40, the answer arm:

| Figure | What it prices | The 40 | Reading |
|---|---|---|---|
| **D_own** = G(`fs-own`) − G(build 2) | what real audio inside our note windows buys the search | **−0.191 [−0.261, −0.122]** | better |
| −D_own | build 2 against the row | +0.191 [+0.122, +0.261] | worse (a heard-size gain is not ruled out) |
| **C_own** = G(`fs-own`) − G(row (b)) | what is left against the true DI | **+0.082 [+0.018, +0.146]** | undecided |

- D_own reads better and C_own does not read matches, so the declared code is **XW-part**.
- **Shrunk-sensitive.**
  - On the shrunk arm, D_own is −0.102 [−0.160, −0.044] (better) and C_own is +0.042 [+0.007, +0.076] (matches), so that arm reads XW-closed.
  - The cp50, cp100 and cp200 arms read XW-part, like the answer arm.
- **Not refusal-sensitive.** Nothing was refused, and no rerun was needed.
- **Fieller's share** −D_own / (build 2 − row (b)) is **0.70 [0.52, 0.92]** (bounded). The ratio of the two 40-means is 0.71.
- **D_own is negative on 34 of the 40 parts.** It is below −0.05 on 29 and above +0.05 on 2.

**What the table says next.** Routes 1 and 2 stay open, and their room is at most −D_own. The residual belongs to N, K and F together. **The user picks the sound route.** Under XW-part, the spectral-envelope steps are unlocked, on their own declaration and table.

## What may be said, and what may not

**May be said, by the score:**
- About 70% of build 2's search cost against row (b) is recovered when the search gets real audio inside our note windows.
- The residual against the true DI is undecided, and it holds N, K and F together.
- `fs-own` sits below row (c) on the score, short of the heard-size bar.

**May not be said:**
- Anything about the song-only path. `vc-own` is an oracle: the true DI's audio, gated by notes read from the true DI.
- That the cost is closed.
- That the ceiling sits above LOUDAR.
- Any gain on the panel.
- Anything by ear.

## The caveats (binding, from the audit)

1. **Shrunk-sensitive.** The shrunk arm reads XW-closed, with C_own +0.042 (matches). The answer arm reads XW-part.
2. **By the score, one search, one seed.** Nothing here is heard.
3. **The parts are reused.** The 47 parts have been read many times.
4. **The panel shows nothing.**
   - D_own on the panel is +0.011 [−0.268, +0.291], and C_own is +0.178 [−0.157, +0.513].
   - Every result here is on the 40.
5. **C_own mixes N, K and F.** It can't be split here. The 50-evaluation `vc-fin` row (about 2.6k renders, on its own go) would split it.
6. **The search mask moves with the guitar, but the effect is small and unrelated.**
   - J0's playing frames on the search half are set from the dry guitar. The audit replicated the masks for the true DI, `tr-di` and `vc-own`.
   - On the 40, the overlap (Jaccard) of `vc-own`'s playing frames with `tr-di`'s has a median of 0.996 and a minimum of 0.890. It is below 0.95 on 3 parts and exactly 1 on 16.
   - The mean difference in playing frames is 4.3 of about 418.
   - Spearman against D_own: the overlap −0.10; the difference in playing frames +0.12.

## The figures (the 40 unless named; recomputed by the audit)

**D_own on every arm**

| Arm | The 40 | Reading | Clean 20 | Crunch 20 | BKS 16 | GOAT 24 | All 47 | Panel 7 |
|---|---|---|---|---|---|---|---|---|
| answer | −0.191 [−0.261, −0.122] | better | −0.254 [−0.402, −0.106] | −0.129 [−0.176, −0.082] | −0.161 [−0.281, −0.041] | −0.222 [−0.303, −0.140] | −0.124 [−0.207, −0.040] | +0.011 [−0.268, +0.291] |
| shrunk | −0.102 [−0.160, −0.044] | better | −0.151 [−0.280, −0.023] | −0.052 [−0.098, −0.006] | −0.078 [−0.183, +0.027] | −0.125 [−0.184, −0.067] | −0.058 [−0.124, +0.007] | +0.028 [−0.182, +0.238] |
| cp50 | −0.131 [−0.193, −0.068] | better | −0.201 [−0.320, −0.083] | −0.060 [−0.114, −0.005] | −0.124 [−0.220, −0.029] | −0.137 [−0.228, −0.046] | −0.119 [−0.178, −0.060] | −0.095 [−0.280, +0.089] |
| cp100 | −0.179 [−0.249, −0.109] | better | −0.269 [−0.408, −0.130] | −0.089 [−0.153, −0.026] | −0.165 [−0.286, −0.044] | −0.193 [−0.275, −0.111] | −0.116 [−0.208, −0.023] | +0.011 [−0.288, +0.310] |
| cp200 | −0.192 [−0.266, −0.118] | better | −0.267 [−0.425, −0.108] | −0.118 [−0.174, −0.062] | −0.172 [−0.302, −0.042] | −0.212 [−0.296, −0.129] | −0.134 [−0.219, −0.048] | −0.017 [−0.296, +0.262] |

- **Each of the 32 clusters left out:** the mean stays in [−0.205, −0.164], the upper end at most −0.108, and every one reads better.
- **The three largest parts** are `8ae994594bad` −0.758, `9c3262e5b20e` −0.721 and `c1ea6ef819b3` −0.673. Their contribution to the mean is −0.053 [−0.107, +0.001]. Without them the 40 read −0.156 [−0.207, −0.106] (better).
- **One part per partner** (33 parts, 30 on the 40): −0.203 [−0.298, −0.107] (better).

**C_own on every arm**

| Arm | The 40 | Reading | Clean 20 | Crunch 20 | BKS 16 | GOAT 24 | All 47 | Panel 7 |
|---|---|---|---|---|---|---|---|---|
| answer | +0.082 [+0.018, +0.146] | undecided | +0.146 [+0.012, +0.280] | +0.018 [−0.008, +0.044] | +0.094 [−0.023, +0.212] | +0.070 [+0.009, +0.131] | +0.114 [+0.008, +0.220] | +0.178 [−0.157, +0.513] |
| shrunk | +0.042 [+0.007, +0.076] | matches | +0.069 [−0.002, +0.141] | +0.014 [−0.008, +0.036] | +0.041 [−0.013, +0.094] | +0.043 [−0.005, +0.091] | +0.071 [−0.025, +0.167] | +0.129 [−0.134, +0.392] |
| cp50 | +0.100 [+0.042, +0.158] | undecided | +0.176 [+0.072, +0.280] | +0.023 [−0.003, +0.050] | +0.085 [−0.024, +0.193] | +0.115 [+0.062, +0.167] | +0.092 [+0.030, +0.153] | +0.075 [−0.125, +0.275] |
| cp100 | +0.062 [−0.001, +0.125] | undecided | +0.127 [+0.005, +0.248] | −0.003 [−0.054, +0.049] | +0.071 [−0.044, +0.186] | +0.053 [−0.008, +0.114] | +0.085 [+0.041, +0.129] | +0.131 [+0.056, +0.206] |
| cp200 | +0.085 [+0.022, +0.148] | undecided | +0.152 [+0.020, +0.283] | +0.018 [−0.016, +0.051] | +0.087 [−0.027, +0.200] | +0.083 [+0.019, +0.147] | +0.086 [−0.016, +0.187] | +0.088 [−0.229, +0.404] |

- **Each of the 32 clusters left out:** the mean stays in [+0.059, +0.099], the lower end at least +0.002, and every one reads undecided.
- **The three largest parts** are `89cac0bf475c` +0.699, `b2ce529e68f9` +0.622 and `1cc512e059fb` +0.390. Their contribution is +0.043 [−0.004, +0.090]. Without them the 40 read +0.045 [+0.001, +0.088] (matches).
- **One part per partner:** +0.100 [+0.026, +0.174] (undecided).
- C_own is negative on 13 of the 40 parts and above +0.05 on 21.

**Against row (c):** G(`fs-own`) − G(row (c)) is −0.096 [−0.153, −0.038] on the 40. That reads matches: the whole interval is below zero, but the mean is short of the −0.10 bar.

| Arm | The 40 | Reading |
|---|---|---|
| shrunk | −0.031 | matches |
| cp50 | −0.057 | matches |
| cp100 | −0.125 [−0.182, −0.067] | better |
| cp200 | −0.095 | matches |

- **Splits:** clean −0.116, crunch −0.075, BKS −0.058, GOAT −0.133, all 47 −0.053, panel +0.033.
- **Clusters left out:** the mean stays in [−0.109, −0.084], reading better or matches.
- **The three largest parts** are `1cc512e059fb`, `c1ea6ef819b3` and `1b445da68053`. Without them the 40 read −0.066 (matches).
- **One part per partner:** −0.100 [−0.160, −0.039] (matches).

**Each row's own G on the 40**

| Row | G | Reading |
|---|---|---|
| `fs-own` | −0.182 [−0.259, −0.106] | passes |
| Build 2 | +0.009 [−0.088, +0.106] | |
| Row (b) | −0.264 [−0.310, −0.219] | |
| Row (c) | −0.087 [−0.155, −0.018] | |

**LOUDAR (beside).** G at cp50 of `fs-own` less `ld-stem`'s G50, on BKS+panel (23 parts, `bp_rows`):
- the pooled figure is −0.112 [−0.265, +0.041], part-weighted mean −0.116;
- BKS −0.110 [−0.279, +0.060]; panel −0.114 [−0.442, +0.213].

Read both ways:
- **This way:** "matches", so a heard-size loss against LOUDAR is ruled out. It is not "better", so the oracle ceiling is **not shown** to sit above the released song-only rebuild on unseen sets.
- **The other way (−x):** undecided.

For comparison, build 2 at cp50 less `ld-stem` is −0.002 [−0.121, +0.116], the seen +0.002 with the sign reversed.

**Ranks (beside).** Spearman against −D_own on the 40, 40 parts each:
- with the stored S, +0.47;
- with the control's Ux, −0.26.

**Reproduced first.** Build 2 − row (b) came out at +0.274 [+0.186, +0.361] and LOUDAR's G50 on BKS+panel at −0.051 [−0.159, +0.058]. Both equal their stored rows exactly. Every seen figure repeated to 3 places:

| Seen figure | Value |
|---|---|
| G(build 2) | +0.009 |
| G(row (b)) | −0.264 |
| Build 2 − row (b) at cp50 | +0.230 |
| Build 2 − row (b), shrunk | +0.143 |
| `vc-own`'s floor | +0.321 |
| LOUDAR − build 2 at cp50 | +0.002 [−0.116, +0.121] |

## The run

All steps ran on 2026-11-28 from fresh detached worktrees of main, at 309636c9 for the search and at 44a686f2 for the score. They ran after the control's XC-stands (`coverage_label` null) opened the gate, with `require_own` and `require_spend("search-row")` holding before each launch.

| Step | Renders | Wall time | Result |
|---|---|---|---|
| `check-score` | 40 | 100 s | Repeats row (c) exactly |
| `check-search` | 22 | 48 s | Repeats row (c) exactly |
| `search`, 3 shards | 4,244 + 4,252 + 3,933 = 12,429 (94 of them start references) | 6,247–6,457 s per shard, about 1.8 h | No refusal |
| `answers` | 0 | 10 s | 47 parts, 0 refused (`phase_scratch_own_answers`) |
| `score`, 3 shards | 320 + 320 + 300 = 940 | 711–736 s per shard | Scoring control on 47 of 47 parts, every Cen render exactly its stored value |
| `reproduce` | 0 | 17 s | Holds |
| `read` | 0 | 93 s | Once |

**13,431 renders** in all. `rows.json` sha256 c627325c…, `report.json` sha256 decf09ff….

## Defects found (recorded; none changes a figure)

1. **A privacy slip in the stored read files.**
   - The read wrote the names of the settings the non-finite rule replaced as they came. One of them is a partner's part key, so that key sits in the local `rows.json` and `report.json` under PF; nothing went to git.
   - The fix is PR #663: the names are tagged, and the checks' mismatch names follow the same rule.
   - The stored files stay as they are (the orchestrator's call: no re-read). Here the partner appears only as its tag, `ea5fc54a8160`.
2. **A non-finite borrowed answer.**
   - On 3 parts (`b0936e9f5d83`, `89cac0bf475c`, `c1ea6ef819b3`), the borrowed answer from that one partner rendered non-finite. `nonfinite_rule` replaced it as declared.
   - It enters only the borrowed answer, never G, so no D_own or C_own figure changes.
3. **A cosmetic label on the start references.**
   - `scratch_notes.start_reference` writes its own constant `dry: "tr-di"` into each start-reference record, whatever guitar it was handed.
   - The record's `dry_sha256` is `vc-own`'s, and the search records name `vc-own`, so nothing was read from the wrong guitar.
   - The label is left as it is, because the shared step is pinned.
