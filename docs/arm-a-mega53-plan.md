# Arm A with Mega-53: does the better separator help at the song level? Plan (2026-10-17)

Declared 2026-10-17, before any separation or render for it, and before experiment 1d's report was
read. It is the song-level test that experiment 1c's readout calls for
([local-objective-results.md](local-objective-results.md), 1c: "it does not by itself show a
song-level gain; that needs arm A's song test with Mega-53 in the loop"), and the fresh-draw check
on full mixes with vocals that amendment 3a (item 6) requires before any separator switch.

The rules of [`research/ml-plan-2026-10.md`](research/ml-plan-2026-10.md) section 5 apply, with the
user's rule of 2026-10-16 (estimates with intervals, no pass/fail bars, the cheaper option on a
tie) and decision 2 (evidence-based stopping). Code: `learn/arm_a_mega53.py`, tests
`tests/test_arm_a_mega53.py` (written after review, before any render). Ledger: `arm-a-mega53` in
[`dev-test-ledger.json`](dev-test-ledger.json).

**Status:** declared, then reviewed 2026-10-17 by an independent agent: approved with 8 required
changes, all made as [amendment 1](#amendment-1-2026-10-17-review-changes-before-any-separation-or-render)
below, which governs where the two differ (stage F's pool, renders, hours and stopping are
restated there). Re-reviewed the same day: approved, no further required changes. Nothing has
been separated or rendered.

## Why

- **Arm A's adopted recipe** ([levers](arm-a-levers-results.md), adopted by the user 2026-10-16):
  the rebuilt-DI search stopped after its 52-render main stage (3-C′), its moves shrunk halfway to
  S, falling back to S on a silent render. On step 3's 24 parts: **−0.083 [−0.135, −0.032]**
  against S, 12/14 bands; about −0.07 expected after selection. It was measured with htdemucs_6s
  stems of the *instrumental* context.
- **Experiment 1c:** Mega-53 feeding both the rebuild and the reference lifts the cross-half local
  Spearman from 0.289 to 0.398, **+0.109 [+0.058, +0.160]**, about 43% [26%, 70%] of the
  perfect-stem gain (1b). The matched configuration is the decided one.
  - Right around S, where the search starts, no gain was detected: −0.002 [−0.049, +0.045].
  - On the K_S points (where a good search goes) it is +0.122 [+0.045, +0.199].
  - Local fidelity is a proxy. The link from fidelity to arm A's held gain is correlational
    (−0.026 in gain per +0.1 of *menu* fidelity, levers' learning analysis). Only a song test says
    whether the better ranking turns into closer presets.
- **What the product would get:** the full mix, with vocals, and a 5–6× separation cost (Mega-53
  about 80–95 s per 30-s context on the CPU, htdemucs about 15–28 s).

## The question

With arm A's adopted recipe held fixed, how much closer to the record (held half, true DI) does
arm A land when Mega-53's stem replaces htdemucs's, feeding both the rebuild and the search's
reference? Asked twice:
1. **Stage D (development):** on step 3's 24 parts, instrumental context, paired with arm A's
   stored htdemucs results.
2. **Stage F (fresh draw):** on development parts never used by arm A, the levers or the
   separator experiments, from the **full mix with vocals**, both separators run live.

## Are step 3's songs reusable? What is a fresh draw?

**Step 3's 24 parts are reused for stage D, as a development reading, not as the decision.**
- **Why reusable:** the song-level outcome with Mega-53 has never been observed on them. The
  htdemucs comparator is stored and exactly reproducible (the stored searches replay with zero
  renders, and a re-render matched within 2e-5), so the contrast is paired at no comparator cost.
  It is also the same parts and directions where 1c measured local fidelity, so it tests whether
  1c's gain transfers to the song level, unconfounded by a change of parts.
- **Why not decisive:**
  - this is at least the seventh use of these parts (step 3, levers, local objective 1, 1b, 1c,
    1d, bleed audit);
  - **two selection biases pull in opposite directions:** the recipe (52 renders, shrink 0.5) was
    chosen to maximise the *htdemucs* arm on these parts, which flatters the comparator; Mega-53's
    matched configuration was chosen on these parts' local fidelity, which may flatter Mega-53;
  - they are instrumental contexts, not what a product receives.

**The fresh draw is stage F: the 35 classed clean or crunch development parts outside step 3's 24**
(label table, [`label-table-parts.json`](label-table-parts.json)), in 17 bands.
*(Stage F only, superseded by amendment 1, item 1: the usable pool is 21 parts in 12 bands.)*
- **What makes them fresh for this question:** no arm A search, no levers variant, no
  local-objective experiment and no separator experiment has scored them. Arm A's recipe and the
  Mega-53 configuration were chosen without them.
- **What they have been used for** (stated, none of it chooses anything here):
  - the label table's 111-preset menus through the measure DI (true-DI scores of factory presets);
  - htdemucs stems of the instrumental context (label table, no SNR filter);
  - arm B's training bank (their sessions' DI tracks as inputs) and the arm B diagnostics' render
    targets (DI windows, never records);
  - the bleed audit (zero renders);
  - Honey: knob ceiling (its half B is refused by the judge) and the separator-robust networks'
    residual library;
  - S itself was chosen on 22 clean and 13 crunch development parts, which may include some of
    them. That understates gains against S; it does not touch the separator contrast.
- **Freshness is graded, so it is reported in three rows:**

  | Row | Parts | Bands | What it is |
  |---|---|---|---|
  | **F, all fresh (declared)** | 35 | 17 | new parts; 21 of them share a song (the mix) with a step-3 part |
  | F-song: new songs only | 14 | 7 | no step-3 part in the same song: Nosso Mundo; let's dance ×2; wickerman ×4; Hikikomori; Honey, Lost Alive, Until I Get Back; Measurements, Strangest Places; She's Gone |
  | F-band: new bands only | 8 | 5 | Ale Lak, Szymon Skiba, John Morgan Kimock, Swatkins, Bernard Purdie Tribute All-Stars (descriptive: 5 bands) |

  - **Same-song parts carry part of the selection's luck** through shared band and session
    effects, so F-song is the robustness row. With 7 bands it can show a large effect, not a small
    one.
  - 12 of the 17 bands are among step 3's 14. They are new units for the recipe's and the
    separator's selection, not new bands.
- **Experiment 4 step 5's reserved bands:** that step (a fresh known-target control) was stopped
  2026-10-16. Stage F spends 10 of the parts its 8 candidate bands held outside the 24; stated
  here and in the ledger.
- **Held-out data is never read.** The code asserts every stage-F part's session has
  `split == "development"` in `docs/validation-datasets.json`, that none is from Guitar-TECHS P3,
  sets 4, 5 or 6, or any `held_out_uses` entry, and refuses otherwise.

## The recipe (fixed; only the stem and its rebuild change)

For each direction (search half → held half), part and amp, with the part's class's S:
1. **Rebuild:** the part's fold's final C′ (DONE marker) rebuilds the 10-s stem crop, re-EQ'd by
   fold 2's average − fold f's, to −22.9 LUFS (`local_objective.rebuild_from`, exactly 1b's and
   1c's recipe), with experiment 4's leak assertion per part.
2. **Search:** `arm_a_levers.main_stage`: `knob_ceiling.coord_search` with `cats="levels"` from S,
   seed 20261013, the limit round(150 × 0.35) = **52 renders** through the rebuilt DI. Objective:
   `rebuilt_distance(stem, render, rebuilt)` on the search half at lag −52, with its activity
   fallback (the C′ fallback of 1c's "own" mask; the same function).
3. **Shrink:** `arm_a_levers.shrink(dims, S, best, 0.5)`: continuous dims halfway to S in unit
   scale, the best's mics and switches.
4. **Fallback to S (the product's rule, made concrete now):** the shrunk setting is rendered once
   through the arm's own rebuilt DI. If that render's peak (after trimming the first 0.25 s) is
   below −60 dBFS, or its search-half objective is non-finite after the activity fallback, the
   arm's output is S. Product-side information only: the held half and the true DI are not used.
5. **Judge:** the output rendered through the part's measure DI, `knob_ceiling.judge` against
   `reference.wav` on both halves at the part's `judge_lag`; the held half is the outcome. The
   unshrunk best is also judged (descriptive: does shrinkage carry to fresh data?).

Renders per direction and arm: 52 + 1 + 2 = **55**.

**The arms:**

| Arm | Stem (search reference) | Rebuilt DI | Stage D | Stage F |
|---|---|---|---|---|
| **H** (today's recipe) | htdemucs_6s guitar stem | C′ of that stem | stored (zero search renders) | live, full mix |
| **M** (Mega-53, matched) | Mega-53 `electric-guitar` stem | C′ of that stem | live (1c's crops and rebuilds) | live, full mix |
| **T** (anchor: a perfect separator) | `reference.wav` (the amp track) | C′ of the amp track (1b's) | live, descriptive | — (a song gives no amp track) |
| **X** (conditional, below) | per 1d | the separator-robust net's rebuild | live | live |

- **Stage D's H** is the stored 3-C′ replay with shrink 0.5 (`levers/early/lever-shrink-0.5/`).
  Only its fallback check (step 4) is rendered: 142 renders through C′'s stored stem rebuild.
- **Stage D's M** uses 1c's Mega-53 crops (`local-objective/sep/mega53/crop/`) and rebuilds
  (`local-objective/rebuilt-mega53/`), which passed 1c's checks. Nothing is re-separated.
- **Stage D's T** uses 1b's rebuilds (`local-objective/rebuilt-ref/`). It is the song-level
  analogue of 1b, and the ML plan's step 6 row 4 test ("re-run arm A from the amp track") with
  the adopted recipe. It is there to interpret a null: if T doesn't beat H either, local fidelity
  doesn't transfer to the song level and the separator is not the limit; if T does and M doesn't,
  Mega-53 falls short.

## The conditional arm X (declared now, before 1d's report is read)

Experiment 1d (amendment 4, running; `~/ndsp-presets/learn/local-objective/report-1d.json`) tests
the separator-robust rebuild. Arm X is added **only if 1d shows a gain**, by this mechanical rule
on `report-1d.json["primary"]` (row (a), all of Σ, cross-half):
1. if `P2_sepnet_mega53_minus_mega53` has `lo90 > 0`: **X = the separator-robust net rebuilding
   the Mega-53 stem**, scored against that stem (1d's `csep_mega53`). Its contrast is X − M;
2. otherwise, if `P1_sepnet_stem_minus_current` has `lo90 > 0`: **X = the net rebuilding the
   htdemucs stem**, scored against it (1d's `csep_stem`). Its contrast is X − H;
3. otherwise (both intervals contain 0 or lie below it, or the report is incomplete): **no arm X.**
   1d's own reading builds on a positive estimate through more library work, not a song test.

- **Why "lo90 > 0" here:** an X arm costs about 19.5k renders. 1c's local gain of +0.109, with an
  interval above 0, is what this plan exists to translate into song-level terms; a local gain
  whose interval contains 0 would almost surely give an undetectable song-level one.
- `arm_a_mega53 decide-x` applies the rule, writes `x.json` (the rule's inputs and outcome) and is
  run once, before any render; the outcome is appended to the ledger as `arm_x` before the first
  render. It is never revisited.
- **X's rebuilds:** stage D reuses 1d's (`rebuilt-csep-stem/` or `rebuilt-csep-mega53/`); stage F
  rebuilds with 1d's pinned networks (amendment 4a's sha256 table), `assert_sepnet_ok` per part
  (the band is in none of the parent C′'s pool, the fine-tune's caches or the residual library),
  and amendment 4b's level rule (within 0.05 LU of the paired C′ rebuild of the same source).
- **Cost order on a tie:** the incumbent C′ before the separator-robust net.

## Stage D: development (step 3's 24 parts, instrumental context)

- **Units:** song-settings' 142 used directions (144 minus the 2 the readout dropped), per part the
  mean over amps and directions.
- **Renders:**

  | What | Renders |
  |---|---|
  | M: 142 × 55, plus 72 warm-ups (one per part and amp through the rebuild) | 7,882 |
  | T: the same | 7,882 |
  | H's fallback checks: 142, plus 72 warm-ups | 214 |
  | Repeat check (below): 6 judges, 6 warm-ups | 12 |
  | **Stage D** | **15,990** (hard cap 16,500) |
  | X, if added | +7,882 (cap +8,200) |

- **Plumbing checks (zero extra renders, each stops the shard if it fails):**
  - **M's first evaluation is S.** Its search-half objective must equal 1c's stored score of S
    through `cprime_mega53` against the Mega-53 crop (same function, lag −52, own mask with the C′
    fallback) within 0.005 (log). T's must equal 1b's `cprime_ref` S score the same way. This
    checks that the search optimises exactly the objective 1c and 1b measured.
  - **Repeat check:** 6 directions drawn by `random.Random(20261034)` from the 142: H's stored
    shrunk setting re-rendered through the measure DI must reproduce its stored held-half judge
    within 0.005 (log). The renderer then matches the stored comparator.
- **S** is step 3's stored S judge (knob ceiling's), as the levers used.

## Stage F: the fresh draw (35 parts, full mix with vocals)

*(Superseded by amendment 1: 21 parts, 126 directions, 14,112 renders.)*

**Inputs (zero renders, CPU):**
1. **Contexts** (`contexts`, the main `.venv`): each part's 30-s context of the **full mix**
   (`learn.separate.context`, role `mix`: every included mix track at unity, vocals kept), the crop
   10 s at its offset. Checks: the crop slice equals the crop folder's `mix.wav` within 1e-6; the
   crop is 480,000 samples. Saved as float32 so both separators read identical input.
   - 4 parts have no vocal tracks (let's dance ×2, magilla elecgtr1, Hikikomori): their full mix
     is their instrumental mix. Stated; no special rule.
2. **htdemucs** (`separate --sep htdemucs`, demucs-venv): `learn.separate.GuitarSeparator` with
   `DEVICE=cpu`, 2 threads, as the label table's stems (htdemucs_6s, shifts 0, overlap 0.25).
3. **Mega-53** (`separate --sep mega53`, msst-venv): `separator_screen.MsstSeparator` exactly as
   1c (provenance hashes and commit ea7eb9c checked, pruned head, CPU, 4 threads,
   `PYTORCH_ENABLE_MPS_FALLBACK=0`, 48 → 44.1 kHz, `electric-guitar`, channel mean, back to 48 kHz),
   behind 1c's memory gate (about 11 GB available for the pruned head; no training job, no other
   separation) and its 256 MB swap guard.
   - **Per-part checks** (as 1c; a failing part stops `separate`, recorded in `check.json`):
     480,000 samples; GCC(Mega-53 crop, htdemucs crop) within ±3 samples (both from the same
     input).
   - **Logged (descriptive):** both stems' gain-fitted SNR against `reference.wav`; Mega-53's
     level above 6 kHz relative to htdemucs; the htdemucs full-mix stem's SNR beside the label
     table's instrumental stem (the vocals' cost to htdemucs, zero renders).
4. **Rebuilds** (`rebuild --sep htdemucs|mega53`, demucs-venv for torch): the recipe's step 1.
   Checks: GCC between the two rebuilds of a part within ±3 samples; each at −22.9 LUFS within 0.05,
   or, if BS.1770's gate puts it outside (amendment 4b), within 0.05 LU of the other separator's
   rebuild of the same part. A failing part is recorded and `search` refuses it until resolved;
   nothing is silently dropped.

**Renders:**

| What | Renders |
|---|---|
| Per part and amp (105): a measure-DI warm-up, S's judge, one warm-up per rebuild (H, M) | 420 |
| H and M: 210 directions × 2 × 55 | 23,100 |
| **Stage F** | **23,520** (hard cap 24,300) |
| X, if added: 105 warm-ups + 210 × 55 | +11,655 (cap +12,100) |

- **S's judge** is rendered fresh (it is the comparator for every arm) and checked against the label
  table's stored `menu.json` S score within 0.005 (log) on every half the judge scores; a miss
  stops the shard (the renderer against stored scores, as amendment 4a).
- Honey's half B is refused by the judge (knob ceiling), so its search-A direction drops for every
  arm (the drop rule below).

## Measures and contrasts (declared now)

**The outcome:** each direction's held-half true-DI distance d (`knob_ceiling.judge` through the
measure DI). Per direction, log(d_arm / d_ref); per part, the mean over amps and directions; then
band-weighted means with **90% band-clustered t intervals** (`song_readout.bw_stats`, bands − 1
df), the part-weighted figure, leave-one-band-out range, bands better and worse, per amp and per
class.

**Primary contrasts (two, both reported whatever they show):**
- **P_D (stage D): M − H,** step 3's 142 directions, 14 bands (13 df).
- **P_F (stage F): M − H,** the fresh draw, row F (up to 17 bands).

**Also reported:**
- each arm against S, in each stage (stage F's H − S is the first fresh-draw estimate of the
  adopted recipe, from full mixes, which the levers' results say is needed before shipping);
- stage D: T − H (the perfect-separator song gain), M − T, and **M's share of T's gain**,
  (M − H) / (T − H), band-weighted with Fieller's 90% interval (13 df), named "unbounded" with its
  shape when T − H's interval contains 0 (as 1c);
- the unshrunk best against the shrunk output, per arm (does shrinkage carry to fresh data?);
- the fallback count per arm; the activity-fallback count per search;
- arm X, if added: its contrast (X − M or X − H) in each stage, and X − S;
- P_F − P_D is not tested (different parts and contexts); both are shown side by side.

**Rows (each contrast, each stage),** with 1c's machinery (`local_objective_1c.ROWS`, the bleed
audit's flags in `docs/audits/bleed-2026-10-16/bleed-table.json`, which covers all 59 parts):
- **(a) all directions: the declared row;**
- **(b) no high bleed:** the direction rule (drop a direction whose held half, the truth, is
  flagged high) with the cell rule (either half flagged) beside it;
- (c) no moderate or high bleed, both rules;
- (d) Cambridge only (no bleed: the overdubs are clean);
- without the MUSDB18-train songs' bands (Atlantis Bound, Wall Of Death: htdemucs trained on
  those mixes, so H is flattered there; Mega-53's training data is unstated);
- stage F only: F-song and F-band (above).
- **Stage F has more high bleed than step 3:** 6 of its 9 Telefunken parts read high on at least
  one half (Lost Alive and Until I Get Back at about −2 dB on half B, so their truth there is mostly
  other instruments). Bleed in the truth dilutes every arm's ratio toward 0; it does not favour a
  separator, since renders carry no bleed. So (a) stays declared, and (b) is read beside it.

**Drop rule:** a direction any arm of the stage can't score (a refused held half after the fallback
to S, or S's own held half refused) is dropped for every arm of that stage, and listed.

**Non-finite objective values** inside a search are `inf` (the search treats them as worse than any
finite value), as arm A did.

## Reading (estimates; the user's rule)

- **Each primary is its estimate and interval.** Negative is closer to the record.
- **What decides the product's separator for arm A: P_F, row (a).**
  - **Interval below 0:** Mega-53 lands closer on fresh full mixes. The product path is to switch
    the separator for arm A, weighing the gain (in log distance, and as a share of H − S) against
    the 5–6× CPU cost; that weighing is the user's.
  - **Interval contains 0:** a tie, so the cheaper option, htdemucs, stays. The estimate is
    reported and built on if negative (for example a stronger separator, or the blend), not
    dropped.
  - **Interval above 0:** Mega-53 makes arm A worse on fresh full mixes.
- **P_D is the development reading** beside it: with T, it says whether 1c's local gain transfers
  to the song level on the parts where it was measured. If P_D and P_F disagree, P_F decides; the
  disagreement is reported.
- **Two primaries:** both are reported, neither promoted after seeing the data. They share the
  recipe but not parts, so they are close to independent; one of two 90% intervals excluding 0 by
  chance alone is about 19% likely (about 10% for a given direction).
- **Arm X** is read by the same rule on its own contrast, in stage F, with the incumbent C′ first
  in the cost order.

## Stopping (decision 2)

- **Per search:** the 52-render main stage. That is the levers' evidence: the main stage carries a
  median 91% of the 150-render search's objective drop, the later stages' change is unrelated to
  the held gain (ρ 0.01), and 3-C′ against full A is −0.007 [−0.031, +0.016].
- **Stage D:** a fixed set, paired direction by direction with stored results; every direction is
  needed for the 14-band interval (on fold 3 alone the minimum detectable effect is 2.30 σ_d,
  against 0.71 σ_d on 14). Only breakage stops it.
- **Stage F: precision-based, at most the pool.** *(Withdrawn by amendment 1, item 4: a fixed set.)*
  - Whole bands are taken in the order `random.Random(20261035).shuffle` of the 17 sorted band
    names. Within a band, every fresh part, amp and direction runs, each direction through every
    arm back to back (so a stop leaves the arms balanced).
  - Before a shard claims a new band, it computes P_F's 90% half-width (row (a)) on the completed
    bands. **When at least 10 bands are complete and the half-width is ≤ 0.025, no new band is
    claimed;** bands in progress finish. Otherwise the pool runs out at 17 bands.
  - **Why 0.025:** it separates from zero a song-level gain of about 0.04, about half of arm A's
    gain over S (−0.083), the least that would plausibly justify 5–6× the separation CPU. With a
    band SD of the paired contrast around 0.06 it is reached near the full pool, so the hours below
    assume the full pool.
  - The rule depends on precision only, never on the estimate's sign or size.
- **Arm X** follows its stage's stopping.

## Machine order, hours and disk

*(Renders, hours, gates and order restated in amendment 1, items 6 and 8 and its tables.)*

- **At most 3 render processes machine-wide,** counting every session's (`search` refuses to start
  beyond it), each launched with `setopt no_bg_nice`, `nohup`, `OMP_NUM_THREADS=1`, under the swap
  guard and the shared `STOP.json`.
- **Every render** goes through `knob_ceiling.Renderer`: `isolate=True`, process reuse. Any render
  kept as audio (the final outputs' FLACs, for a possible listening check) is 16-bit FLAC with the
  first 0.25 s trimmed.
- **Separation never overlaps 3 render processes.** Mega-53 uses 4 threads; 3 render processes
  plus 4 threads oversubscribe 8 cores. So while a separation runs, at most 2 render shards run
  (shard 2/3 of stage D starts when the separation chain exits).
- **Order:**
  1. now (zero renders): this plan, review, ledger; then the code and its tests;
  2. after 1d's report (about 11:00): `decide-x`, then:
     - **CPU lane A:** contexts → htdemucs → Mega-53 → rebuilds (H, M, and X if added) → the
       stage-F rebuild checks;
     - **render lane:** stage D shards 0/3 and 1/3 (M, then T, X if added); shard 2/3 waits for lane
       A to exit;
  3. stage F, 3 shards, after every stage-D shard (cap of 3);
  4. reports and the readout in `docs/arm-a-mega53-results.md`, then an independent audit.

| Step | Renders | Hours (wall) |
|---|---|---|
| Contexts, htdemucs (35 × about 26 s), Mega-53 (35 × 80–95 s), rebuilds | 0 | about 1.2 h (CPU lane, beside 2 render shards) |
| Stage D (M, T, checks) | 15,990 | about 2.7 h (2 shards for the first 1.2 h, then 3; about 2.2k per shard-hour, step 3's arm A rate) |
| Stage F (H, M) | 23,520 | about 3.6 h (3 shards) |
| Reports | 0 | minutes |
| **Total** | **39,510** (hard caps 40,800) | **about 6.3 h from 11:00** |
| Arm X, if added | +19,537 (caps +20,300) | +3 h |

- **Renders so far:** about 201k once 1d finished ([ROADMAP](ROADMAP.md), 2026-10-17); this plan
  adds about 30k (amendment 1), or about 45k with X (1d gave no arm X). There is no fixed limit (decision 2).
- **Disk:** about 1.5 GB at most (35 contexts and 2–3 stems of 30 s float32 ≈ 0.6 GB; rebuilds
  ≈ 0.4 GB; final-output FLACs ≈ 0.5 GB). 58 GB free when this plan was written, against the 31 GB
  guard, which every shard checks.

## Code (after review, before any render)

`learn/arm_a_mega53.py`, reusing `arm_a_levers` (`main_stage`, `shrink`, the units, `effects`),
`local_objective` (`rebuild_from`, the process checks), `local_objective_1c` (`ROWS`, the bleed
table, Fieller), `local_objective_1d` (`assert_sepnet_ok`, the pinned nets), `learn.separate` and
`separator_screen`:
- `decide-x` (zero renders), `contexts`, `separate --sep htdemucs|mega53`, `rebuild --sep
  htdemucs|mega53|x`, `check-inputs` (zero renders: held-out assertion, leak assertions, rebuild
  checks), `search --stage D|F --shard i/n`, `report --stage D|F`.

`tests/test_arm_a_mega53.py`:
- the fresh pool: 35 parts, 17 bands, the F-song and F-band lists, none in step 3, every session
  `development`, no Guitar-TECHS P3, no set 4–6 part;
- the band order (seed 20261035) and the precision stop on a toy table;
- the recipe: `main_stage` + shrink + fallback reproduce the stored 3-C′ shrunk settings for H
  from the stored objective curves (zero renders);
- the fallback rule on toy renders (silent, refused, normal);
- `decide-x` on toy reports (each branch, and incomplete);
- the drop rule, the rows (each bleed rule) and Fieller's shapes, reusing 1c's tests' fixtures;
- the render counts per stage against the table above.

## Seeds

- Searches: 20261013 (arm A's and K_S's).
- Stage D repeat-check draw: `random.Random(20261034)`.
- Stage F band order: `random.Random(20261035)`.
- Nothing else is random; separation and rebuilds are deterministic on the CPU (1c's identity was
  exact at fixed threads).

## Stated limits

- **Stage D is post-hoc and unblinded** (see above). Its two selection biases are named; neither is
  corrected.
- **Stage F is fresh for this question only:** its parts were used to build menus, banks and the
  bleed table, and 21 of 35 share a mix with a step-3 part. F-song is the cleaner row, at 7 bands.
- **One take per part, one seed per search;** the search's own noise is in the intervals, not
  separated.
- **The truth is the judge, not listening,** and the bleed parts' truth carries other instruments.
- **Mega-53's training data is unstated;** a leak can't be ruled out. htdemucs trained on the
  MUSDB18-train songs (row without them).
- **Stage D's T arm uses the amp track as its stem:** no song provides it. It is an anchor, not an
  option.
- **The output space is arm A's** (knob ceiling's `space`; pedals, EQ and effects kept from S).

## Amendment 1 (2026-10-17, review changes, before any separation or render)

The independent review approved the plan with 8 required changes. All are made here; nothing has
been separated, rebuilt or rendered. Where this amendment and the text above differ, this governs.

**1. Stage F's usable pool: 21 parts, 12 bands, 126 directions (was 35, 17, 210).**
- The label table's stored S scores (`label-table/<part>/menu.json`, `flat`: the same
  `aligned_distance`, measure DI and `judge_lag` as `knob_ceiling.judge`) refuse S on at least one
  half for 14 of the 35 parts, on all three amps (verified independently of the review):
  - both halves: Prodigal ElecGtr2, Signs ElecGtr6, Hikikomori, Lost Alive, Measurements, Until I
    Get Back;
  - one half: Drag Me Down ElecGtr3 (A), It Was My Fault ElecGtr4 (B), Nosso Mundo (A), Passing
    Ships ElecGtr3 (A), Prodigal ElecGtr1, 3 and 4 (A), Honey (B). Most of these halves are silent
    in the amp track (the bleed table flags them), so there is no guitar to search on.
- **The rule (mechanical, zero renders, step 3's):** a part enters stage F only if S's stored
  score is finite on both halves for all three amps. Step 3 excluded Honey on the same grounds.
  The parts failing it are neither separated nor rendered.
- **The pool:**

  | Band | Parts |
  |---|---|
  | Atlantis Bound | It Was My Fault ElecGtr3 |
  | The Travelling Band | Passing Ships ElecGtr2, ElecGtr4; Quicksand ElecGtr2 |
  | Zeno | Signs ElecGtr3 |
  | Eat The Feeder | Today's The Day ElecGtr07; wickerman elecgtr1, 2, 3, 7 |
  | Diesel13 | colour-me-red elecgtr02, 03 |
  | Wall Of Death | femme elecgtr5 |
  | Magician's Nephew | get-out-of-bed elecgtr2 |
  | Szymon Skiba | let's dance elecgtr3, 4 |
  | Turbosauro | magilla elecgtr1 |
  | Dom McLennon | Gym Hours GTR_2; Russian Cream GTR_1 |
  | Bernard Purdie Tribute All-Stars | She's Gone |
  | Doom Flamingo | Strangest Places |

  11 clean and 10 crunch; 17 Cambridge, 4 Telefunken. 10 of the 12 bands are among step 3's 14.
- **Rows restated:**
  - **F, all usable (declared):** 21 parts, 12 bands (11 df).
  - **F-song** (no step-3 part in the same song): wickerman ×4, let's dance ×2, Strangest Places,
    She's Gone: 8 parts, 4 bands. Descriptive only.
  - **F-band is dropped as a row:** 3 parts in 2 bands (let's dance ×2, She's Gone). They are
    listed per part instead.
  - **(b) no high bleed:** Russian Cream GTR_1, She's Gone and Strangest Places read high on both
    halves, so the row keeps 18 parts in 10 bands. The text above about Lost Alive and Until I Get
    Back is void: they are not in the pool.
- Experiment 4 step 5's reserved bands: stage F now spends 7 of their parts, in 6 of its 8 bands
  (It Was My Fault ElecGtr3, Signs ElecGtr3, femme elecgtr5, get-out-of-bed elecgtr2, magilla
  elecgtr1, Gym Hours GTR_2, Russian Cream GTR_1).

**2. The held-out assertion reads both catalogues and fails closed.**
- Sets 1–2 sessions are checked in `docs/validation-datasets.json`; the set-3 parts (colour-me-red
  ×2, femme, get-out-of-bed, let's dance ×2, magilla, wickerman ×4) in `docs/validation-set3.json`
  and `docs/set3-heldout-use-ledger.json`. That ledger counts uses, not sessions, so the real check
  is `validation-set3.json`'s `split` field and its empty `held_out_uses`; the code says so.
- Every session must be found and be `development`, with no `held_out_uses` entry; a session not
  found stops `check-inputs` (it can't pass vacuously). No Guitar-TECHS P3, set 4, 5 or 6 part.
  All 21 are development (the review checked the 35).

**3. The primaries depend only on H, M and S.**
- The drop rule applies per contrast: P_D and P_F use the directions where H, M and S all score;
  T's and X's contrasts use their own intersections. A descriptive or conditional arm can't change
  a primary.
- Stage D's 142 units are inherited from step 3 (its 2 directions were dropped because the
  150-render arm A's renders were refused there), not produced by this plan's rule.

**4. Stage F is a fixed set; the precision stop is withdrawn.**
- With 12 bands and a band SD of the paired contrast near 0.06, the 90% half-width is about
  1.796 × 0.06 / √12 ≈ 0.031: the 0.025 rule could not fire before the pool ran out, and stopping
  on a small-sample SD would undercut the interval's coverage.
- So stage F, like stage D and 1c, is the whole usable pool, declared now. Only breakage stops it.
  The evidence-based stop is the search's (the 52-render main stage). The band-order seed 20261035
  is no longer used.

**5. Power, stated before the budget is asked for.**
- **P_F (12 bands, 11 df):** the effect detectable with 80% power is about 0.046 at a band SD of
  0.06 and about 0.077 at 0.10 (the levers' A − S band SD is about 0.11). P_D (14 bands) is a
  little better: about 0.042 and 0.07.
- **A rough prior expectation:** the levers' slope (−0.026 in gain per +0.1 of *menu* fidelity)
  times 1c's +0.109 of *local* fidelity is about −0.03. Different fidelities, so very rough.
- **So the likely readout is a tie, and by the user's rule htdemucs then stays.** What the test can
  show is a large song-level gain (about half of arm A's −0.083 or more), or a large loss. It also
  gives the first fresh-draw estimate of the adopted recipe on full mixes (H − S), which is needed
  before shipping whatever the separator result. This is stated so the user can weigh about 30k
  renders against it before the run.

**6. The CPU gate, declared (the code's own, tested).**
- `local_objective._wait_cap` waits while any separation runs, so it is not reused as is.
- **A render shard starts** only when fewer than 3 render processes run machine-wide, or fewer than
  2 while a separation runs. It waits otherwise.
- **A separation starts** only when at most 2 render processes run, and with 1c's memory gate
  (about 11 GB available for Mega-53's pruned head; no training job; no other separation) and the
  256 MB swap guard. htdemucs (2 threads) uses the same gate.
- A test covers both gates on toy process lists.

**7. The stage-F rebuild is generalised and checked for identity.**
- `rebuild_from` loops over step 3's parts and loads step 3's stem rebuild for its GCC check; the
  fresh parts have none. The new rebuild takes any part list and source, with the GCC and level
  checks paired between a part's H and M rebuilds (as the plan states).
- **Identity check (zero renders, before any render):** on step 3's 24 parts, the generalised
  rebuild must reproduce the stored `song-settings/rebuilt/` (htdemucs stem) and 1c's
  `rebuilt-mega53/` within 1e-6, as amendment 4a did.
- **The fold** of every part comes from `song_settings.folds()` (`docs/song-settings-folds.json`).
  `validation-set3.json`'s own fold column disagrees for Diesel13, Wall Of Death, Szymon Skiba and
  Turbosauro; the leak check passes either way, but the re-EQ depends on the fold.

**8. Process.** Section 5's "plan, review, message the product session, run, audit": a message to
the product session (the plan, its renders and its CPU lane) is sent before any separation, and
the order below includes it.

**Also taken from the review's suggestions:**
- **Two descriptive rows:**
  - **without any MUSDB18 song:** also leaves out Zeno's Signs (in MUSDB18 *test*). Mega-53's
    training data is unstated, and many MSST models train on MUSDB18-HQ including its test split;
  - **SNR ≥ 1 dB** of the label table's htdemucs instrumental stem against `reference.wav` (step
    3's selection rule; zero renders), to bridge P_D and P_F.
- **`decide-x` reads `report-1d.json` as it stands at launch** (before 1d's audit). A later audit
  correction does not revisit X; it is reported beside.
- **Limit:** C′ never saw stems from mixes with vocals. Any edge Mega-53 gets from rejecting vocals
  is part of the product effect, not a confound, but it is named.
- **T is kept** as the null's anchor; dropping it would save about 7.9k renders and 1.2 h, the
  user's call.

**Renders and hours, restated** (about 2.25k renders per shard-hour, step 3's arm A rate):

| Step | Renders | Hours (wall) |
|---|---|---|
| Lane A: 21 contexts, htdemucs (about 26 s each), Mega-53 (80–95 s each), H and M rebuilds, checks | 0 | about 0.8–1.0 h (beside 2 render shards) |
| Stage D: M 7,882; T 7,882; H's fallback checks 214; repeat check 12 | 15,990 (cap 16,500) | about 2.7 h (2 shards while lane A runs, then 3) |
| Stage F: 63 part-amps × 4 (measure-DI warm-up, S judge, two rebuild warm-ups) + 126 × 2 × 55 | 14,112 (cap 14,600) | about 2.1 h (3 shards) |
| Reports | 0 | minutes |
| **Total** | **30,102** (caps 31,100) | **about 4.8 h from 11:00** |
| Arm X, if added: stage D 7,882; stage F 63 + 126 × 55 = 6,993 | +14,875 (caps +15,500) | +2.2 h |

Disk: under 1 GB now. 56 GB free at this amendment, against the 31 GB guard.

**Order, restated:**
1. this plan, review, ledger (done before any render); the code and its tests, including the
   identity check, the held-out and leak assertions and the gates;
2. a message to the product session;
3. after 1d's report: `decide-x` (recorded in the ledger as `arm_x`), then lane A beside stage D's
   shards 0/3 and 1/3; shard 2/3 starts when lane A exits;
4. stage F, 3 shards, after stage D;
5. reports, `docs/arm-a-mega53-results.md`, an independent audit.
