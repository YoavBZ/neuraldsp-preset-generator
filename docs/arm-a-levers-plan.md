# Arm A's levers: plan (2026-10-16)

Declared 2026-10-16, before any of its renders. It covers three experiments from the learning
analysis of song-settings' stored results (scripts kept in
`~/ndsp-presets/learn/song-settings/learning-analysis/`):
1. re-judging stored settings;
2. a rank-fidelity screen of the rebuilds on songs;
3. arm A stopped early.

Development data only. The rules of [`research/ml-plan-2026-10.md`](research/ml-plan-2026-10.md)
section 5 apply, with the user's rule of 2026-10-16 in place of pass/fail bars (below). Code:
`learn/arm_a_levers.py`, tests `tests/test_arm_a_levers.py`.

**Review:** reviewed 2026-10-16 (`tmp/arm-a-levers-plan-review.md`, local): approved with 10
changes, all folded in.
- Experiment 3's C′ arm is a zero-render replay.
- 3b is decided by 3a's sound result.
- Experiment 2 has 5 frozen candidates.
- dirs-avg is reported but can't win.
- S and the menu pick are candidates.
- Only the pooled mean decides.
- Leak, lag and non-finite rules are added.
- The relation to experiment 4 is stated.
- Machine-wide CPU cap.
- The ledger entry is entered.

The reviewer's optional local fidelity measure is experiment 2b. Nothing runs before the user's
yes.

## Why

From [song-settings-results.md](song-settings-results.md) and the learning analysis (held half,
log ratio against S, band-weighted, 90% band-clustered):

- **Arm A** (a search through C′'s rebuilt DI) is −0.078 [−0.157, +0.002] against S, about 30% of
  the true-DI search K_S (−0.269).
  - It closes ≥ 50% of K_S's gap on 34% of informative units, about the rate of its clean-render
    control (3 of 9).
  - So A is a weak but real search.
- **A moves the right way, noisily.** Its knob move has a positive cosine with K_S's on 92% of
  units, but only about 0.36 of the move lies along K_S's. It changes a mic on 99% of units and
  matches K_S's mics on 5%.
  - Shrinking toward S, or averaging the two directions, brings A closer to K_S in knob space
    (0.330 to about 0.28; S is 0.319).
  - This is a knob-space proxy, so experiment 1 judges it in sound.
- **Arm B** has little song-specific signal. Its direction from S is often right but too large: a
  0.5 blend is the closest in knob space, but a song-blind constant gets most of that.
- **A's gain tracks the rebuild's rank fidelity:** the Spearman, over a part's menu, of the
  rebuilt objective against the true DI. Unit-level ρ = −0.50 [−0.66, −0.29], about −0.026 in
  gain per +0.1 fidelity; C′'s median fidelity is 0.76, against 0.97 for the true DI across halves.
  - The link is correlational. The starting distance and the agreement of A's two directions carry
    signal beside it.
  - Experiment 4's arms (1z, 1a, 1b) were only judged on 4 clean-render cells, where 1a − 1z was
    −0.028 ± about 0.065.
- **The early stages carry most of A's work.** The main stage (52 of 150 renders) gets a median 91%
  of A's objective drop, and the later stages' change doesn't relate to the held gain (ρ 0.01).
- **Every stored search replays exactly, with zero renders.** Feeding a stored objective curve
  back to `knob_search` reproduces all 144 arm A searches (settings, best, every stage). The stored
  per-render evaluations reproduce all 144 K_S trajectories the same way. So A at 52 renders needs
  only a judge render per direction.

## The rule: estimates, not bars

There is no pass/fail threshold anywhere in this plan.

**What is measured:** each unit's held-half true-DI distance d (`knob_ceiling.judge` through the
measure DI, at the part's `judge_lag`, as arm A was judged). In experiment 2 it is the rank
fidelity.

**How it is compared:**
- The log ratio of the candidate against **S** and against **A**: the stored full arm A, C′, 150
  renders.
- The per-part unit is the mean over amps and directions.
- Band-weighted means with 90% band-clustered intervals (`song_readout.bw_stats`), the part-weighted
  figure (`confirm_run.stats`), bands better or worse, and the leave-one-band-out range.
- Each is reported per amp and per gain class.

**What decides:**
- **Only the band-weighted pooled mean** (fidelity in experiment 2). Per amp, per class,
  part-weighted and leave-one-band-out figures are descriptive.
- **The candidate lists below are frozen.**
- **The best candidate** is the one with the most negative band-weighted mean against S (the
  highest fidelity in experiment 2).
- **The tie rule:**
  - A candidate is "within noise" of the best when the 90% interval of its paired difference from
    the best contains 0.
  - The interval is band-clustered. On the fold-3 steps (3 bands, 5 parts) it is the wider of the
    band interval (t, 2 df) and the part interval (t, 4 df), so a chance-narrow 3-point SD can't
    decide.
  - Of the best and the candidates within noise of it, the first in the step's cost order is
    chosen.
- **Winner's curse:** the chosen candidate's estimate is optimistic, being the best of several on
  the same data. There is no correction, because no bar is applied. The guards are the tie rule and
  the fresh draw stated in the limits.

**Units and refusals:** song-settings' own 142 used directions. The readout's `drop_refused` rule
applies to every candidate alike: a direction any candidate can't score is dropped for all.

## Experiment 1: re-judging stored settings

No search. Each variant is built from stored settings and rendered once through the measure DI.
That one render gives both halves; the direction's held half is used.

**Definitions.** Only `knob_ceiling.space(amp, S)` changes; every other setting stays S's. The
analysis checked that A, B and the constant equal S outside it, and the builder asserts it.
- **Continuous dims** (`cont`; `space()` has no `log` dims) are combined in the dim's unit scale
  (`Dim.to_unit`), mapped back with `from_unit` and stored with `K.fmt`.
  - A value equal to S's (or to the source's) keeps that stored string.
  - A key missing from a preset counts as `d.lo`, as `coord_search` does.
- **Mics** (`leftMicType`, `rightMicType`) and **switches** (the amp's switches,
  `rightCabActive`) are taken whole from one source, as listed below.

| Variant | Continuous | Mics | Switches |
|---|---|---|---|
| shrink-0.25 | u_S + 0.25 (u_A − u_S) | A's | A's |
| shrink-0.5 | u_S + 0.5 (u_A − u_S) | A's | A's |
| shrink-0.75 | u_S + 0.75 (u_A − u_S) | A's | A's |
| S-mics | u_A | S's | A's |
| dirs-avg | (u_A + u_A′) / 2, A′ = the other direction's A | this direction's A | this direction's A |
| B-blend | u_S + 0.5 (u_B − u_S) | S's | S's |
| C-blend | u_S + 0.5 (u_C − u_S) | S's | S's |

- B is arm B's search-half prediction, and C the song-blind constant (`armB/predictions.json`).
- The shrink variants keep A's mics, so they isolate the knobs; S-mics isolates the mics.

**Candidates, frozen, in cost order:**
1. S (0 renders per song);
2. C-blend (0);
3. B-blend (0 renders, B's model);
4. the stored C′ menu pick (111 renders per song);
5. A (150);
6. S-mics;
7. shrink-0.5;
8. shrink-0.25;
9. shrink-0.75.

Variants 6–9 are one A search each, in order of simplicity.

- **S and the menu pick need no new renders** (stored).
- **If S is chosen:** A's own interval against S contains 0, so S can win under the tie rule. That
  reads "no lever beats doing nothing within noise on these data". The product then keeps S, as it
  does now, and the levers are not pursued without a better objective.
- **dirs-avg is reported but is not eligible to win.**
  - The held half's stem was searched against by the other direction, so its held-half figure is
    in-sample.
  - It is shown beside a zero-render in-sample comparator: A′'s stored judge on its own search
    half, which is this direction's held half.
  - Both directions' A settings exist for all 144 directions, including the 2 dropped ones, so
    dirs-avg needs no extra search.

**Repeat check:** 6 directions drawn by `random.Random(20261024)` are re-rendered for A and for S.
They must reproduce the stored d within 0.005 (log; knob ceiling's tolerance), or the run stops
and is investigated. This is a correctness check, not a decision.

**Renders:**
- 6 per-direction variants × 142 = 852.
- C-blend: 72, one per part and amp, since C and S are the same in both directions.
- Repeats: 12. Warm-ups: 72.
- **1,008 in all; hard cap 1,100.**

## Experiment 2: song rank-fidelity screen of the rebuilds (fold 3)

**Parts:** the 5 fold-3 parts (bands Eggy, Starnes And Shah, Timo And The Timezone; 30
directions), the only parts with nets other than C′:
- Bloomlight;
- Farthest Step;
- Fragments;
- Prodigal ElecGtr5;
- just-don't-talk elecgtr3.

**Rebuilds:**
- Each part's stem is rebuilt by `models-fs-{1z,1a,1b}-f3/fold3.pt`, exactly as `song_settings.rebuild_all`
  rebuilds with C′: CPU, re-equalised by fold 2's average minus fold 3's, at −22.9 LUFS.
- Every net must have its DONE marker (`song_settings.net_ready`).
- **Leak check:** for every net × part,
  `di_fine_structure.assert_no_leak(band, net_fold, cell_fold, train_pool_bands(fold, the net's caches))`
  is asserted, as experiment 4's control rebuild does. `rebuild_all` has no such check.
- Each new rebuild's GCC lag Δ against C′'s stored rebuild of the same stem
  (`rank_margin.gcc_lag`) is recorded.

**Renders:** each amp's whole menu (PR12 35, SW50R 45, AC20 31 = 111) through each new rebuild,
with one warm-up per amp. Each render is scored with `rebuilt_distance` on both halves at lag −52
(as C′'s stored menu pick was) and at the net's own alignment, −52 − Δ.
- **The deciding score** is at −52 − Δ. With Δ = 0, as on every experiment-4 control cell, the two
  are the same. In an ensemble, each member is scored at its own lag.
- C′'s scores are the stored `menupick/` results.
- **Repeat check:** 3 menu presets per part, drawn by `random.Random('20261024|<part>')`, are
  re-rendered through C′'s stored rebuild and must match `menupick/` within 0.005.

**Candidates, frozen, in cost order:**
1. C′ (exists for every fold; 1 render per evaluation);
2. 1z;
3. 1a;
4. 1b;
5. E4, the four-net ensemble {C′, 1z, 1a, 1b}: 4 renders per evaluation, and 3 nets to train per
   further fold.

1z, 1a and 1b come in experiment 4's tie order. An ensemble's objective, per preset, is the mean
over members of log(rebuilt distance).

**What is measured, per (part, amp, direction):**
- **Rank fidelity** (deciding): the Spearman, over the amp's menu, of the candidate's search-half
  objective against the true-DI search-half d. The true d is knob ceiling's stored menu, as in the
  analysis.
- **The menu pick's held sound:** log(true d of the candidate's pick on the held half / d_S). This
  is a sound outcome at zero search cost.
- **Pick regret:** log(true d of the pick / the best menu preset's d), held half.

**Non-finite values:**
- Presets are dropped pairwise: a preset counts only where both the candidate's objective and the
  true d are finite, as in the analysis.
- An ensemble member at inf or NaN makes that preset inf.
- The rebuilt-judge fallback (proxy) count is reported per net.

**How it is compared:**
- Each candidate's fidelity difference against C′, by the tie rule's fold-3 interval.
- The leave-one-band-out means.
- The expected A gain implied by the stored slope (−0.026 per +0.1), descriptive only.

**Decision:** the best fidelity, under the tie rule, in the cost order above. With 3 bands, the
rule will often keep C′. That is intended: a fold-3 gain this small would not justify training more
folds.

**Renders:** 3 nets × 5 parts × 114 = 1,710, plus 15 repeat renders and 15 warm-ups. **Hard cap 1,800.**

### Experiment 2b: local fidelity on the K_S trajectories (only on a tie)

It runs only if experiment 2 leaves the best candidate with at least one other candidate within
noise of it. It then decides among that tied set only, by the same rule.
- **What it adds:** the menu ranks presets far apart. A search needs ranking near S. The replayed
  K_S trajectories are exactly that: settings near S that a search visits, with each one's true d
  on both halves stored.
- **Settings:** per fold-3 (part, amp), 15 in all:
  - both directions' replayed K_S trajectories, pooled and deduplicated;
  - 40 settings drawn by `random.Random(20261025)`.
- **Renders:** each through C′, 1z, 1a and 1b (the tied ones' members), scored on both halves at
  each net's deciding lag. 4 × 15 × 40 = 2,400, plus 60 warm-ups. **Hard cap 2,500.**
- **Deciding measure:** local fidelity, the Spearman over the 40 of the candidate's objective
  against the true d. It is computed per half and averaged, per (part, amp). Ensembles take their
  members' scores.

## Experiment 3: arm A stopped at the main stage

**The search:** `knob_search`'s main stage alone. That is `coord_search` with `cats="levels"`, from
S, seed 20261013 (arm A's), under the limit `round(150 × 0.35)` = 52 renders.

**3-C′, a zero-render replay, on all 142 directions:**
- Each stored arm A `objective_curve` is fed back to the main stage. That gives exactly the
  settings arm A held after 52 renders, with no search render.
- Each direction is then judged once.
- **Test:** on all stored curves, the replay reproduces `stages.main.best`, every stage's renders
  and best, and the final A settings.
- **Decision on 14 bands:** candidates S, 3-C′ (52 renders), full A (150), in that cost order.

**Descriptive only:** if experiment 1 chose a one-search lever other than A (S-mics or a shrink),
it is also applied to 3-C′'s settings and judged.

**Renders:** 142 judges + 72 warm-ups, plus up to 142 + 72 for the lever. **Hard cap 450.**

**3a, the fold-3 parts (30 directions):**
- **3-W:** a live main-stage search with experiment 2's (or 2b's) chosen objective, if it is not
  C′. An ensemble renders through each member: 52 × k.
- **Decision:** candidates S, 3-C′, full A, 3-W, in that cost order, by the fold-3 tie rule.
- **Renders:** 30 × (53k + 1); **hard cap 6,400** (k ≤ 4).

**3b, all parts:**
- It runs only if 3a's rule chooses 3-W. If 3-C′, full A or S is kept, 3b does not run.
- It needs:
  1. the chosen net's fine-tunes for folds 0–2: experiment 4's recipe, seed 0, its fold-leak rules
     and DONE markers;
  2. the experiment-2 screen on those folds' 19 parts (reported, not deciding);
  3. 3-W on the 112 directions outside fold 3, compared with 3-C′ (already judged), full A and S,
     by the 14-band rule.
- E4 in 3b (9 fine-tunes) needs the user's yes, for cost.
- **Renders (k = 1):** 112 × 54 + 19 × 114 = 8,214. **Hard cap 8,300.**
- **MPS:** 3 fine-tunes, about 1.5–3 h each.

## Relation to experiment 4

- Experiment 4's step 2 read 1a "undecided" (the fold-1 branch, on the user's yes), and 1z and 1b
  "stop".
- Under the user's rule of 2026-10-16, those readings are descriptive, not vetoes.
  - This plan doesn't amend experiment 4's gate.
  - It can choose 1z, 1a or 1b without a further yes; the report states it beside experiment 4's
    reading.
- 3b reuses experiment 4's fold-1 fine-tune of the chosen arm if it exists
  (`models-fs-<arm>-f1` with DONE), and doesn't train it again.

## Machine order and caps

- **CPU:** at most 3 render processes machine-wide, counting every session's jobs.
  - Experiments 1 and 2 queue behind the running `song_diag render-targets` shards.
  - Each process runs under the separator screen's swap guard, launched with `setopt no_bg_nice`.
- **Every render** goes through `knob_ceiling.Renderer`: `isolate=True`, with process reuse.
- **Rebuild inference** runs on the CPU, alone.
- **MPS** (1c was stopped for stalling) is used only by 3b's fine-tunes, one at a time, queued
  behind any experiment-4 MPS job.
- **Order:**
  1. zero-render replays and checks;
  2. experiment 1 and 3-C′'s judges;
  3. experiment 2 (2b if tied);
  4. 3a;
  5. 3b if chosen.
- **Total hard cap:** 1,100 + 1,800 + 2,500 + 450 + 6,400 + 8,300 = **20,550 renders**. Running
  total: about 152–154.5k declared before this plan, so at most about 175k of 200k.
- **Disk:** scores and settings only, no render audio. Rebuilds are 15 arrays of about 4 MB.

## Code

**`learn/arm_a_levers.py`:**
- pure parts:
  - variant builders;
  - `main_stage` and the replays;
  - `rank_fidelity`, `ensemble_objective` and `objective_lag`;
  - the paired intervals and `choose`;
  - the reports;
- render commands, not unit-tested, like the other step modules.

**Commands, in run order:**
1. `replay` (zero renders);
2. `judge-variants --shard i/n`;
3. `judge-early --shard i/n`;
4. `report-1`;
5. `rebuild --folds 3` (torch);
6. `screen --folds 3 --shard i/n`;
7. `report-2`;
8. if tied: `local --shard i/n` and `report-2b`;
9. `early-search --folds 3 --shard i/n`;
10. `report-3`;
11. 3b only if chosen: the fine-tunes, then `rebuild`, `screen` and `early-search` with
    `--folds 0,1,2`, then `report-3`.

**`tests/test_arm_a_levers.py`:**
- the variant table (λ = 0 gives S, λ = 1 gives A, mics and switches, no key outside `space()`
  changes, a missing key counts as `lo`);
- `main_stage` equals `knob_search`'s main stage on a toy objective;
- the replay of all stored arm A and K_S searches (skipped without the data);
- the ensemble and non-finite rules;
- `rank_fidelity`;
- `choose` with the tie rule and the fold-3 wider interval;
- the drop rule.

## Seeds

- Searches: 20261013, as arm A and K_S used.
- Repeat-check draws: `random.Random(20261024)`.
- 2b's draws: `random.Random(20261025)`.
- 3b fine-tunes: seed 0, as in experiment 4.
- Nothing else is random. The intervals are t-based.

## Ledger

The entry `arm-a-levers` is in [`dev-test-ledger.json`](dev-test-ledger.json), entered 2026-10-16
after review and before any render. Its `tally` names the exact directions, nets and candidates.

## Stated limits

- **These are post-hoc, unblinded development analyses.** Every variant was suggested by reading
  these same scores, so the estimates are exploratory and optimistic. Anything chosen here needs a
  fresh draw (new parts, or experiment 4 step 5's draw) before it is trusted for shipping.
- **One take per part.**
- **Experiments 2 and 3a have 3 bands and reuse fold 3** (its third or fourth use). That is a
  selection effect, not a leak. The intervals are wide, so they can show a large gain, not a small
  one.
- **Menu fidelity is a coarse screen.** It ranks presets far apart, and its link to A's gain is
  correlational on the same data. 2b measures closer to S only on a tie.
- **dirs-avg's held-half figure is in-sample.**
- **3b's fine-tunes repeat one recipe and one seed per fold.** Seed noise isn't separated.
- **Experiment 1 judges levers on full A, not A at 52 renders.** The combination is descriptive
  only.
