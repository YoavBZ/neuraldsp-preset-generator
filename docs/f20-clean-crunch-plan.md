# F20 on the clean/crunch pool (re-plan, 2026-10-30)

**Status: draft for the user's yes. Nothing has been run, rendered or trained under it. Once approved, each step
is declared in the ledger and independently reviewed before it runs.**

Replaces T3's F20 plan (ledger `trusted-data-t3`, `amendment_1`'s F20 fixes; ROADMAP item (d)). It builds on the
[clean/crunch pool](clean-crunch-pool-plan.md) (ledger `clean-crunch-pool-dcc`).

## Why

On V-real, D_F5 about equals its own constant (−0.004 [−0.052, +0.043], T3's F5 read). D_CC trails its own constant: +0.103
[+0.051, +0.155], 0 of 7 bands better (`amendment_4_outcome`). Most of D_CC's loss against D_F5 is in its pedal
answers: the drive switches sit near chance (pooled p 0.42–0.50 against 48–53% "on" in its labels), and a 0.5
readout turns a bare-majority "on" into "off".

The question F20 answers: **does much more clean/crunch data make the model beat its constant?**

## What we already know

- **In-distribution, the model reads few heads.** R0 (`trusted-data-t3` `amendment_1_r0_outcome`) found 20 of D_F5's
  116 heads readable on FS5. That includes 5 of 85 knobs, about the 4 expected by chance.
- **The information is lost before the model.** The tone-information probe (`amendment_2_outcome`) found a linear
  reader gets 86 of 116 heads from the target render, 30 from the self-built mix and 20 from the stem. The mix
  hides most of the tone, and the stem gets none of it back.
- **Two input fixes did not help.** The mix as input (D_F5mix) is not shown better and leans worse. The X-LANCE
  fine-tune was not adopted.
- **The time effects are mostly not heard.** On the guitar alone, 25 of the 26 pairs near tau were not heard
  (`clean-crunch-pool-dcc` `amendment_6_answers`). All 8 spring pairs came back "same".

More data can only help if the model is data-limited. If the stem has simply lost the information, it cannot.
Step 0 measures which is true on data we already have, before F20's renders.

## Step 0: a learning curve on stored data (zero renders)

**What runs.**
- D_CC's recipe (`cc_build train`: same heads, loss, augmentation and early stopping on FS_CC), trained on nested
  subsets of its 2,699 training examples.
- Sizes: 25% and 50%, drawn within each section so every section keeps at least one example, and nested (the
  25% set sits inside the 50% set). The subset draw's seed is declared in the ledger.
- 2 seeds each (20261042 and 20261043, as D_CC). The 100% point is D_CC's two stored runs; nothing is retrained.
  That makes 4 new runs.
- An optional 75% point adds 2 runs.

**Cost.**
- D_CC took 15.6 s per epoch (8.3 and 3.6 min for its two runs). At the 40-epoch cap, a 50% run takes at most
  about 5 min and a 25% run about 2.5 min.
- So the 4 runs take at most about 15 min on MPS, and under 30 min with scoring.
- Zero renders and zero separations. The time falls within the F20 training the user approved on 2026-10-27,
  once this plan is approved.

**Scoring.**
- R0's per-head table (`trusted_data_t3_r.r0_rows`), on FS_CC (334 examples, 32 sections, in distribution),
  against each subset's own constant and, beside it, the full pool's constant. The statistics:
  - switches: AUC;
  - knobs: the E difference against the constant;
  - amp choice: accuracy minus the base rate;
  - mics: accuracy minus the constant's.
- Intervals are 90% section-clustered, or jackknife, as R0.
- Reported per family (as R0: today's space, amp choice, amp EQ, pedals with the drives on their own, time
  effects, spring, gate and doubler, cab) and overall: the number of readable heads and each family's median effect, at 25%, 50% and 100%.
- D_CC's full-size table is the first R0 on the clean/crunch pool. It is read beside D_F5's R0, descriptively.

**Reading.** Effect sizes with intervals, no pass bar.
- **Still rising from 50% to 100%** (more readable heads, family effects growing beyond the seed spread): data is a
  bottleneck, which supports F20's scale. A log-linear trend gives a rough guide to 10k and 20k, flagged as
  extrapolation.
- **Flat:** data is not the bottleneck. F20's renders would be better spent on the input or the model: the input
  features, the loss (scored by sound rather than knob by knob), or the switch readout. That goes back to the
  user before any F20 render.

**Caveat.** FS_CC is also D_CC's early-stopping set, as FS5 was for R0. Choosing the best epoch on it biases every
point slightly upward. The bias is the same at every size, so the slope is what is read.

**Code needed.**
- A subset option on `cc_build train`. It writes to its own runs folder and never touches D_CC's runs.
- An R0 command for the clean/crunch pool that reuses `trusted_data_t3_r.r0_rows`, with `cc_build`'s rows, FS_CC
  and the constants that `cc_readout fit` stores (or the same computation run on a subset's labels).
- Both are declared and reviewed first.

### Step 0b (optional, 99 renders): the near-chance readout on D_CC

D_CC is re-read on V-real-11 with decision C's rule, declared before the read. Every switch whose pooled p lies
within δ of 0.5 takes the pool's majority.

It needs one new answer: 33 (part, amp) groups × (1 priming + 1 answer × 2 directions) = 99 renders, about 6 min.
The rows are D_CC:C − D_CC and D_CC:C − D_CC:constant, descriptive.

It tests the readout rule on a stored model, before F20 depends on it.

## Step 1: F20 (only if step 0 supports it, and on the user's yes at B)

**The pool.**
- The clean/crunch pool's 294 sections, with heavy material at most 20%, under the trusted-data rules.
- ElecGtr8 joins if the alignment check on its shifted copy reads within 1 ms of 0. `cc_build shift` and
  `align-shifted` run inside this build, as `amendment_4` (c) requires.
- "Unknown" DIs make up at most 25% of draws.
- The DI inventory and the pool are rebuilt before the plan step, and drift is printed.

**Size, staged, stopping on evidence.**
- Stages: 5k, then 10k, then 20k examples.
- After each stage, D_CC's recipe trains on everything built so far (one seed, minutes) and step 0's R0 table is
  re-read on FS_CC.
- The next stage starts only while the curve still rises. The renders used are reported at each stage.

**Measured cost.** These come from the clean/crunch pool's own build on 2026-10-30, which covered 3,890 examples.
Per 1,000 examples:
- about 4,540 renders, priming included;
- about 48 min of render wall on 3 shards;
- about 51 min of separation (MPS and CPU workers);
- about 1.3 GB of disk.

On top of that, near-silent redraws add target renders. D_CC refused 15.8% of targets, so allow about 16–22% more
target renders.

| Size | Renders | Render wall | Separation | Disk |
|---|---|---|---|---|
| 10k | about 50k | about 8 h | about 8.5 h | about 13 GB |
| 20k | about 100k | about 16 h | about 17 h | about 26 GB |

- Rendering and separation overlap by stage: one stage separates while the next renders, so the GPU and CPU both
  stay busy. That shortens the wall time.
- The estimate is higher than T3's 51k renders for 20k, because each target renders in its own primed process
  (`amendment_5_fix`'s recipe).
- At most 3 render processes machine-wide, `setopt no_bg_nice`, and the 31 GB disk guard.
- **Disk is the binding limit.** On 2026-10-30, 45 GB were free. With the 31 GB guard, about 14 GB can be used.
  That fits 10k, but not 20k (see F).

**Training.**
- D_F20, 3 seeds (20261042, 20261043, 20261044), with D_CC's recipe and early stopping on FS_CC (plus the new
  stages' fit sections).
- About 58 s per epoch at 10k and 115 s at 20k. With the 40-epoch cap, that is at most about 40 or 77 min per run
  on MPS.
- D_F20w is the same build with the audibility-weighted loss (D): 3 more runs and no renders.

**The declared fixes**, from T3's F5 audit and since:
1. A near-silent target redraws its new controls from its own stream, up to 5 tries. It is dropped only when every
   try is silent. The redraw share and the switch on-rates are printed.
2. The audio runaway check. A target dominated by a steady tone the DI lacks, or rising steadily to saturation,
   is refused and redrawn. The rules and thresholds are those of the 2026-10-30 scan (`amendment_3_answers`), set
   where at most one non-oscillating example fires. Without the check, about 2% of each pool was runaway, mostly
   with delay feedback of 0.75 or more.
3. Each example is separated once, on one recorded device (D_CC's 802105 was separated by both workers).
4. The near-chance readout (C), declared before training.
5. The model is read against its own constant (rows below).
6. Audibility-weighted time-effect labels (D). Their form and the reader for the ear answers are declared and
   reviewed before any use.
7. ElecGtr8, as above.

## Step 2: the readout on V-real

- **V-real-11:** the same frozen 11 parts, 66 directions and 7 bands as every stored arm (decision E). T3's F20
  code expects V-real-12, so the readout reads T3's frozen V-real-11 as `cc_readout` does, a small code change.
- **The answers:**
  - D_F20 (the pooled, plain readout);
  - D_F20 with the near-chance readout (if C is adopted);
  - D_F20's own constant;
  - D_F20 with the pedals at S;
  - D_F20w.
- **Renders:** 33 × (1 + 5 × 2) = 363, about 25 min.
- **Rows,** descriptive:
  - D_F20 − D_CC;
  - D_F20 − D_F5;
  - D_F20 − its own constant;
  - D_F20:at-S:pedals − D_F20;
  - D_F20w − D_F20;
  - the readout rule's row.
- Each row: band-weighted means with 90% band-clustered t intervals (7 bands), per class with bands −/+,
  part-weighted, V-real-10 and leave-one-band-out beside. Per-seed answers are inference only.
- No pass bar: an interval holding 0 is undecided, not failed.
- Each answer's renders are read where they were made: cross-process comparisons carry the time effects'
  render-order noise (noise, not bias).

## Decisions for the user

- **A. Run step 0 first** (zero renders, under 30 min). *Recommended:* it costs minutes and decides whether
  F20's 50–100k renders are worth it.
- **B. F20 on step 0's result.**
  - If the curve rises: build in stages (5k, 10k, then 20k if disk allows) and stop when the curve flattens.
  - If it is flat: no F20 renders. Bring the input and model options back to you.
  - *Recommended.*
- **C. The near-chance readout.**
  - Where a switch's p lies within δ = 0.1 of 0.5, take the pool's majority (the model's own constant), with the
    plain readout beside.
  - This keeps every control learned. It also respects the 2026-10-27 ruling that writing S for unreadable
    controls is not the method; S's value is the alternative, and it conflicts with that ruling.
  - Step 0b checks the rule on D_CC first (99 renders). *Recommended: the majority rule, with 0b.*
- **D. The audibility weight's form.**
  - A per-example weight for each time effect and spring, from a zero-render proxy computed from its settings.
    The proxy is calibrated on the 95 measured pairs' guitar-alone J (step 4's 71 and the drive page's 24) and
    checked against the ear answers.
  - The weight is per effect family, because no single cut works across effects: unheard drive pairs reach a
    solo J of 2.68, while the heard tremolo is at 2.30.
  - Trained as D_F20w beside the plain D_F20, so no extra renders.
  - *Recommended.* Measuring every example's audibility by rendering would cost about 25–30k renders at 20k.
- **E. V-real-11 or V-real-12.**
  - *Recommended: V-real-11*, comparable with every stored arm.
  - Signs ElecGtr6, the 12th part, could be read beside, but each compared arm would need about 6 more
    directions rendered there. Not proposed.
- **F. Disk for 20k.**
  - 10k fits today. 20k needs about 12 GB more free above the guard.
  - What to move to the Trash is your call. Otherwise F20 stops at 10k.
  - *Recommended: decide only if step 0 and the 10k stage still show a rising curve.*
