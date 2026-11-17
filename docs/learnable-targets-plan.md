# After the ladder: Step 3 (the centre) and Step 5 (targets the model can learn)

**Status:** declared 2026-11-17, before any Step 5 run and before the R1 versions check ran. The planner's draft went
through two rounds of independent review the same day: approve with changes (six blocking points, eight others, all
taken; section 9), then approve. The work follows the **lean path** from the second round. Step 3's ear read and its
R1 versions check go ahead. Of Step 5, only stage 0 is built and run (zero renders, CPU). The confirm, the fine-tune,
the noise repeat and the ladder read are declared here (sections 4.8 to 4.10) but built only after stage 0 reads
S0-rise, or on the user's word. This is Step 3 and Step 5 of the plan the user approved after the 2026-11-16 review,
reached by the ladder's stop rule, branch 3 (`docs/preset-ladder-plan.md` section 15, "After stage 2").
- **Ledger:** `pipeline-fix` holds `phase_s5` (Step 5's rule and tables), `phase_s5_targets` (stage 0) and
  `phase_r1_versions` (Step 3's versions check). Step 3's ear read is the exam page's second amendment
  (`docs/real-song-exam-plan.md`, the listening page's second dated note; `phase_exam_ear`).
- **Code:** `learn/learnable_targets.py`, tests in `tests/test_learnable_targets.py`.
- **Data:** `PF/step5/` (`PF` is `~/ndsp-presets/learn/trusted-data/pipeline-fix`).

Every number is by the score unless it says "by ear". The score is J0: ln(d_row / d_against) on the held half, below
zero closer. Intervals are 90% cluster t intervals. The deciding pool is BKS, GOAT and the panel, weighted equally.
The heard-size floor is −0.05.

## 1. What the plan stands on

| Read | Row | Result | Reading |
|---|---|---|---|
| Ladder stage 1 | Cen − S (480 parts) | −0.121 [−0.177, −0.065] | the label centre beats the factory start on the ladder's units |
| Ladder stage 2 | `xl@-3 − cen` | +0.061 [+0.005, +0.117] | the raw model path loses to Cen on the product's stem (fragile) |
| Re-centred pass | `rc-xl@-3 − cen` | +0.0084 [−0.0417, +0.0585] | undecided; a gain beyond 0.042 is ruled out |
| Re-centred pass | `rc-xl@-3 − xl@-3` | −0.0524 [−0.0782, −0.0267] | re-centring helps the model's own answer on the stem |
| Re-centred pass | `rc-mix@-3 − cen` | −0.0267 [−0.0605, +0.0072] | undecided and underpowered (lower end beyond −0.05) |
| Ladder stage 2 | label − Cen | −0.404 [−0.458, −0.350] | the headroom; the model closes 7 to 12% of it on the ideal input |
| Exam (V-real, 7 bands) | M − R | −0.019 [−0.126, +0.088] | undecided; resolves about 0.15 |
| Exam | C − S (three amps) | +0.030 [−0.065, +0.125] | Cen not shown better than S on real songs |
| Exam | C-pick − S | −0.001 [−0.090, +0.089] | the same, through the product's amp pick |
| Exam | L − S | −0.192 [−0.238, −0.145] | these songs hold real headroom |

- **The reader is the limit, not the input.** With a perfect input the model path reaches about Cen. So the next lever
  is the model (Step 5), then its input (Step 6).
- **Cen's gain over S is shown on the ladder's units only.** The exam neither confirms nor contradicts it.

**The goal check:** Step 3 serves the goal by deciding the product's starting presets. It converges: one sitting, one
table row, framed as underpowered. Step 5 serves the goal only through G, the product's input against the best fixed
preset. It converges: every stage has a stop, and no cell loops back. Its dose is small, so stage 0's S0-flat stop is
the likely end of the step as approved.

## 2. Step 3: act on "reader or constant"

The review's rule: if the model is level with the centre, ship the centres as new starting presets **once Step 1
confirms them**, and check the model's answers on the stored versions of each R1 song.

| Code | Action | Why |
|---|---|---|
| S3-default | **Cen does not become generate's starting presets now.** | Step 1 reads C − S +0.030 and C-pick − S −0.001, both undecided. |
| S3-flag | **No new product flag for Cen now.** | No real-song gain is shown, and no decision waits on it. It stays the product session's call. |
| S3-ear | **One confirming read: C-pick over R by ear, on the exam page the user has yet to sit.** | The page already holds C-pick beside R. It costs no render, no extra sitting and no code change. |
| S3-versions | **The R1 versions check runs, declared, as a description** (2.2). | Approved in Step 3; seconds of CPU; decides nothing alone. |
| S3-flagged | **The flagged model path is re-centred, as its own reviewed change, after Step 5 ends.** | The stop rule's "flagged" cell. It is declared and built on whichever model stands then, so the table is built once. |

### 2.1 The ear read

- **What it compares:** C-pick against R.
  - C-pick is the three Cen presets of the part's class, through the product's stock-DI amp pick.
  - R is generate's research preset, the dry factory start on 8 of 10 units.
- **How it is read:** as the exact mirror of the stored ("R", "C") pair in `EAR_PAIRS`, with no exam code change.
  - The share is one minus the stored "R over C" share, and the interval is [1 − hi, 1 − lo].
  - The bootstrap uses the same bands and seed, so the mirror is exact. A test checks it.
- **Declared in the exam plan:** this is the page's second amendment, made after the J0 score rows were known and before
  any ear score. M over R stays the primary, and L over R stays the positive control, read first.

| L over R (control) | C-pick over R | Code | Next |
|---|---|---|---|
| heard above | heard above | S3-ship | Proposed to the user: the Cen presets replace the dry factory starts (the product session's change, reviewed). |
| heard above | not known | S3-hold | Not confirmed and not failed. No ship. Cen stays the ladder's constant and rides as an arm in the next real-song read. |
| heard above | heard below | S3-no | Cen is not shipped. The ladder's gain did not carry to these songs by ear. |
| not heard above | any | S3-nopower | The page had no power. Nothing is concluded and nothing ships. |

**Power, said first:** one listener, 10 units, 7 bands. By L0's simulation an arm truly ahead on 75% of items clears
about half the time. By the score, C-pick and R are close, so "not known by ear" is the likely reading.

**Stop rule:** one sitting, one read. A score confirmation of a gain near 0.05 would need about 25 bands, so it is not
planned here; it goes to the user.

### 2.2 The R1 versions check (`phase_r1_versions`, `learnable_targets versions`)

- **What:** the adopted pair's answers (R-all's all-labels pair, held as C3-cabS) on each of the three amps, from each
  stored version of each R1 song's window.
  - The versions are in `PF/r1/versions/`: 7 songs × the 6 versions stored (stem, stem_C, xlst_mdxc, cw, steerx_L,
    steerx_R).
  - The planner's draft said 7 × 7. Six versions are on disk, and six are read.
- **Reading each version as the product reads a stem:**
  - Take the version's 10-s window at the stored offset, and undo its stored loudness gain.
  - Find the gain that brings the window's mix (`r1/<song>/model/window.npz`) to the product's −12.25 LUFS, and apply
    the same gain to the version.
  - Read half A through `product_path`'s `answers` code.
  - Use the class `model/answers.json` records.
- **Control:** the same code on the product's own stored window reproduces `model/answers.json` on every amp. The result
  is recorded per song; a mismatch is reported, not hidden.
- **The measure:** the RMS distance over the written knob heads (the ladder's knob groups) that sound.
  - Between a song's versions: every pair, same amp.
  - Between songs of one class: same version and amp.
  - Medians per amp, pooled, and per knob group.
- **Sealed data:** it reads R1 audio (stored stems and the stored window), so it runs only as this declared step. No
  separation, no render, no song file is opened.
- **Already measured twice with truth:**
  - On the exam, M moves less between a unit's input variants (median 0.008 to 0.013) than between units of a class
    (0.021).
  - On the ladder, a part's answer moves about as much between inputs (0.041 to 0.044) as answers differ between parts.

| Reading (pooled, all knob groups) | Next |
|---|---|
| answers move more between versions than between songs | "The model reads the separator's version." It weighs for Step 6 and is quoted in the user's separator call. No product change. |
| answers move less between versions | Consistent with the exam. Nothing changes. |

## 3. Step 5: what it is and how it differs

- **The defect it aims at (the review's G5).** A label is the judge's optimum for one recording.
  - 91% of the 665 labels have at least one EQ band on its ±12 dB limit.
  - Near-ties are settled by the search's path, so labels of similar recordings land far apart.
  - A model trained on them learns their mean: its answers' spread is 15 to 25% of the labels'.
- **The change.** Per record, among the stored settings the judge scores about as well as the best, train on the one
  nearest the centre. As far as the judge knows the sound is the same, and the target is the most typical one.
- **How it differs from what was tried.**
  - C3, C3i, C3s and C3r changed which controls, rows or loss the model trains on. None changed which of a record's
    near-equal settings is the label.
  - The re-centred answer moves the model's mean after training. This changes what the model is trained to say.
  - The centres as presets (RcBG, Cen) drop the per-record part. This keeps it wherever the judge insists.
- **Why it may still fail.**
  - **The dose is small** (the planner's preview, section 4.2). At the declared margin the stored trials move a label
    only 18% of its distance to the centre.
  - R-all's answers follow the preview's targets no better than the labels.
  - The judge is not the ear at these sizes, so "about as well" is by the score only.
  - The model may be limited by its input, not its targets.

## 4. Step 5 in detail

### 4.1 What is on disk

| What | Where |
|---|---|
| The stored search outputs | `PF/goat/search-c2/`, `PF/real/search-c2/` (BKS), `PF/captures/search-c2r/`, `PF/captures2/search-c2r/`, `PF/panel/search-c2r/` |
| The labelled records | 665: BKS 306, GOAT 214, cap1 121, n12 12, the panel 12; every one is C3r's training source of kind `c2` |
| Step 1's trials | 200 a record, each with its 39 searched values and the judge on both halves; with `step1.start_settings` each is a full setting |
| Stages A and B | each stage's best setting and judge; `step2.trace` holds each evaluation's judge and peak but not its setting |
| The folds, the drops, the training mix | `full_controls_c3r.state()`, `split`, `records_of`, `mixed`, `cycled_to` |
| R-all's out-of-fold answers (480 read parts, both halves) | `PF/c3r/answers/all.json` |
| Cen as the ladder built it | `PF/ladder/answers/cen.json` (per fold), `PF/ladder/centres.json` (all labels) |

### 4.2 The planner's preview (zero renders; stage 0 recomputes it under the declared rule)

The preview ran on all 665 records, with one unweighted centre per amp and class and a mean distance.

| Margin | Picks other than the best-scoring candidate | Median distance to the centre | EQ bands on a limit, a record | Held-half cost against the label |
|---|---|---|---|---|
| the label | | 0.304 | 1.55 | |
| 0.01 | 78% | 0.283 (−7%) | 1.28 | +0.003 |
| 0.03 | 92% | 0.260 (−15%) | 1.07 | +0.012 |
| **0.05** | **96%** | **0.248 (−18%)** | **0.94** | **+0.023 (cluster mean +0.021 ± 0.006)** |
| 0.10 | 98% | 0.236 (−22%) | 0.71 | +0.044 |

- **Its learnability readout** reads +0.006 [−0.002, +0.014] over all knob heads, which is S0-flat. The reviewer
  reproduced it at +0.006 [−0.001, +0.014].
- **Known weakness of the readout:** the correlation does not change if every target moves the same fraction of the way
  to the centre. At this dose the expected rise is inside its spread. So S0-flat says only "the dose is not shown". It is
  not a verdict on targets nearer the centre.
- **These figures were seen first.** The held-half cost is read from stored values, and the margins were seen before
  0.05 was named.

### 4.3 The target rule (`phase_s5`)

| Part | Rule |
|---|---|
| **Candidates** | Every stored full setting of the record, in this order: the label (with its fresh render's judge), stage B's best, stage A's best, then step 1's 200 trials (each on `start_settings`). Identical settings count once and the first is kept: stage B's best is the label on every record, so it folds into the label. Only candidates with a finite, positive judge on both halves are used. |
| **Not candidates** | Stage A's and B's other trials. The trace stores no setting, and the zero-render replay that could recover them is **not built** on the lean path. Each per-trial peak is also not stored, so C2's near-silent bound is checked at the confirm (4.8), where a miss falls back to the label. |
| **Margin** | Within **0.05** of the record's best candidate, in ln judge on the **search half**. 0.05 is the heard-size floor (F65), which was set for pooled means; using it for one record borrows its meaning. Other margins are printed only as a description. |
| **Centre** | Cen as the ladder builds it: `centre_of` over the run's training labels under C3's training mask, each record weighted by its showings in an epoch, then written by `answer_settings` and C3r's hold. **Each run uses the Cen of its own training records, which makes nine target sets (`RUNS`).** fold model k uses folds other than k, less the drops. **Inner run k uses folds other than k and k + 1, less its drops.** The all-labels pair uses every record. Cen is not recomputed from the targets. |
| **Validation** | Inner run k validates on fold k + 1's records. Each takes the target the same rule picks under inner run k's own Cen, which holds none of fold k + 1's labels. The held loss against the raw labels is logged beside. |
| **Distance** | The sum of squares in the `full_space` unit space. It runs over the heads the adopted answer writes (C3-cabS's written keys, the forced EQ and gate switches out) that sound in both the candidate and Cen. A knob counts its squared difference; a switch or a mic type counts 0 when equal and 1 when not. |
| **Pick** | The qualifying candidate nearest Cen. A tie goes to the better search-half score, then to the lower index, so the label comes first. |

### 4.4 Heads and rows (`HEAD_RULE`, coded and tested)

**No head loses a training row.**
1. A written head, the mic types included, takes the candidate's own value and keeps the label's training mask. It
   trains wherever, and only where, the label trains it.
2. A trained head the answer does not write (the left cab, the room mics, the right cab's phase) keeps the label's row:
   its value and its mask, whatever the candidate.
3. Stage 0 counts every head's training rows (showings) under the labels and under the targets, run by run. It
   **refuses** if any count differs.

- **How part (1) is read.** The mask is the label's, so a trained written head stays trained when the candidate has it
  switched off; it then takes the candidate's stored, silent value. A head the candidate sounds but the label doesn't
  train stays untrained. Stage 0 counts both cases and reports them.
- **Why.** For written heads the target stays one rendered, judged setting. The EQ and the mic were tuned together, so
  the label's mic is not grafted onto a trial's EQ.
- **The price.** On some records the target goes back from stage B's mic to the start's. The preview counted 192;
  stage 0 reports the count for each discrete head.

### 4.5 Coverage: every control

No control changes its status in the coverage table (C0). Step 5 changes which value a searched control is trained on,
and by `HEAD_RULE` every head trains on as many records as today.

| Family | Step 5 |
|---|---|
| Input gain, amp knobs and switches, cab position and distance, right cab on and level, amp EQ, pedals, gate threshold | re-targeted, trained, written |
| Mic types | trained on every record and written. The target's mic is its candidate's; on some records that is the start's mic instead of stage B's. They are not re-searched. |
| Left cab, room mics, right cab's phase | not re-targeted: each keeps its label's row, held at S in the answer (C3-cabS), as today |
| Amp choice | unchanged: the stock-DI pick. On the exam it read at chance by the score, undecided (M − M3 −0.005). A research target of its own. |
| **Time effects, the spring, the doubler and stereo** | **not re-targeted and not trained here.** No stored trial holds one. They stay open in C0, and the effects route is the user's call (section 6). |
| Output gain | unchanged: the loudness step |

### 4.6 Stage 0 (`phase_s5_targets`, `learnable_targets stage0`; zero renders)

1. **Controls:**
   - every labelled record's training source is the search output's label;
   - each record has 200 trials, and its halves are known;
   - step 1's stored best is its trial;
   - each record's class matches its unit's;
   - the label's fresh judge is finite;
   - each fold model's Cen reproduces the ladder's stored `cen` answers on its parts;
   - the all-labels Cen reproduces `centres.json`;
   - R-all's answers file was answered on today's C3r state.
2. **The nine target sets**, written to `PF/step5/targets-{run}.json` with their sha256. They cover each run's training
   records and an inner run's validation records.
3. **`HEAD_RULE`'s row counts**, every head, every run, labels against targets. Also each discrete head's count of moved
   targets, and part (1)'s two counts.
4. **Per run:**
   - how many targets differ from the label, and of which kind;
   - the median distance to Cen, label against target;
   - the EQ bands on a limit;
   - the distinct non-label training targets the confirm would render (each primed, so twice).
5. **The stored held-half cost** of each run's training targets against the labels (ln judge, the stored values), by set
   and on the deciding pool.
6. **The dose table:** the all-labels set at margins 0.01, 0.02, 0.03, 0.05 and 0.10, with each margin's held-half cost.
   The within-cell spread of the knob targets against the labels.
7. **The learnability readout:**
   - **The data:** R-all's out-of-fold answers on the read records. Each is compared with its label and with its target
     under its own fold's Cen. That Cen holds none of the record's fold.
   - **Which values:** every written knob head (the ladder's knob groups) that sounds in the answer, the label and the
     target, and that the label trains. Both halves of each answer are used.
   - **How it is computed:** each of answer, label and target is centred within its (amp, class, head) cell, using
     cells of at least 5 values. r(answer, label) and r(answer, target) are each the sum of products over the root of
     the sums of squares, as in the preview.
   - **The interval:** the difference's 90% interval comes from a cluster bootstrap. Clusters (set, cluster) are
     resampled with replacement, 2,000 times, seed 20261171, percentile.
   - **Reported:** per knob group and over all of them.

**Stage 0's table** (`S0_TABLE`, coded; the first that holds):

| Code | When | Next |
|---|---|---|
| S0-fail | A control fails, or any head's training rows differ between the labels and the targets. | Stop. Reported. |
| S0-overfit | The all-labels targets' stored held-half cost has its whole 90% interval beyond +0.05 on the deciding pool. | Stop: the search half's near-ties are not near-ties on the held half. A smaller margin is an amendment, reviewed first. |
| S0-flat | Over all written knob heads, r(answer, target) − r(answer, label) has a 90% interval that holds zero or lies below it. | **Stop before any render or training.** To the user, with the dose table and the readout: the line to the centre (4.11), or their word to run the step as approved. Not failed: the stored trials' dose is not shown to reach what the model reads. |
| S0-rise | That interval lies wholly above zero. | On to the confirm: its own build, and review of that build. The size is reported beside the answers' r today. No bar on it. |

**The line to the centre** is pending the user's word. If the user says yes before stage 0 runs, its candidates join the
target build first (4.11), as an amendment reviewed before stage 0. Otherwise stage 0 runs as declared here.

### 4.7 Stages, costs and stops

Measured rates:
- **Fresh primed renders:** 70 a minute on 3 shards. Stage 1 did 8,640 in 2 h 3 min; stage 2 did 12,480 in 3 h 4 min.
- **Training:** R-all's 18 training runs logged 128.0 run-minutes in their records, of which the 16 fold and inner runs
  took 114.4.
- **Encoding:** the planner's preview encoded all 133,000 trials in 24 s.

| Stage | What | Renders | Machine time | Stop |
|---|---|---|---|---|
| 0 | as 4.6 | 0 | minutes of CPU | `S0_TABLE` |
| 1, the confirm | Each distinct setting chosen as a training target, rendered fresh and primed, judged on both halves | at most 7,980 (6 a record × 665 × 2); stage 0 counts them | at most 1 h 54 min | the confirm's table (4.8) |
| 2, the fine-tune | R-near: 8 inner runs, 8 fold runs, the all-labels pair; then the noise repeat, 16 runs | 0 | 128.0 and 114.4 run-minutes as logged for R-all | one training each; no rerun on a read |
| 3a, the action rows | `rc-n-mix@-3`, `rc-n-xl@-3` | 3,840 | about 55 min on 3 shards | one pass, one report, the cell named and its hash in the ledger; then the audit |
| 3b, the beside rows | the raw and same-input rows | 5,760 | about 82 min on 3 shards | only as 4.9 says; they cannot change the cell |
| 3c, the noise row | the repeat pair's `rc-xl@-3` | 1,920 | about 27 min | only when O reads better or worse |

**The confirm's size departs from the approved plan.** The review's Step 5 gave about 650 renders, one a record. This is
up to 7,980, for two reasons:
- every fresh render here is primed, so a setting costs two;
- nine target sets keep each run's centre free of the labels it is read or validated on, so a record can have up to six
  training targets.

### 4.8 The confirm (declared; built only after S0-rise)

The held-half cost is already known from the stored values at stage 0. So the confirm checks only that a fresh render
reproduces them: render fidelity and the level bound.

| Code | When | Next |
|---|---|---|
| K-ok | Each fresh search-half value is within 0.005 of its stored one (C2's start-check tolerance) and passes C2's near-silent bound | Train. The fresh held-half cost is reported beside the stored one. |
| K-fallback | Single targets miss the tolerance or the bound | Each falls back to its label, counted and named by library unit id. Train. |
| K-machinery | 5 of a shard's first 10 targets miss (C2's systematic-miss guard) | Stop before training: the stored values can't be trusted. Reported. |

### 4.9 The fine-tune and the read (declared; built only after the confirm)

**The fine-tune:** C3r's R-all recipe, with one change: each record's target and each head's row come from 4.3 and 4.4.
- **Unchanged:** W's NS-best state per seed; seeds 20261042 and 20261043; `train-ft --masked --ft-cap 300`; C3r's four
  folds, drops and two-source epoch mix; each fold run takes its own inner run's E, and the pair the median of the eight;
  per-head held losses logged; the answer's hold C3-cabS.
- **Each inner run** trains and validates on targets under its own Cen, and logs the raw-label loss beside.
- **Naming:** each run takes its own name (a new base, never R-all's). It records its target set's sha256 and refuses
  until the confirm is written.
- **Training noise, measured, not assumed:**
  - *Seed to seed (zero renders):* always reported beside the read. It gives the distance between the two seeds'
    answers, per knob group, against the shift from R-all to R-near.
  - *The noise repeat:* R-all's recipe on the raw labels with two new seeds, named in the training phase when it is
    declared: 16 fold and inner runs.

**The read, on Step 2's ladder:** the same 480 parts, each answered by its own fold's R-near pair from the stored
features. It uses zero separations and the ladder's statistics (`rows_for_pair`, `summarise`). The read's action rows
are:
- **G:** `rc-n-xl@-3 − cen`;
- **O:** `rc-n-xl@-3 − rc-xl@-3`;
- **R:** `rc-n-mix@-3 − rc-mix@-3`, which acts only inside S5-level;
- **the noise rows:** N (`rcN-xl@-3 − rc-xl@-3`) and O2 (`rc-n-xl@-3 − rcN-xl@-3`), where rcN is the repeat pair's
  re-centred answer.

The beside rows (pass 3b) run when G, O or R reads better or worse, and the noise row (3c) when O reads better or
worse. R-all's side needs no render: its rows are stored and hash-checked before the report.

**Ledger:** the confirm, the training, the repeat and the read each get their own phase, declared and reviewed before
they run. The read's phase goes in the `preset-ladder` entry.

### 4.10 The outcome table (`S5_TABLE`, coded now with its tests, before any run)

"Adopt only if it beats R-all and Cen there" (the review). Each of the nine (G, O) pairs appears once. `table_guard`
refuses any command if the table is broken.

| # | G (against Cen) | O (against R-all) | Code | Next |
|---|---|---|---|---|
| 1 | better | better | S5-adopt | If the noise rule holds: R-near replaces R-all as the adopted model (ML's reviewed change). The re-centred R-near path is the default candidate, and that goes to the user with the ladder read. Step 6 trains on R-near's targets. |
| 2 | better | undecided | S5-user | It beats Cen but is not shown better than R-all, so the rule is not met. To the user, with both intervals. |
| 3 | undecided or worse | better | S5-build | If the noise rule holds: a gain over R-all, not shown over Cen. Not the default; Cen stays Step 3's start. R-near replaces R-all behind the flag (a reviewed change) and is Step 6's base. |
| 4 | undecided or worse | undecided | S5-level | No change of model. Not failed. Then by R: **better**, Step 6 trains on R-near's targets; **not better**, Step 6 trains on the raw labels, and the stronger doses (4.11) go to the user with this read. |
| 5 | undecided or worse | worse | S5-worse | The targets hurt on the product's input. Not adopted; the raw labels stay. "Worse" is said only if it holds against the repeat too. |
| 6 | better | worse | S5-impossible | Cannot occur while R-near's rows read R-all's directions (G = O + 0.0084 on the pool means). The report refuses and stops. |

**The noise rule** (rows 1, 3 and 5). O compares two trainings, and R-all's recipe has never been repeated. So O's
reading counts only if O2 reads the same way. Otherwise the cell's action does not fire: the write-up says "not
separable from training noise", gives N, O and O2, and the choice goes to the user. Until O2 is rendered, the action is
held.

**False alarms, qualified.** Under no effect of the targets, G reads better with at most 5% (one tail). G still carries
R-near's training noise. The same 5% for O holds only if training itself adds no difference, which is not known; the
noise rule is there for that.

**Under S5-adopt, Step 1's set is descriptive.** It is one declared read against the exam's stored renders, with the ear.
It has no cells.

**Stop rule:** one target build, one confirm, one fine-tune and its one repeat, one read in its declared passes. No
margin or rule is tuned on the ladder's units. Any change is a dated amendment before the next stage, reviewed first.
Step 5 ends at a stage 0 stop, a confirm stop, or one of the cells.

### 4.11 Not declared: stronger doses (each needs the user's go)

| Option | What | Why it may fail | Measured cost |
|---|---|---|---|
| The line to the centre | Per record, render the label moved a quarter, a half and three quarters of the way to Cen, and add those to the candidates | The judge may rise fast off a limit-pinned optimum: at the centre itself the cost is 0.40 | 1,995 settings, 3,990 fresh renders, about 57 min for one set; up to six times that with a line per target set |
| A search pulled to the centre | C2's search again, with the distance to Cen as a small penalty | It repeats the label run's cost for a dose not yet known to matter | 177,800 renders, 27 to 29 h at 6,200 to 6,600 an hour |

A third idea, picking the near-best setting nearest the model's own answer, is not proposed: it would teach the model
its own errors.

## 5. Order of work

| # | Work | Machine |
|---|---|---|
| 1 | The exam's second amendment (PR #510); the user's sitting; the exam session's `score` | none |
| 2 | This declaration, reviewed and merged | none |
| 3 | The R1 versions check | seconds of CPU |
| 4 | Step 5 stage 0; hand-back to the orchestrator, unaudited, then the audit | minutes of CPU |
| 5 | Only after S0-rise or the user's word: the confirm, the fine-tune and the repeat, the read, each built, declared and reviewed first | as 4.7 |

## 6. The user's pending calls (not decided here)

- **The line to the centre** (4.11): under an hour of renders to raise Step 5's dose.
- **The effects' default route:** move the effect readers' trigger from "after step 4" to "after Step 5's read".
  - The product keeps research's effects as the floor, and the delay reader stays off.
  - The learning route is C0's own order: each effect switch's loss on NS at zero renders; then a reader on exposed
    windows where the truth is known; then wet real rows.
- **Separator work.** The planner's lean is to hold it until Step 5 ends.
  - A perfect input reaches only about Cen, so a separator is not shown to make the model path beat the fixed preset on
    today's reader.
  - That is not "shown unable": `rc-mix@-3 − cen` is underpowered, and a post hoc cut without the heavier lenders reads
    −0.039.
- **Stage 3 and Step 4's rows.** The planner's lean is to skip them now and declare them again on the model that stands
  after Step 5.
  - The case for running them: `clean@-3 − xl@-3` is −0.060 [−0.108, −0.012], a heard-size gain, though confounded and
    fragile.
  - The case against: `clean@-3 − cen` is +0.001.
- **A score confirmation of Cen on real songs** needs about 25 bands.

## 7. Standing rules, as applied

- **Before and after each run:** every ledger phase is declared before its run. Each step has an independent review
  before it runs and an independent audit before its write-up.
- **Reporting:** no pass bars. Sizes and intervals are reported. Undecided is not failed, and an interval whose lower end
  is beyond −0.05 is called underpowered.
- **Sealed sets:**
  - V-real is read only by the exam's declared `score`, and under S5-adopt by one declared descriptive read.
  - R1's audio is read only by the versions check (stored stems and window, no song file).
  - NS and the reserve are not touched.
- **Trusted data only:** the 665 labelled records are the reviewed set.
- **The public repo** gets titles and library unit ids only: no audio, path, preset or settings value. Targets and
  settings live under `PF/step5/`.
- **Machine:** at most 3 render processes, one MPS job, the 31 GB disk guard, no rented machine.

## 8. Risks, and what stage 0 can't say

- S0-flat is close to certain at this dose, and it says "the dose is not shown". It does not mean targets nearer the
  centre cannot help.
- The readout uses R-all's answers, a model trained on the labels. It asks whether those answers already lean towards
  the targets. It does not ask what a model trained on the targets would say.
- The stored step 1 trials were judged in a primed renderer and the label in a fresh one. The held-half cost mixes the
  two; the confirm would measure it fresh.
- Each per-trial peak is not stored, so a near-silent trial can be a target at stage 0. The confirm's bound catches it.

## 9. Changes from the planner's draft, and after the reviews

The first review approved with changes; all six blocking points and the eight others were taken in the draft before the
second round approved it.

| # | Review point | Change |
|---|---|---|
| B1 | Inner-run leak: inner run k got fold k's Cen, which holds fold k + 1's labels | Each run uses the Cen of its own training records: nine target sets. Inner runs validate on targets under their own Cen, the raw-label loss beside. |
| B2 | Heads that lose training rows | `HEAD_RULE`, coded with tests; stage 0 counts rows per head and refuses on a difference. |
| B3 | The ear pair is stored as R over C | The read is the mirror of the stored pair, with no exam code change; the exam plan's second amendment (PR #510). |
| B4 | O's 5% claim ignores training noise | Qualified; a seed-to-seed gauge and a noise repeat are declared; O counts only if O2 reads the same. |
| B5 | Fairness of the user's calls | "Not shown to", with the underpowered row and the −0.039 cut named; Step 4's case cites −0.060. |
| B6 | Two unsourced runtimes | About 600 separations, about 46 min; the pulled search 27 to 29 h. |
| N1–N8 | Passes, stage 0's action, the confirm's known cost, the coded table, the descriptive V-real read, the confirm's size, the amp pick, the effects route | As 4.6 to 4.10 and section 6. |

**Choices made while building stage 0** (for this declaration's review to check):
- **Candidate order:** label, stage B, stage A, then step 1. Duplicates fold into the first copy, so an exact tie keeps
  the label.
- **Stage A's and B's other trials stay out.** The replay is not built on the lean path.
- **`HEAD_RULE` (1) is read as "the label's mask on every head".** A trained written head that is silent in the
  candidate keeps its row, with the candidate's stored value. Both cases are counted.
- **The readout's cells are the preview's (amp, class, head).** The ladder's knob read uses (set, fold, amp, class,
  head). Each record's target is under its own fold's Cen.
- **The overfit stop reads the all-labels set.** The other eight sets' costs are reported beside.
- **Six stored R1 versions,** not seven.
- **A pre-merge check** ran only the source and Cen controls on the real data: 665 records, all of kind `c2`, no
  problem. Each fold model's Cen reproduced the ladder's on 480 of 480 parts, and the all-labels Cen reproduced
  `centres.json` on 6 of 6 cells. No target, count or readout was computed before this declaration.
