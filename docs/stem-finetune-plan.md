# Step 6: fine-tune on what the product feeds (plan)

**Status:** stages 0 and N run and audited 2026-11-18 ([results](stem-finetune-results.md)): S0-ok, then **N-quiet** by the score (N +0.003 [−0.004, +0.010]); Step 6 stops and hands back, as declared, and the pilot waits for the user's answer to open question 1; declared 2026-11-17 for **stages 0 and N only** (section 5.1; section 5.2 says how they are built). The
plan was a planner's draft, revised the same day after its independent review (approve with changes; section 15 lists
the changes) and approved on the re-check (round 2: APPROVE, no blocking items). **The pilot and the full run wait for
the user's answer to open question 1** and are not built. **By the user's word (2026-11-17), no decision is taken from
stage N's result until a separate listening check of whether the score can be trusted at small differences**; stage
N's hand-back reports numbers only. It is Step 6 of the plan the user approved after the 2026-11-16 review, reached by
the ladder's stop rule, branch 3 (`docs/preset-ladder-plan.md` section 15) and Step 5's stage 0 stop (S0-flat, pending
the user). Every number is by the score unless it says "by ear": J0, ln(d_row / d_against) on the held half, below
zero closer; 90% cluster t intervals; the deciding pool is BKS, GOAT and the panel weighted equally; the heard-size
floor is −0.05. `PF` is `~/ndsp-presets/learn/trusted-data/pipeline-fix`.

- **Ledger:** `pipeline-fix` holds `phase_s6` (the rule and the tables) and `phase_s6_noise` (stages 0 and N's
  training); later, only on the user's answer, `phase_s6_stems`, `phase_s6_pilot`, `phase_s6_train`. `preset-ladder`
  holds stage N's reads (`phase_l6_noise`; later `phase_l6_pilot`, `phase_l6`). Each is declared and reviewed before
  its run.
- **Code:** `learn/stem_finetune.py` (the tables, stage 0, stage N's answers and report), the `train-ft --c3r-rep`
  path in `learn/pipeline_fix.py`, and Step 6's rows in `learn/preset_ladder.py` (`L6_MODEL_ROWS`, `L6_RC_ROWS`);
  tests `tests/test_stem_finetune.py` (pure, light CI) and `tests/test_train_ft_rep.py` (torch). Data `PF/step6/`.
- **Read-only work behind the draft:** the docs on `origin/main`, the ladder's stored files, C3r's 18 run records, and
  two zero-render counts of the planner's (section 3). No render, training or separation was run for it.

## Why

R-all, the adopted model, trained on real amp tracks in non-guitar backings: no separator, no other guitar
(`pipeline_fix.cmd_build_dfix_real`, `DfixData`). The product feeds it an X-LANCE stem of a full mix
(`product_path.cmd_separate`, `cmd_answers`). The ladder measured that gap on 480 held-out parts.

| Row (ladder, deciding pool) | Result | What it says for Step 6 |
|---|---|---|
| `xl@-3 − mix@-3` (the whole stem path) | +0.086 [+0.051, +0.121] | the raw cost of the product's input |
| the separator alone, `xlnoG@-3 − mixp@-3` | +0.053 [+0.009, +0.096] | fragile, mostly crunch (+0.117); Step 6's stated target |
| `rc-xl@-3 − xl@-3` | −0.052 [−0.078, −0.027] | re-centring already wins back most of the raw cost, with no training |
| `rc-mix@-3 − rc-xl@-3` | −0.035 [−0.066, −0.004] | **the ceiling left for Step 6 after re-centring**; carried by GOAT |
| `rc-xl@-3 − cen` | +0.008 [−0.042, +0.058] | today's best readout on the stem is level with the fixed preset |
| `rc-mix@-3 − cen` | −0.027 [−0.061, +0.007] | where a perfect Step 6 would land against Cen: undecided, underpowered |
| `sic-xl@-3 − cen` against `sic-mix@-3 − cen` | +0.117 against +0.049 | on the stem the model's mean answer sits further off |

**The goal check, said first.**
- Step 6 removes a known mismatch between training and the product. It works on the input, which the outlook
  (section 13) reads as not the limit.
- **It is not shown able to make the model path beat Cen.** On the pool means, G (`rc-s-xl@-3 − cen`) equals O
  (`rc-s-xl@-3 − rc-xl@-3`) plus 0.0084. A row against a constant resolves about ±0.05, so G needs O near −0.06, past
  the −0.035 ceiling.
- **O is likely to read undecided even if Step 6 works.** A model-against-model row resolves about ±0.026, and more
  stem variants don't narrow that. By the reviewer's calculation (one tail, 5%), O clears zero about 70% of the time if
  the whole −0.035 ceiling is reached and about 30% at half of it, and less once the noise rule's second row is also
  required. G has almost no power.
- So what Step 6 can change is the model behind the flag and the base later work builds on. Whether that is worth the
  machine time is the user's call (open question 1), and the pilot waits for it.
- It converges: every stage has a stop, and no cell loops back.

## How this differs from what came before

- **P2d and D_CC (October)** trained on X-LANCE stems, with plugin-rendered targets only. Dropped on 31 October.
- **D_fix, FT, FTm, C3, R-all** train real rows as guitar plus backing, summed. None passed a separator or held another
  guitar.
- **N5 and N5b (F55, F56)** read FTm on stems of mixes with no other guitar and found no cost. The ladder found one for
  the separator alone (+0.053), also with no other guitar. What differs from N5 is the exposure, the model (R-all, every
  control) and crunch (+0.117). With other guitars the whole stem path costs +0.086.
- **The re-centred answer** moves the model's mean after training, with a per-part table that is optimistic for the
  product. Step 6 changes what the model is trained to read.
- **Step 5** changes the labels. Step 6 keeps the raw labels.

**Why it may still fail.**
- The ceiling is small and sits inside the heard-size floor, and the read's power is low (above).
- The reader is the limit, not the input: on an isolated guitar the model reaches about Cen (`clean@-3 − cen` +0.001
  [−0.051, +0.052]; an input it never trained on, so confounded).
- X-LANCE keeps every guitar. In the ladder's mixes the target sits a median +0.4 dB over the other guitars (quartiles
  −1.2 and +4.4; the planner's count from the 400 build records). Where the other guitar is as loud, no input tells the
  model which one is the target, so training can only teach the mean there (F61: a linear reader leans to the louder
  guitar).
- Two trainings of one recipe have never been compared. A gain of 0.03 may be inside that noise (section 4).

## 1. What it trains

**Two changes from R-all, not one:** the input (stems among the showings), and E chosen on stems. Both are named in
every write-up, and the second is reported apart (the last row below).

| Part | Declared choice | Why, by evidence |
|---|---|---|
| **Base** | R-all's recipe, its fine-tune stage again from W: `train-ft --masked --ft-cap 300 --c3r all`, W's NS-best state per seed, seeds 20261042 and 20261043, C3r's folds, drops, masks and two-source epoch mix, the answer's hold C3-cabS | Step 5 produced no new model (S0-flat). The review asks for the fine-tune stage alone. Continuing from R-all's fold checkpoints is not proposed: fold model k trained on fold k+1, which inner run k validates on. |
| **Rows and labels** | C3r's 665 trusted records on **461 units** (BKS 102, GOAT 214, cap1 121, n12 12, the panel 12), on their raw C2 and C2r labels | The reviewed trusted set. The stems don't depend on the labels, so a later change of targets does not redo them. |
| **Stems** | The product's default only: X-LANCE `gtr_mss` on the mix's mid, read at the product's level (the mix brought to −12.25 LUFS, the stem by the same gain, `step4_half`), both halves | `product_path`'s default input is the mono stem. The level step costs nothing (+0.001 [−0.005, +0.006]). |
| **Not trained: side-picker versions** | none | The side picker is not in the product (`product_path.VERSIONS`). The ladder's layout puts the target in the centre, so a side pick would return the other guitars under the target's label. The side may hold a different guitar part, so its different answers are not an instability to train away. Section 6 tracks the R1 finding beside. |
| **Not trained: `xlst_mdxc`** | none | Behind a flag, not the default. On the exam it read M-x − M +0.153 [−0.032, +0.338]. |
| **Other guitars** | Real amp units as donors (section 3), none, one or two a variant | Real songs' other guitars are real amps. The ladder's six lender sessions can't be used: the read sits on them (section 3). |
| **Variants** | 8 stem variants a unit (table below); the first 2 are the pilot's | The review's count. |
| **Showing rule** | Each epoch, a training real row shows a stem variant with probability 1/2 (uniform among the unit's built stem variants), else its D_fix backed variant exactly as R-all drew it (`dfix_variant`). Both draws are seeded by the row and the epoch, not by the run's seed. | The pilot and the full run are then one recipe at two doses, and a loss on the old input shows (section 6). **The 1/2 is a declared constant with no measurement behind it.** The product never feeds the backed mix, so stems only is the goal-direct choice (open question 4). |
| **Validation (inner runs)** | Fold k+1's rows on their stem variant 0; E by R-all's rule (the first argmin of the trailing 3-epoch average, patience 15, cap 300). | E is chosen on the input the product feeds. **This is the second change.** |
| **The second change, reported apart** | The backed loss R-all tracked is logged every epoch beside the stem loss, and per-head losses on both. For every inner run the report gives **the E R-all's backed rule would have picked** (`ft_inner_E` on the backed track) beside the E used. | So a reader can tell how much of a difference could be the epoch count alone. C3r showed that matters: part of R-all − R-ctl was R-ctl's early stop (F77). No extra training is spent on it; if the two E's differ widely, that is said and goes to the audit. |

**The 8 stem variants of a unit** (each a 10-s mix, built by the ladder's `lender_mix` path with two substitutions: the
backing and the other guitars):

| Variant | Other guitars | Target against everything else, on the mid | In |
|---|---|---|---|
| 0 | one donor | −3 dB (the ladder's exposure) | the pilot and the full run |
| 1 | none | −3 dB | the pilot and the full run |
| 2, 4, 7 | one donor | drawn uniformly in −9 to 0 dB | the full run |
| 3, 5 | two donors | drawn uniformly in −9 to 0 dB | the full run |
| 6 | none | drawn uniformly in −9 to 0 dB | the full run |

- **The target:** the unit's amp section (`real_amp_track`), levelled as D_fix levels it (`dfix_level`, by its D_fix
  lending example, which lends numbers only: the target loudness, the mix loudness and the mastering draw).
- **The backing:** a wide-pool entry from the 13 "extra" sessions only (229 windows of the 406), a session drawn
  uniformly, then a window, vocals with probability 0.5, as `dfix_draws` draws, and never the unit's own session.
- **The donors' level:** the target-to-other-guitars ratio is a seeded pick from the 400 ladder builds' recorded values
  (5th to 95th percentile −1.9 to +8.4 dB). Only level statistics are borrowed, no audio. It does match training to the
  read's conditions (section 11).
- **Layout and mastering:** the ladder's (target within ±0.15, donors on one side at ±0.6 to ±1.0, the backing by
  `sep_s0.backing_pan`, the ratio set on the mid, the lender's mastering draw).
- **Recorded per variant:** the built ratios, the stem's loudness less the mix's, SI-SDR and the donors' leak on half A,
  and whether the window would pass the product selector's guards (`steady_whole`, within 12 dB of the mix). Nothing
  is filtered on them.
- **Stored:** features only (about 60 KB a variant, as the ladder's `feats/`); no audio.

**The separations count is by unit, not by record.** BKS's three amp records share one unit's audio. So the build is
461 × 8 = **3,688 separations**, not the review's 5,500 or the earlier draft's 5,320. The pilot's share is 922.

## 2. The read rows

The read uses the ladder's 480 parts on 400 units, each answered by its own fold's pair from the ladder's **stored**
`xl@-3` and `mix@-3` features: zero separations. R-all's rows (`xl@-3`, `rc-xl@-3`, `mix@-3`, `rc-mix@-3`, Cen, S, the
label, their constants) are stored and hash-checked before any report. Statistics are exactly the ladder's
(`rows_for_pair`, `summarise`).

| Model | Runs | Prefix |
|---|---|---|
| R-rep, the noise repeat: R-all's recipe, two new seeds | 8 inner, 8 fold; the pair only if the full run goes ahead | `rep-` |
| R-stem2, the pilot: stem variants 0 and 1 | 8 inner, 8 fold | `s2-` |
| R-stem, the full run: 8 stem variants | 8 inner, 8 fold, the pair | `s-` |

`rc-` rows are re-centred by the ladder's `recentre` ("rule"), each model with its own same-input constants.

## 3. Leakage, against the ladder's held-out parts

The ladder's 480 parts stay held out of every model that is read on them. Each line below is a coded refusal
(`leak_refusal`), checked before the stem build and again by every training run. The review verified L1 to L6.

| # | Rule | How it is met |
|---|---|---|
| L1 | No read part's unit, DI file or creator trains in the model that reads it | C3r's rotation unchanged: `split`, `rows_for`, `check_rows`; each part is read by its own fold's pair |
| L2 | A held unit's audio never enters its fold's runs as an other guitar | A donor d for target u is of **u's own fold and class**, shares no DI file or creator with u, is not from u's song session (BKS, the panel), and **trains in every run where u trains** |
| L3 | The read's other guitars and backings are not trained on through the separator | The read's inputs sit on six lender sessions (118 of the pool's 120 sections lend). No stem variant uses a lender example's `others` render, its amp tracks or its session's backing: donors are real units, and stem backings come from the 13 extra sessions, which hold none of the six lender sessions, no BKS session and no panel recording |
| L4 | An inner run's validation inputs hold no fold-k audio | Follows from L2: a validation unit's donor is of its own fold, k+1 |
| L5 | No stem of a held unit is loaded by its fold's runs | As `DfixData`: variants are loaded for training units only |
| L6 | The read's inputs are the ladder's, untouched | The stored `feats/xl@-3` and `feats/mix@-3` hashes equal the ladder reports' `sources_sha256` |

- **L2 is feasible (the planner's count, zero renders):** every one of the 461 units has at least 10 such donors
  (quartiles 20, 26 and 38). The donor pool is GOAT 50%, BKS 32%, cap1 12%, the panel 5%, n12 2%.
- **Why not the ladder's 800 stored stems as training inputs (a zero-separation pilot):** their lender sessions cross
  every fold, so a model would be read on the very sessions it trained through. Rejected: its "yes" could not be told
  from familiarity with those six sessions.
- **What stays shared, in both arms alike:** R-all's backed variants already draw from the lender sessions' backings
  (the wide pool's 177 "training" windows). Step 6 keeps those variants as they are, so the comparison with R-all is
  like for like. The read stays conditional on the six lender sessions, as the ladder says.
- **The direction of the remaining mismatch:** training's other guitars are real amp units, the read's are plugin
  renders and session amp tracks. A gain is then out of sample in kind; a null may partly be that mismatch.

## 4. The noise gauge (stage N)

R-all's recipe has never been repeated, so how far two trainings differ by the score is unknown. Every row that
compares two trainings rests on it. Three gauges, cheapest first:

| Gauge | What | Cost (measured) |
|---|---|---|
| Seed to seed | Each fold pair's two seeds answered apart on the stored `xl@-3` and `mix@-3` features: the distance between seeds, per knob group, beside the distance between inputs (0.041 to 0.044) and between parts (0.039 to 0.044) | zero renders; the ladder made 4,800 answers in about 30 s |
| Same-seed replay | Fold 3's inner and fold run for seed 20261043 trained again with nothing changed, under its own name; the answers' distance to the stored run's | 11.9 run-minutes as logged (6.8 + 5.1); zero renders |
| **The repeat, R-rep** | R-all's recipe on the same rows and labels with two new fine-tune seeds, each starting from one of W's two states (the seeds are named in the phase). A run's seed sets the epoch order and torch's seed; the variant draws don't follow it. The 16 fold and inner runs. | 114.4 run-minutes as R-all's own runs logged; a row is 1,920 renders, 27 min |

**Correction (2026-11-18, the stage N audit):** the seed-to-seed row's "between inputs (0.041 to 0.044)" and "between
parts (0.039 to 0.044)" are the ladder's stage 0 inputs (`mix-drawn`, `clean-kind`, `xl-v0`). For `xl@-3` against
`mix@-3` they are 0.060 and 0.039 (mix) or 0.048 (xl), from the ladder's stage 2 report.

- **N:** `rep-xl@-3 − xl@-3`, the row `N_TABLE` reads. It is one draw of the noise: a size, not a distribution.
- **Beside, rendered at stage N:** `rc-rep-xl@-3`, for `rc-rep-xl@-3 − rc-xl@-3` (the noise on O's own row) and
  `rc-rep-xl@-3 − cen` (a second draw of the goal row, +0.008 today).
- **Beside, optional (the lean review keeps or drops it):** `ens4-xl@-3`, the four seeds of R-all and R-rep pooled, for
  `ens4-xl@-3 − xl@-3`. It reads model variance as a lever at no extra training. 1,920 renders, 27 min.
- **What this noise is.** R-rep shares W's two states and D_fix's variant draws, so it measures the fine-tune's seed
  noise only. That is the right noise for Step 6, which changes the fine-tune alone. It is not the noise of the whole
  pipeline, and the write-up says so for any other use.
- **What one draw can and can't say.** With no real noise, N still reads "loud" about 10% of the time (a two-sided 90%
  interval). "Quiet" does not bound the noise; it gives one interval.
- **The noise rule.** A reading of a row that compares R-stem (or R-stem2) with R-all counts only if the same row
  against R-rep reads the same way. Otherwise the action does not fire: the write-up says "not separable from
  training noise" and the choice goes to the user.
- **Code change:** `train-ft` refuses seeds outside `SEEDS`. The repeat needs a reviewed change that maps each new seed
  to a W state and gives the runs their own base name, so no R-all file can be overwritten.

## 5. Stages, costs and stops

Measured rates, with their sources:
- **Separations:** 4.6 s a stem on the MPS (ladder stage 2: 800 in 61 min; A2s: 386 in 30 min).
- **Fresh primed renders, the read's kind:** about 70 a minute on 3 shards (ladder stage 1: 8,640 in 2 h 4 min;
  stage 2: 12,480 in 3 h 4 min). One row is 960 answers, 1,920 renders, 27 min. The searches' in-process rate of 6,200
  to 6,600 an hour does not apply to a read.
- **Training, measured for R-all only:** its 18 runs logged 128.0 run-minutes (inner 61.4, fold 53.0, the pair 13.6),
  with the two seeds running side by side (both arms' 34 runs in 2 h 7 min of wall time). One job at a time is not
  measured. R-rep's figure is that same recipe again. **R-stem2's and R-stem's figures are R-all's by analogy, not
  measured:** E may differ, and each inner epoch adds a second validation pass.
- **Mix builds:** 0.4 to 0.7 s a unit's two mixes (the ladder's dry run).

| Stage | Gate | What | Separations | Training | Renders | Stop |
|---|---|---|---|---|---|---|
| 0 | ledger and a lean review | Section 5.1 | 0 | 0 | 0 | `S0_TABLE` |
| N | S0-ok | R-rep's 16 runs, the same-seed replay, the answers, `rep-xl@-3`, `rc-rep-xl@-3` (optional `ens4-xl@-3`) | 0 | 114.4 + 11.9 run-min | 3,840, 55 min (optional 1,920 more) | `N_TABLE`, then **the user** |
| P, the pilot | **the user's answer to open question 1**, and N-quiet | The donor draws, L1 to L6, the variant table, a dry build of 10 units; stem variants 0 and 1 for every unit; R-stem2's 16 runs; `s2-xl@-3` and `rc-s2-xl@-3` | 922 (71 min) | 114.4 run-min, by analogy | 3,840 (55 min) | `P_TABLE` |
| F, the full run | P-go, under the user's same answer | Variants 2 to 7; R-stem's 18 runs and R-rep's pair; pass a: `s-xl@-3`, `rc-s-xl@-3` | 2,766 (3 h 32 min) | 128.0 + 13.6 run-min, by analogy | 3,840 (55 min) | `S6_TABLE` |
| F, pass b | G, O or W decided | `s-mix@-3`, `rc-s-mix@-3`, `sic-s-xl@-3` | 0 | 0 | 4,800 (69 min) | cannot change the cell |

At most 3,688 separations (4 h 43 min), 382 run-minutes of training and 16,320 renders (about 3 h 53 min), plus the
optional row. Stages 0 and N spend no separation.

### 5.1 Stages 0 and N: the scope to build now

| # | Deliverable | Cost |
|---|---|---|
| 1 | Ledger: `phase_s6` (this plan's rule and tables), `phase_s6_noise`, `phase_l6_noise`, declared before any run; the two new seeds named there | none |
| 2 | `S0_TABLE`, `N_TABLE`, `P_TABLE` and `S6_TABLE` as coded constants with tests and a `table_guard` (every cell exactly once; a missing cell refuses). `P_TABLE` and `S6_TABLE` are coded now so they can't be shaped by stage N's result; nothing else of the pilot is built. | none |
| 3 | Stage 0 controls: C3r's state hash equals the ladder's; the ladder's controls passed; the stored rows' and features' hashes equal the ladder reports' `sources_sha256` (no such field exists: section 5.2 gives the stronger substitute); free disk against the 31 GB guard | CPU seconds |
| 4 | The seed-to-seed gauge: per-seed answers of R-all's eight fold pairs on stored `xl@-3` and `mix@-3` | zero renders; about a minute |
| 5 | The reviewed `train-ft` change: two new seeds, each mapped to one W state, under base `C3r-rep`; a same-seed replay under its own base. A test that no existing run file can be written. | none |
| 6 | Training: R-rep's 8 inner and 8 fold runs, then the replay's 2 runs, one MPS job at a time | 114.4 + 11.9 run-min as R-all logged |
| 7 | Answers: `rep-xl@-3`, `rep-mix@-3`, R-rep's same-input constants, `rc-rep-xl@-3` (optional `ens4-xl@-3`) | zero renders; about a minute |
| 8 | Renders, 3 shards: `rep-xl@-3`, `rc-rep-xl@-3` (optional `ens4-xl@-3`) | 3,840 renders, 55 min (optional 1,920, 27 min) |
| 9 | `report`: the `N_TABLE` cell, read only after the rows are saved; N, the two beside rows, the replay, the seed-to-seed gauge; the cell's hash in the ledger | seconds |
| 10 | Hand-back, then the independent audit, then **the user**: open question 1, with N | none |

Not in this scope: the donor draws, the stem build, any separation, the R1 versions read and any V-real read.

### 5.2 Stages 0 and N as built (declared with the code)

- **The seeds and names.** R-rep's fine-tune seeds are **20261181** (from W's NS-best state of seed 20261042) and
  **20261182** (from W's of 20261043), base `C3r-rep`. The same-seed replay is fold 3's inner run and FT_3 for seed
  20261043, base `C3r-replay`. A run's seed sets torch's seed and the epoch order; D_fix's variant draws and C3r's
  source orders are seeded by the row, the epoch and the fold, so they are R-all's exactly.
  `stem_finetune.rep_write_refusal` stops a run whose name is not its base's, or whose files exist, before any work;
  `rep_refusal` allows R-all's recipe only (`--c3r all` on C3's recipe), fold runs only, R-rep's seeds only and the
  replay's one fold and seed. R-rep's FT_k reads its own base's inner runs only. The tests show no R-all name can be
  made and a dry pass over every run changes no file.
- **Commands.** `train-ft --masked --ft-cap 300 --c3r all --c3r-rep rep --seed <seed> --real-fold <k> [--inner]`;
  the replay with `--c3r-rep replay --seed 20261043 --real-fold 3`. One MPS job at a time: the 8 inner runs, then the
  8 FT_k, then the replay's 2 (`learn/step6_noise_train.zsh`, the disk guard checked before each run). Then
  `stem_finetune answers`, the renders on 3 shards, and `stem_finetune report-n`.
- **Stage 0's hash control.** The ladder's reports hold no `sources_sha256` of the features; only the re-centred
  answers' files hold one, of their source answer files. So stage 0 checks: the re-centred rows' `sources_sha256`
  equal today's files; R-all's pairs reproduce the stored `xl@-3` and `mix@-3` answers bit for bit from the stored
  features (which no changed feature file or model could do); every stored row's judge files were made from today's
  answers; report-rc's `rc-xl@-3 − cen` and `rc-xl@-3 − xl@-3` re-derived field by field. A manifest of every
  C3r-all and C3r-ctl run file, the two inputs' feature files and the stored answer files is saved; stage N's answers
  refuse if any changed.
- **The rows.** `rep-xl@-3` (R-rep's pair), `ens4-xl@-3` (R-all's and R-rep's four seeds pooled), `sic-rep-xl@-3`
  and `rc-rep-xl@-3` (the ladder's own `cmd_sic` and `cmd_rc`, Cen unchanged: the same training rows). **`ens4-xl@-3`
  is kept** (section 4's optional row; the review: "the one free test of model variance"), so stage N renders 5,760:
  3,840 for the two declared rows and 1,920 for `ens4`, about 82 min at the measured 70 a minute.
  **`ens4` has no table:** it is read as a beside row only, and any action from it needs its own declaration.
  **`rep-mix@-3` is dropped:** no stage-N row reads it (the review).
- **Gates and pins (PR review).** Every `--c3r-rep` run refuses unless stage 0 read S0-ok (so stage 0's manifest is
  taken before training), and unless its rate and cap are R-all's, (1e-4, 300); `stage N's answers` also refuse a run
  whose rate, cap, mask or real-row share differs from R-all's same fold's record. `report-n` re-checks the
  comparators (`xl@-3`, `rc-xl@-3`, Cen): their answers as stage 0 hashed them and their judge files made from them.
- **What a smoke pass showed (before the declaration, no result read).** Stage 0's 17 controls run on the stored data
  in 42 s with the cell and the gauge skipped. Stage N's answer path, with R-all's own runs standing in for R-rep's,
  reproduces `xl@-3`, `sic-xl@-3` and `rc-xl@-3` exactly.

**`S0_TABLE`** (zero renders):

| Code | When | Next |
|---|---|---|
| S0-fail | A control fails or a stored hash differs | Stop. Reported. |
| S0-ok | None of those | Stage N. The seed-to-seed distances are reported, with no reading attached. |

**`N_TABLE`** (N = `rep-xl@-3 − xl@-3` on the deciding pool):

| Code | N | Next |
|---|---|---|
| N-quiet | undecided | **Stop and hand back. Nothing starts by itself.** The half-width and what the interval rules out are reported as the noise's size. The pilot starts only on the user's answer to open question 1. |
| N-loud | better or worse | **Stop.** Two trainings of one recipe differ by the score. To the user, with N, the replay and the seed-to-seed gauge: a second repeat to size the noise (114.4 run-minutes, 27 min of renders a row), or end Step 6. The write-up names the earlier model-against-model reads that carry the same doubt; none is changed. |

**`P_TABLE`** (P = `s2-xl@-3 − xl@-3`; P2 = `s2-xl@-3 − rep-xl@-3`; Q = `rc-s2-xl@-3 − rc-xl@-3`, O at the pilot's
dose; each of the 27 triples once):

| Code | P | P2 | Q | Next |
|---|---|---|---|---|
| P-go | better | better | better or undecided | The full build and run. The write-up gives what Q's interval rules out; if its lower end is above −0.035, the ceiling's mean is ruled out at this dose, and that is said. |
| P-aim | better | better | worse | Stop. The stems moved the model's aim, which re-centring gives free, and the re-centred answer got worse. To the user. |
| P-flat | undecided | any | any | Stop. To the user with the intervals: at 2 stem variants a unit the answer on the product's input is not shown to move. Underpowered if P's lower end is beyond −0.05, and said so. Not failed. |
| P-worse | worse | worse | any | Stop. R-all stays. Reported. |
| P-noise | better | undecided or worse | any | Stop. Not separable from training noise. To the user with N, P, P2 and Q. |
| P-noise | worse | better or undecided | any | The same. |

- **What the pilot can and can't decide.** Of the raw ceiling, −0.086, re-centring already gives −0.052 free. A model
  trained on stems will very likely move its mean on stems, so P and P2 "better" is the expected reading and says
  little about O. That is why Q is rendered every time and is in the table. Q itself resolves about ±0.026 against a
  ceiling of −0.035, so it mostly rules things out. **The pilot is a check that training on stems takes and does no
  harm. It is not a forecast of O.**
- **False alarm:** under no effect P-go needs P and P2, each at most 5% on one tail.

**Is there a cheaper deciding test?**
- **Stage N is the cheapest test that can stop the step**, at zero separations: it says whether one pair against one
  pair can carry a difference of the ceiling's size at all.
- **The pilot cuts the dose, not the rows or the folds.** It is the real recipe at 2 of 8 stem variants, leak-free, on
  every fold, and nested: the full run adds variants and redoes nothing.
- **One fold is not cheaper where it matters.** It needs most of the stems anyway (fold 0's runs train 259 of the 461
  units) and reads a quarter of the parts, which about doubles every interval.
- **Fewer rows** changes the recipe under test (the training set), so it is not proposed.

## 6. The read

| Pair | Role |
|---|---|
| **G:** `rc-s-xl@-3 − cen` | action: does the stem-trained model's best readout beat the fixed preset on the product's input? Almost no power (section "Why"). |
| **O:** `rc-s-xl@-3 − rc-xl@-3` | action: does it beat R-all's best readout, like for like? Ceiling −0.035; about ±0.026; likely undecided even if it works. |
| O2: `rc-s-xl@-3 − rc-rep-xl@-3` | the noise rule for O |
| **W:** `s-xl@-3 − xl@-3`, with W2: `s-xl@-3 − rep-xl@-3` | acts only inside S6-level: does the raw answer improve, as the flagged path would ship it today? Ceiling −0.086, of which re-centring already gives −0.052. |
| T: `s-xl@-3 − rc-xl@-3` | beside: the stem-trained raw answer against R-all with its (optimistic) table |
| `s-xl@-3 − cen` | beside: the raw goal row. It equals W + 0.061 on the pool means. |
| `rc-s-mix@-3 − rc-mix@-3`, `s-mix@-3 − mix@-3` | beside (pass b): did the reader lose on its old input? |
| `rc-s-mix@-3 − rc-s-xl@-3` | beside (pass b): the stem's cost that remains, which is all a separator could still buy |
| `s-xl@-3 − sic-s-xl@-3`, `sic-s-xl@-3 − cen` | beside (pass b): the per-unit reading on the stem (R-all −0.056, undecided) and where the answers' centre sits (R-all +0.117) |
| the knob reads; each inner run's two E's | beside, zero renders |

**The R1 versions read (beside, zero renders, its own declared phase line, only if the full run goes ahead).** R-stem's
and R-rep's all-labels pairs on the six stored versions of the seven R1 windows, by the declared `versions` code. It
reads stored stems only and no song file.

| Measure | R-all (audited) | Reported for R-stem and R-rep |
|---|---|---|
| pairs among the four centre versions | 0.016 | the same median |
| pairs with one side-picker version | 0.063 | the same median |
| between songs | 0.042 | the same median |

It decides nothing. It says whether stem training makes the answers steadier across the centre-route outputs, beyond
what a retraining alone moves. The side-picker pairs are reported and not expected to fall: the side may hold another
part.

**Step 1's set (V-real, sealed): one descriptive read, only under S6-adopt, S6-user or S6-build.** R-stem's all-labels
pair through the exam's stored M windows and stems (zero separations), as the exam's M and M3 arms, against the exam's
stored S, R, M, C-pick and L, hash-checked. It resolves about ±0.107, has no cells and decides nothing. The exam's
chain took 46 to 66 s a run and its whole judge pass 24 min. Under S6-level or S6-worse the set is not spent.

## 7. The outcome table (`S6_TABLE`, coded with its tests before any run)

Each of the nine (G, O) pairs appears once; a missing cell refuses; the launcher refuses unless the tests pass.

| # | G (against Cen) | O (against R-all) | Code | Next |
|---|---|---|---|---|
| 1 | better | better | S6-adopt | If the noise rule holds: R-stem replaces R-all as the adopted model (ML's reviewed change), and the re-centred R-stem path is the default candidate. That goes to the user with the ladder read, Step 1's descriptive read and the ear. |
| 2 | better | undecided | S6-user | It beats Cen but is not shown better than R-all. To the user, with both intervals. |
| 3 | undecided or worse | better | S6-build | If the noise rule holds: a gain over R-all on the product's input, not shown over Cen. By the adopt rule's second level (section 8): R-stem replaces R-all behind the flag and is the base for later work. Not the default; Cen stays Step 3's start. |
| 4 | undecided or worse | undecided | S6-level | **The likely cell, even if Step 6 works.** No change of model. Not failed: the write-up gives what each interval rules out. Then by W: **better, and W2 better:** the stems fix the model's aim on the product's input without a table; that, with T, goes to the product session as a choice for the flagged path. **Otherwise:** nothing changes. |
| 5 | undecided or worse | worse | S6-worse | Not adopted; R-all stays. "Worse" is said only if O2 reads worse too. |
| 6 | better | worse | S6-impossible | The means add: O worse puts G's mean above +0.008. The report refuses and stops. |

- **False alarms, qualified.** Under no effect G reads better at most 5% of the time, and O with O2 less than that if
  training adds no difference, which stage N measures.
- **Stop rule:** one stem build, one pilot, one fine-tune, one read in its declared passes. No share, variant count or
  exposure is tuned on the ladder's units. Any change is a dated amendment, reviewed first.
- **Negatives are read adversarially** by the audit: per set, per class, half A, each cluster and each deciding set
  left out, and without the heavier lenders. An undecided row with its lower end beyond −0.05 is underpowered.

## 8. The adopt rule: must it beat Cen, or only R-all?

| Reading | Rule | What it means here, by the measured ceiling |
|---|---|---|
| A: beat Cen **and** R-all (the review's "adopt only if it beats R-all and the centre") | Only S6-adopt changes anything | S6-adopt needs O near −0.06. The ceiling is −0.035 [−0.066, −0.004]. So under A alone, Step 6 most likely ends with no change whatever it finds, and is hard to justify running. |
| B: beat R-all only | S6-build swaps the model behind the flag | A gain of up to about 0.035 on a path that is not the default and is level with Cen, with about 70% power at best. It can't make the product's preset better today. It keeps a later reader's gain from being lost on the product's input. |

**Proposed: two levels.** The default candidate needs G and O (reading A, unchanged). The model behind the flag and
the base for later work needs O with the noise rule (reading B). **Which reading holds is the user's call (open
question 1), and the pilot does not start before it.** The table above is coded for the two-level rule and reports
both.

**A swap is not free.** The product's amp pick compares the stem with stock-DI renders in the adopted model's own
features (`product_path._feats`), so a new model changes the pick. Any swap needs the pick read again first (A2s's
read is the template), as its own reviewed change.

## 9. Machine plan

- **Limits:** one MPS job at a time; at most 3 render processes; the 31 GB disk guard; no rented machine.
- **Disk:** 46 GB free on 2026-11-17 at 20:38, down 2 GB in about half an hour from a writer this plan did not
  identify. **Every launcher re-checks the guard before it starts.** Step 6 stores about 0.5 GB: 3,688 feature files
  at about 60 KB, 28 checkpoints at 4.3 MB, and judge files. No audio. Stages 0 and N store under 0.1 GB.
- **Beside each other:** one MPS training beside 3 render processes did not slow the renders (measured 2026-11-11).
  A separation is never run beside a render (the ladder's guard; not measured), so the build and the renders take
  turns.
- **Unattended, so fit for a night:** every training, the stem build, and each row's renders. Each launcher reads its
  coded table only after the rows are saved. Reports, audits and the user's calls are day work.

| When | Runs | Time |
|---|---|---|
| The first night after stage N's ledger entry and lean review | Stage 0, then stage N: 18 trainings, the answers, two rows' renders | minutes; 126.3 run-min; 55 min |
| Then | The audit; **the user's answer to open question 1** | no machine |
| Only on that answer | The pilot: 922 separations, 16 trainings, two rows | 71 min; 114.4 run-min by analogy; 55 min |
| Only on P-go | Variants 2 to 7; 20 trainings; pass a | 3 h 32 min; 141.6 run-min by analogy; 55 min |

**Tonight (2026-11-17):** only stages 0 and N are close to runnable. They train R-all's existing recipe and need one
small reviewed change (the new seeds), their ledger phases and a lean review first.

## 10. Coverage and standing rules

- **Every control:** no control changes its status in the coverage table. Step 6 changes the input, not which controls
  are trained or written. The effects stay unlearned here, as Step 5's plan says.
- **Declared first:** every phase before its run; an independent review before each stage and an independent audit
  before each write-up, each brief carrying the goal check.
- **No pass bars:** sizes and intervals are reported. Undecided is not failed.
- **Sealed sets:** V-real only by section 6's one descriptive read. R1's audio only by the declared versions read. NS's
  loss is logged by the fold runs as R-all's were, never tracked. The reserve is not touched. Stages 0 and N touch
  none of them beyond that NS log.
- **Trusted data only:** the 665 labelled records; donors and backings come from the same reviewed units and the
  heard-clean extra sessions.
- **The public repo** gets titles and library unit ids only: no audio, path, preset or settings value.
- **Jobs:** monitoring and waits go to the executor session; no agent kills a PID it did not record at launch; the
  protected files stay (`average-fold2.npy`, the pretrain set's `recipe.json`).

## 11. What the read can't say

- The mixes are built: the target is foreign to its backing, the donors are unrelated performances, and every layout
  is centred. An off-centre target is not trained or read.
- **Training is matched to the read's conditions.** E is chosen on stem variant 0, which is one donor at −3 dB, the
  read's own exposure. The donors' levels are drawn from the read set's 400 builds. That is not label leakage, but a
  gain on the ladder may not carry to real songs' exposures.
- The read is conditional on the ladder's six lender sessions and one exposure, −3 dB.
- Every read is by the score, whose labels sit on the EQ's limits. No ear read is planned here.
- R-rep is one draw of the fine-tune's seed noise.
- A null does not separate "stems can't be learned from" from "2 or 8 variants are too few", nor a share of 1/2 from
  stems only.
- A difference may be the epoch count as much as the input; the two E's are reported for that.

## 12. Open questions

1. **For the user, and it gates the pilot:** is Step 6 worth running for the flagged model alone (reading B)? Under
   reading A it most likely changes nothing, and O is likely undecided even if it works.
2. **For the user: the learning-curve diagnostic** (section 14), in place of the pilot or before it.
3. **Donors are real units,** not the lender sessions' guitars, so training's other guitars differ in kind from the
   read's. The alternative re-reads the ladder on new lenders (800 separations and its rows again).
4. **The showing share:** 1/2 as declared, or stems only, the goal-direct choice.
5. **Step 1's read only under three cells:** the 2026-11-16 review's wording has it unconditional.
6. **The amp pick under a swap** (section 8): whose change, and is A2s's read enough?
7. **Separations beside renders** is unmeasured; the machine plan assumes they take turns.
8. **The optional `ens4-xl@-3` row** at stage N: keep or drop (1,920 renders).
9. **Step 5's line to the centre** is still with the user. Step 6's stems are valid either way.

## 13. Outlook (not a plan; nothing here is recommended to start)

**What limits the per-recording reading, by the evidence.** Steps 5 and 6 each have a small measured ceiling, and
neither is shown able to beat Cen. The headroom is real: the labels sit −0.404 [−0.458, −0.350] beyond Cen on the
ladder and −0.192 beyond S on V-real, and the model closes 7 to 15% of it on its best input.

| Suspect | Measured | Reading |
|---|---|---|
| The input | The exposed backed mix reads −0.025 against Cen and its re-centred answer −0.027, both undecided; an isolated guitar +0.001 (an input R-all never trained on, so confounded); the stem's whole cost after re-centring is 0.035 | **Not the limit.** It costs, but removing it leaves the model at about the fixed preset. |
| Features and model type | No network type or input was shown better than masked FT; a ridge on mel statistics was undecided against it; EfficientAT added 0.6% (2026-11-06). Those reads used older inputs and labels and resolve ±0.02 to ±0.05 | **Not shown to be the limit.** Not ruled out either. |
| Training | Recipe changes move 0.03 or less (C3i +0.028, C3s −0.008 and −0.019, the amp heads level). The answers' centre sits off (+0.049 on the mix, +0.117 on the stem); re-centring fixes that on the stem (−0.052) and still only reaches Cen | **Its aim was a defect, now measured and fixable. Not the limit.** |
| Label noise | A recording's other windows, averaged, sit 0.193 from a unit's own label (the centre: 0.263) yet reach 97% of the ceiling (F35, F36; BKS only). So a window's label scatters widely along directions the judge is flat on. The stored near-ties towards the centre are a small dose (−13% spread), and S0-flat rules out the rise a noise-only move would give | **Part of it:** the scatter is real, but the one cheap way of removing it is too weak a dose. |
| Data size | A per-recording reading first showed with about 160 recordings a fold (F37, −0.053 against a matched centre). R-all − R-ctl read −0.059 [−0.078, −0.040], about −0.04 where the epochs match (F77), but R-all added whole new sets R-ctl never had, so that mixes more chains with wider coverage. Real rows against none: −0.192 on V-real (F41). The one learning curve (N3) was undecided | **The only lever with a like-for-like gain, and its size is not isolated.** F36's own reading is "the model's reading or the number of recordings". |

**Plainly:** the limit is the reader's signal against its noise. A window's label is a noisy sample of its recording's
chain, and the model has 665 of them from a few hundred chains, so it learns little more than their mean (its answers'
spread is about a fifth of the labels', r +0.157 within a cell). The input is not what holds it back; the features are
not shown to. This is not proven: N3 was undecided, F36 rests on one band, and F77 is confounded.

**Three things the table above leaves out.**
- **The amp pick.** On the exam the model's pick reads at chance (undecided) while the best amp is worth about 0.07,
  more than either step's ceiling. The ladder tells each part its amp, so it can't see this.
- **The yardstick.** The panel's 5 recordings carry 89% of the goal row's variance, and the held-out bands are spent.
  No direction can be shown to beat Cen without more real-amp recordings to read on.
- **The effects** are still unlearned, against the user's rule that every control is learned.

**Three candidate directions beyond the approved steps.** Each needs the user's go; none is recommended here.

| Direction | How it differs from what failed | Why it may fail | Measured cost |
|---|---|---|---|
| **More distinct real chains.** Label and train on more trusted captures. | Every training change since F37 reworked the same 665 rows or fewer. Adding rows is the one change with a gain. | **Supply:** TONE3000's calibrated clean and low-gain rigs are mostly used after batch 3, and about 175 labelled capture units already failed the ear or DI checks. N3 was undecided; the second batch stayed undecided on 32 units (N10b); F77's gain is confounded. Captures are one family on GOAT's DIs. | Labels: C2r searched 170 records in 36,948 renders, about 217 a record, so 100 records are about 3.5 h at 6,200 to 6,600 an hour. Then one fine-tune (128.0 run-minutes) and one ladder read (3,840 renders, 55 min). The user's ear time on every capture is on top, and fetching needs a yes. |
| **Recording-level labels.** Label several windows of one chain together, and train every window on the chain's one setting. | Step 5 pulled labels towards the cell's centre, a direction the judge resists (a quarter of the way costs about +0.08 to +0.10, by a proxy). F36 shows the recording's own mean is nearly free (97% of the ceiling). No model has yet been trained on such labels: F36's +0.042 is arm R, trained on per-window labels. | It removes scatter but adds no chains, so it fails if the count of chains is the limit. Only BKS has several windows of one chain today: none of cap1's 48 captures has two records on one amp (the planner's count), and a GOAT chain has one window. | Zero renders for BKS's 102 units. For cap1, each extra window is a search: two more for each of its 121 records is about 52,500 renders, 8 to 8.5 h. Whether GOAT's or n12's chains can give more windows was not checked. Then one fine-tune and one read. |
| **Calibrate the readout on Cen, with no training.** Keep the model's deviation only for the knob groups where it pays, and scale it. | Not new: Step 5's results doc already proposed a training-free shrink. What is added is reading each knob group apart, on Cen and on the stem. | **A zero-render check predicts close to nothing** (the reviewer's): the least-squares scale is about 0.9 (r 0.157 times a spread ratio of 5.6), so the best scale is about today's, a half scale is predicted to lose, and each group explains 1 to 5% of its labels. Choosing the best of five groups on the ladder's units is selection, with no fresh set to confirm it. | Five group rows are 9,600 renders, 2 h 17 min; two scales 3,840 more, 55 min. Zero training, zero separations. The zero-render check per group comes first, in seconds. |

**Inside the approved steps, still pending the user:** Step 4's pooling over a song's windows (a single answer's
scatter costs +0.104 against Cen) and Step 5's line to the centre.

## 14. A candidate diagnostic: is more data the lever? (needs the user's go)

**2026-11-19: the user's go; declared as its own plan, [half-data-plan.md](half-data-plan.md)** (ledger `pipeline-fix`
`phase_s6_half`, `preset-ladder` `phase_l6_half`). It replaces the single half arm below with two matched arms on
complementary halves (stage N's noise result), reads `D_TABLE` under the user's rule that no action rests on a gap
under 0.05, and takes the second round's three items. The text below is the candidate as reviewed.

The review's pick. It sizes the one lever with a like-for-like gain before any scarce capture or any of the user's ear
time is spent. It uses no new label, capture, separation or sealed set.

- **What:** R-half, R-all's recipe trained on **half the chains** of each set. A chain is one recording's amp chain:
  BKS a DI file and reamp track, GOAT a capture render, cap1 and n12 a capture, the panel a DI file. A seeded half of
  the chains is kept in each set, fold and class; a chain's records stay or go together. Folds, drops, labels, masks,
  seeds, W's states and the E rule are R-all's. Each source is still cycled to 300 rows an epoch, so an epoch has as
  many updates as R-all's. The inner runs validate on the whole of fold k+1, as R-all's did.
- **Read:** the ladder's 480 parts from the stored `xl@-3` features, raw and re-centred, against R-all and against
  R-rep.
- **How it differs from what failed.**
  - **N3 (2026-11-05)** was FTm, on the core controls and older labels, read on the backed input, with no noise
    measured beside. It was undecided, "which says nothing against more rows".
  - **F77** added whole new sets, so chain count and coverage moved together. This keeps every set and halves the
    chains inside it.
  - This reads on the product's input with stage N's noise beside it.
- **Why it may fail:** with half the chains the inner runs may stop earlier, and F77 showed an early stop can pass for
  a data effect. The two models' E's are reported; an epoch-matched read would need more training and is not planned.
  One halving is one point of a curve.
- **Cost:** 8 inner and 8 fold runs, 114.4 run-minutes by analogy with R-all's; `half-xl@-3` and `rc-half-xl@-3`,
  3,840 renders, 55 min (1,920 for the first row alone).

**`D_TABLE`** (H = `rc-half-xl@-3 − rc-xl@-3`; H2 = `rc-half-xl@-3 − rc-rep-xl@-3`; each of the nine pairs once; the
raw rows are beside):

| Code | H | H2 | Reading |
|---|---|---|---|
| D-data | worse | worse | Halving the chains costs on the product's input. More chains is a live lever, and the cost of one halving is its first size. The "more chains" direction goes to the user with it, beside the supply limit. |
| D-flat | undecided | any | A halving is not shown to cost. The write-up gives the largest loss the interval allows; if that is under 0.05, doubling the chains is not shown to be worth a heard-size gain, and the limit lies elsewhere (the labels or the reading). Underpowered if the upper end is beyond +0.05. |
| D-noise | worse | undecided or better | Not separable from training noise. Reported with N. |
| D-odd | better | any | Fewer chains reads better: an early stop or noise, not a finding. Reported; nothing follows. |

- **Stop rule:** one training, one read, one cell. It changes nothing in the product. A second point (a quarter of the
  chains) is a dated amendment on the user's word.
- **Beside, zero renders:** the per-group scale check for the calibration direction.

## 15. Revisions after review (2026-11-17)

The independent review (round 1) approved with changes: stages 0 and N may go ahead after their
ledger entry and a lean review; the pilot and the full run are gated. All four blocking points and the other points
are taken.

| # | Review point | Change |
|---|---|---|
| B1 | The pilot must not start by itself on N-quiet | N-quiet now stops and hands back. The pilot starts only on the user's answer to open question 1 (status, sections 5, 8, 9, 12). |
| B2 | The pilot decides on the wrong row: −0.052 of the raw −0.086 is the aim fix re-centring gives free | `rc-s2-xl@-3` is rendered every time (+1,920 renders, 27 min) and Q is in `P_TABLE`, now 27 triples with a new P-aim cell. The plan says the pilot checks that stem training takes and does no harm, and does not forecast O (section 5). |
| B3 | State O's power | Said in the goal check, the read's table, S6-level and the adopt rule: ±0.026 whatever the dose; about 70% power at the whole ceiling, about 30% at half, less with O2; G almost none; "likely undecided even if it works". |
| B4 | E on stems is a second change; the read is matched to training | Named as the second change (section 1). Each inner run's backed-rule E is reported beside the E used. Section 11 says E is chosen at the read's exposure and the donor levels copy the read set's builds. |
| | R-stem's run-minutes | Labelled as R-all's by analogy, not measured, and measured with two seeds side by side (section 5). |
| | Disk fell 2 GB from an unknown writer | Every launcher re-checks the guard (section 9). |
| | The N5 sentence | Corrected: the separator row has no other guitars; what differs from N5 is the exposure, the model and crunch. |
| | Stage N's beside rows | `rc-rep-xl@-3` is rendered at stage N, giving the noise on O's row and a second draw of the goal row. `ens4-xl@-3` is added as an optional row (section 4). |
| | What the repeat measures | Fine-tune seed noise only; about 10% false "loud" with no noise; "quiet" does not bound it (section 4). |
| | The share of 1/2 | Marked as an unmeasured constant; stems only named as the goal-direct choice; a null does not separate them (sections 1, 11, 12). |
| | Stage 0's scope | Split: the controls and the seed-to-seed gauge run now; the donor draws and the build's checks move to the pilot, so no pilot code is written before the user's answer. R-rep's all-labels pair moves to the full run (section 5.1). |
| | The side picker | The plan now says its different answers are not an instability to train away (sections 1, 6). |
| | Outlook: features | "Not the features" is now "not shown"; the older inputs and the ±0.02 to ±0.05 resolution are said. |
| | Outlook: F77 | Now says R-all added whole sets R-ctl never had, so the gain mixes chain count with coverage. |
| | Outlook: more chains | The supply limit and the user's ear time are added. |
| | Outlook: recording-level labels | The +0.042 is now attributed to arm R on per-window labels. The cost counts cap1 only (about 52,500 renders); GOAT is out, and "adds no chains" is said. |
| | Outlook: calibration | Marked not new, with the zero-render prediction of close to nothing (best scale about 0.9). |
| | Outlook: gaps | The amp pick, the read set's power and the unlearned effects are added. |
| | The reviewer's pick | Added as section 14, a candidate diagnostic needing the user's go, with how it differs, `D_TABLE` and its stop rule. |
