# After the ladder: Step 5's stage 0 and Step 3's R1 versions check (results)

**Status:** run 2026-11-17 from main at `dde0a610`, the squash of PR #511, which holds the declared phases; it ran
after that commit. Audited the same day by an independent recompute: PASS WITH CORRECTIONS. Every number reproduced,
and the corrections are to wording and reading; they are taken here.
- **Plan:** [learnable-targets-plan.md](learnable-targets-plan.md).
- **Ledger:** `pipeline-fix` `phase_s5_targets_outcome` and `phase_r1_versions_outcome`.
- **Data:** `PF/step5/` (`PF` is `~/ndsp-presets/learn/trusted-data/pipeline-fix`). `stage0.json` has sha256
  `65e2be9d…64d5`, `r1-versions.json` has `586eb39f…ede5`, and there are nine target files.
- **Cost:** zero renders, zero separations, zero training. `versions` took 7.3 s and `stage0` 53.4 s.

Every number is by the score unless it says otherwise. Items marked **post hoc** come from the audit and were not
declared before the run.

## The read

- **Stage 0 reads S0-flat.** Step 5 stops before any render or training, as declared.
- **What the readout found:** R-all's out-of-fold answers do not already lean towards the new targets. Over all written
  knob heads, r(answer, target) − r(answer, label) is −0.0013 [−0.0105, +0.0075].
- **Undecided, not failed, and underpowered for the expected dose.**
  - **Power** (post hoc): the readout's standard error is 0.0057, so its power is about 22% at the expected +0.005 and
    54% at +0.010.
  - **It does rule out a target move that only removes noise** (post hoc). Such a move would have raised r by about
    +0.022, and the readout had 98% power to see that.
- **What it does not show:**
  - what a model trained on these targets would do;
  - anything about larger doses.
- **Next, pending the user:** the line to the centre (the plan's 4.11), or the user's word to run the step as
  approved. Neither is started.

## Stage 0

### The controls (all pass)

- **Sources:** all 665 labelled records are C3r's training sources of kind `c2`. Each search output's label is the
  source, with 200 trials and the halves known. Step 1's stored best is its trial, the classes match, and the label's
  fresh judge is finite.
- **Cen:** each fold model's Cen reproduces the ladder's stored Cen on 480 of 480 parts. The all-labels Cen reproduces
  `centres.json` on 6 of 6 cells.
- **The answers:** R-all's answers file was answered on today's C3r state.
- **`HEAD_RULE`:** every head's training rows are equal under labels and targets in all nine runs. As built this cannot
  fail, so it guards the code only.
- **The label's reference judge:** using stage B's stored judge instead of the label's fresh one changes at most one
  pick per run (1 of 665 on the all-labels set).

### The learnability readout

The data are R-all's out-of-fold answers on 479 read records, both halves. Each answer is compared with its label and
with its target under its own fold's Cen. The heads are the written knob heads that sound in all three and that the
label trains. Values are centred within (fold, amp, class, head) cells. The 90% interval comes from a cluster bootstrap
over (set, cluster): 2,000 resamples, seed 20261171.

| Knob group | Values | Clusters | r(answer, label) | r(answer, target) | Difference [90%] |
|---|---|---|---|---|---|
| drive | 2,564 | 234 | +0.101 | +0.096 | −0.006 [−0.026, +0.011] |
| tone | 1,928 | 234 | +0.205 | +0.198 | −0.007 [−0.026, +0.010] |
| cab | 3,560 | 234 | +0.224 | +0.229 | +0.006 [−0.015, +0.027] |
| EQ | 10,538 | 234 | +0.130 | +0.124 | −0.006 [−0.021, +0.009] |
| pedals | 880 | 92 | −0.015 | −0.013 | +0.002 [−0.022, +0.028] |
| **all** | **19,470** | **234** | **+0.157** | **+0.156** | **−0.0013 [−0.0105, +0.0075]** |

- **Cells without the fold** (post hoc): with (amp, class, head) cells, the read is +0.0024 [−0.0076, +0.0120]. That is
  still flat, so adding the fold does not hide a rise. It explains about +0.004 of the gap to the planner's preview
  (+0.006).
- **The move behaves like a shrink** (post hoc):
  - The answers' covariance with the target is 13% below their covariance with the label: a ratio of 0.870
    [0.814, 0.926], against the targets' SD ratio of 0.878.
  - On the label, the target has a slope of 0.77 and a correlation of 0.88.
- **Raw distances** (post hoc):
  - The answers sit 10.7% nearer the targets than the labels.
  - Cen itself sits 11.6% nearer, so the gap is the targets' own move towards Cen, not learning.
  - Along the move, the answers' excess over Cen is −0.0011 [−0.0015, −0.0007], slightly towards the label.

### The overfit check and the held-half cost

The all-labels targets' stored held-half cost against the labels, on the deciding pool, is +0.0144 [−0.0009, +0.0297].
It is not overfit: the lower end is not beyond +0.05. The pool's interval holds zero. In BKS, GOAT and cap1 (cap1 is
outside the pool) the cost is clear of zero:

| Set | Cost |
|---|---|
| BKS | +0.019 [+0.011, +0.026] |
| GOAT | +0.021 [+0.014, +0.028] |
| cap1 | +0.022 [+0.011, +0.033] |
| The panel (5 clusters) | +0.003 [−0.041, +0.047] |

So by the score the targets are judged about 0.02 worse on the held half in BKS, GOAT and cap1 (post hoc), about a
third of the heard-size floor. The panel's five clusters are what widen the pool. The other eight runs read alike, from +0.005 to +0.023 on the pool.

### The dose (the all-labels set, 665 records)

The distance is the root of the summed squares over the written heads that sound, where a switch or mic mismatch counts
1. It is not an RMS.

| Margin | Targets other than the label | Median distance to Cen, label → target | EQ bands on a limit, label → target | Held-half cost, deciding pool |
|---|---|---|---|---|
| 0.01 | 373 | 1.891 → 1.813 | 1.54 → 1.25 | −0.0007 [−0.0078, +0.0064] |
| 0.02 | 468 | 1.891 → 1.731 | 1.54 → 1.15 | +0.0059 [−0.0030, +0.0148] |
| 0.03 | 533 | 1.891 → 1.687 | 1.54 → 1.04 | +0.0074 [−0.0016, +0.0163] |
| **0.05** | **586** | **1.891 → 1.625 (−14.1%)** | **1.54 → 0.92** | **+0.0144 [−0.0009, +0.0297]** |
| 0.10 | 624 | 1.891 → 1.566 | 1.54 → 0.66 | +0.0337 [+0.0097, +0.0577] |

- **The best-scoring candidate is not always the label.** On 55 of 665 records a step 1 trial beats the label on the
  search half, by a median of 4e-6 and at most 0.018. On those records the pick is neither, so "not the best-scoring"
  and "not the label" give the same counts.
- **At 0.05,** the targets are step 1 trials on 565 records and stage A's best on 21. 79 stay the label.
- **The knobs' within-cell spread** falls 13%, from 0.245 to 0.213, by group:

  | Group | Change |
  |---|---|
  | drive | −4% |
  | tone | −8% |
  | cab | −11% |
  | EQ | −17% |
  | pedals | −18% |

  The answers' spread is 0.044, so the targets stay about five times wider than the answers.
- **Discrete heads moved** (all-labels set):

  | Head | Targets moved |
  |---|---|
  | right cab on | 126 |
  | compressor on | 120 |
  | left mic type | 111 |
  | right mic type | 73 |
  | compressor release | 40 |
  | others | 63 |

### What the confirm would have rendered (not built)

- **The all-labels set:** 586 non-label targets.
- **The union over the nine runs:** 1,070 distinct targets on 609 records, or 2,140 renders primed, against the
  declared ceiling of 7,980.

### An open question for any later fine-tune

- **Written heads the label trains but the target switches off:** 4,088 continuous, 669 switch and 428 mic row
  showings, summed over the nine runs. Under `HEAD_RULE` they would train on values never heard. Stage 0 keeps them
  out of the readout. They need a ruling before any fine-tune is built (plan 4.4).
- **Written heads sounding in the target but untrained by the label:** 2,944 continuous, 244 switch and 522 mic. These
  stay untrained.

## The line to the centre: what stage 0 can and can't say (post hoc)

- **The readout can't judge it.**
  - The line moves each label a fraction f of the way to Cen. Within a cell, the part of f common to all records is a
    pure shrink, which a correlation cannot see.
  - For a model trained on squared error, a common shrink is roughly the same as pulling its answers towards Cen after
    training. The ladder already read that as level with Cen: `rc-xl@-3 − cen` +0.008 [−0.042, +0.058].
  - So any gain has to come from records moving by different amounts.
- **The stored trials as a proxy** (all-labels Cen; the trials are not on the line):
  - Within the 0.05 margin, a record's best trial closes a median of 12% of its distance to Cen (90th percentile 27%).
  - Reaching 25% closer costs a median of +0.10 on the search half and +0.08 on the held half. Only 82 of 315 records
    have such a trial within 0.05.
  - At 50% closer the cost is +0.12, and at Cen itself 0.40 (the ladder).
- **The cheapest deciding test:** render the quarter point only: 665 settings and 1,330 renders, about 19 min at stage
  1's measured 70 a minute. Go further only if most records qualify there.
- **It would need its own gate, declared first,** not the scale-free r. For example:
  - r on the part of the targets the label does not explain;
  - or straight to the confirm and fine-tune, read on the ladder.
- **A cheaper alternative:** a training-free test that shrinks the answers towards Cen after training answers the common
  part.

## Step 3: the R1 versions check (descriptive)

- **What was read:** 7 songs, each with the 6 stored versions (stem, stem_C, xlst_mdxc, cw, steerx_L, steerx_R), on 3
  amps: 126 answers by the adopted pair.
- **Control:** on every song, the same code on the product's stored window reproduces its stored answers on all three
  amps, and the gain matches.
- **The measure:** the RMS over the written knob heads that sound.

| Amp | Within-song pairs | Within-song median | Between-song pairs | Between-song median |
|---|---|---|---|---|
| pr12 | 105 | 0.031 | 54 | 0.040 |
| sw50r | 105 | 0.030 | 54 | 0.044 |
| ac20 | 105 | 0.034 | 54 | 0.043 |
| **pooled** | **315** | **0.030** | **162** | **0.042** |

- **The declared reading, by the median:** answers move less between a song's versions than between songs. That would
  mean consistent with the exam, nothing changes.
- **That reading is fragile** (post hoc):
  - The means are equal: 0.0425 within songs against 0.0423 between songs.
  - A song bootstrap of the median ratio gives [0.49, 1.20].
- **The within-song moves split in two** (post hoc):

  | Version pairs | Median move | Against between songs |
  |---|---|---|
  | Among the four centre versions (stem, stem_C, xlst_mdxc, cw) | 0.016 | about a third |
  | With a side-picker version (steerx_L or steerx_R) | 0.063 | 1.5 times |
  | steerx_L against steerx_R | 0.022 | |
  | Between songs, the side-picker versions only | 0.024 | |

  - For the side-picker versions, the plan's "more between versions than between songs" does hold: **the model reads
    which separator output it gets.** It may be because a different guitar part sits on the sides.
  - For the centre versions it does not.
  - This weighs for Step 6 and for the user's separator call. There is no product change: the product uses a centre
    version.
- **A caveat:** on 5 of 7 songs the product's own window is not one of the six versions.

## Pending (not started)

| Item | Whose call |
|---|---|
| The line to the centre (quarter point first), or running Step 5 as approved | the user |
| Whether silent written heads train, before any fine-tune | review, with these counts |
| The effects' default route, separator work, stage 3 and Step 4's rows | the user (plan section 6) |
| The flagged path's re-centring | after Step 5 ends (plan section 2) |
