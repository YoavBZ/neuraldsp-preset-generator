# F20 on the clean/crunch pool (re-plan, 2026-10-30)

**Status: draft for the user's yes. Nothing has been run, rendered or trained under it. It waits on the user's
decisions on the [pipeline review](ml-pipeline-review.md)'s tests and on this plan. Once approved, each step is
declared in the ledger and independently reviewed before it runs.**

Replaces T3's F20 plan (ledger `trusted-data-t3`, `amendment_1`'s F20 fixes; ROADMAP item (d)). It builds on the
[clean/crunch pool](clean-crunch-pool-plan.md) (ledger `clean-crunch-pool-dcc`).

## Why

On V-real, D_F5 about equals its own constant (−0.004 [−0.052, +0.043], T3's F5 read). D_CC trails its own
constant: +0.103 [+0.051, +0.155], 0 of 7 bands better (`amendment_4_outcome`). Most of D_CC's loss against D_F5 is
in its pedal answers: the drive switches sit near chance (pooled p 0.42–0.50 against 48–53% "on" in its labels),
and a 0.5 readout turns a bare-majority "on" into "off".

The question F20 answers: **does much more clean/crunch data carry over to real songs, so that the model beats its
constant on V-real?**

## Why the question is the transfer, not the in-distribution curve

In-distribution gains have kept failing to carry over to real songs:
- **pretrain-set-c.** The validation curve fell from 10k to 20k (−0.0069 [−0.0092, −0.0047]) and was flat to 40k.
  Part C's existing 40k models then tied S on stage F: D − S +0.033 [−0.053, +0.119] (ROADMAP, 2026-10-19).
- **direct-model-stems.** The pilot's D_stem − D0 was −0.0127 [−0.0216, −0.0039] on R_out. On stage F, step 4's
  D − D0 was −0.006 [−0.032, +0.019].
- **D_F5.** It reads 20 of 116 heads on FS5, drive2 among them at an AUC of about 0.67 (R0), yet it equals its
  constant on V-real.
- **No real size test yet.** D_core5 and D_F5 share their examples, so they are not a size test.
- **AUC misses calibration.** It cannot see D_CC's calibration shift (drive p under 0.5 while the labels are 53%
  "on").

Other facts behind this plan:
- **The information is lost before the model.** The tone-information probe (`trusted-data-t3`
  `amendment_2_outcome`) found a linear reader gets 86 of 116 heads from the target render, 30 from the self-built
  mix and 20 from the stem.
- **Two input fixes did not help.** The mix as input (D_F5mix) is not shown better. The X-LANCE fine-tune was not
  adopted.
- **The time effects are mostly not heard.** On the guitar alone, 25 of the 26 pairs near tau were not heard.
  One tremolo below tau was heard, so the ear places no cut (`clean-crunch-pool-dcc` `amendment_6_answers`).

An in-distribution curve can rule F20 out, but it cannot rule it in. So step 0 reads its size points on V-real.

## Relation to the pipeline review

[The pipeline review](ml-pipeline-review.md) (ledger `ml-pipeline-review`) walks the direct model step by step and
proposes tests P1–P7. **F20 and its step 0 wait on the user's decisions on both: that review's tests and this
plan.**

**The order.**
1. The review's cheap tests come first:
   - **P1:** memorise about 200 examples. If the network cannot fit them, no bigger build helps yet.
   - **P2a:** a model on the clean target renders, read on held-out FS sections by knob and by sound.
   - **P4:** P2a's model on V-real's own amp tracks. Does learning from Morgan renders carry over to real
     recordings at all, at one size?
2. **Step 0 is the natural follow-up if P4 shows transfer.** None of P1–P7 asks whether more data helps on real
   songs, so step 0's V-real size curve stays.
   - The review's step 22 test is "P1, then a learning curve inside P2a": an in-distribution curve on the clean
     input.
   - Step 0 differs: its sizes are read on V-real, real songs, with the input P2 picks.
3. **If P4 is undecided or shows no transfer,** the plan goes back to the user, and step 0 does not run.

**The review's findings that touch F20.** Each is fixed, or settled by its P-test, before step 0's training or
any F20 build.
- **Step 5, the class input.** Training conditions on the draw's base class, which differs from the section's
  class in 1,512 of 3,033 examples. V-real conditions on the part's class. P6 reads it, and the conditioning is
  made the same in training and on songs.
- **Step 12, the doubles.** DT doubles are rendered with the target's core setting, so their drive switches
  differ from the label in 34–35% of the examples that have one. F20's build gives doubles the target's full
  setting. Step 0 reuses D_CC's build, so every size carries this equally (a stated caveat). P7 reads its size.
- **Step 16, the input.** The stem holds every guitar, and the target sits a median 6.2 dB under the rest. Only
  78 of 3,033 D_CC examples have the target as the only guitar. P2's rungs (target alone, mix, stem) decide which
  input F20 builds for.
- **Step 22, too little training.** Runs reach their best epoch after only 430–1,204 steps. The training length,
  and the per-head loss logs of step 24, are set from P1 before any step-0 run.
- **Steps 29, 26–27 and 37, the readout.** D_F5 reads 5 of 85 knobs on FS5. The readout's fallback lands at or
  below the constant, which leans worse than S on V-real (+0.092 [−0.029, +0.213], undecided). P3 tests a
  fallback to S.
- **Step 32, two identical V-real inputs.** Wickerman ElecGtr2 and ElecGtr3 have byte-identical V-real stems:
  both crops cut the same window. Before step 0's read, the fix is declared: either one of the two parts is
  re-cropped at another window, or the two are counted as one input in V-real-11's count and weighting. The rows
  say which.
  - Re-cropping voids the stored comparators for that part (D_CC's constant, D_CC and D_F5). They would be
    re-rendered there, 6 directions each with priming.

**Work merged with the review, not duplicated.**
- Step 0's FS readout uses P2's code (by knob and by sound) instead of a separate R0 command.
- The near-chance readout (former step 0b, decision C) moves into P3's readout test, read beside S's fallback, so
  step 0 drops it. That adds one answer to P3: 33 × (1 + 2 × 2) = 165 renders instead of about 99.

## Step 0: the size points on real songs (231 renders; after P1, P2a and P4)

**What runs.**
- D_CC's recipe (`cc_build train`: same heads, loss, augmentation and early stopping on FS_CC), with the input P2
  picks, P1's training length (step 22), the step-5 class fix and per-head loss logs (step 24).
- Trained on nested subsets of D_CC's 2,699 training examples. Sizes: 25%, 50% and 100%, drawn within each section
  so every section keeps at least one example, and nested (25% inside 50% inside 100%). The draw's seed is declared
  in the ledger.
- 2 seeds each (20261042 and 20261043, as D_CC).
- The 100% point is retrained on the same recipe. D_CC's stored runs were trained the old way, so as the 100%
  point they would confound the curve. They stay beside it as today's D_CC.
- 6 new runs. D_CC took 15.6 s per epoch, so at the 40-epoch cap a run takes at most about 10, 5 and 2.5 min by
  size: under about 40 min on MPS at today's length. If P1 sets a longer run, this scales with it.

**The read on V-real-11** (frozen, held out; declared before any inference):
- Three new answers:
  - D_CC25, the 25% models' pooled answer;
  - D_CC50, the 50% models' pooled answer;
  - D_CC100, the retrained 100% models' pooled answer.
- Renders: 33 (part, amp) groups × (1 priming + 3 answers × 2 directions) = 231, about 15 min. The recipe is
  `cc_readout`'s: isolate=True, one discarded priming render at S, 0.25 s trimmed, at most 3 render processes, the
  31 GB guard and `setopt no_bg_nice`.
- Rows (band-weighted, 90% band-clustered t, 7 bands; part-weighted, V-real-10 and per class beside):
  - each size against D_CC's own constant (its stored renders): D_CC25, D_CC50 and D_CC100, each minus the
    constant;
  - the steps between sizes: D_CC50 − D_CC25 and D_CC100 − D_CC50;
  - beside them, today's D_CC − constant (+0.103, stored) and D_CC100 − D_CC (the recipe's change at full size).
- All are cross-process comparisons: the time effects' render-order noise applies (noise, not bias).

**Beside it, on FS_CC** (334 examples, in distribution):
- P2's FS readout at each size (by knob, R0's rule, and by sound), against D_CC's constant, per family as R0
  (today's space, amp choice, amp EQ, pedals with the drives on their own, time effects, spring, gate and doubler,
  cab).
- Per-switch calibration: the mean p against the "on" rate, and the Brier score against the constant's.
- Caveat: FS_CC is also the early-stopping set, so these readings lean optimistic. They are read beside V-real,
  never alone.

**Reading.** Effect sizes with intervals, no pass bar.
- **V-real improves with size** (each size closer to the constant or past it, the size steps below 0 beyond their
  intervals): more data carries over. That supports F20's staged scale. Extending the trend past 100% is flagged
  as extrapolation.
- **FS_CC rises but V-real is flat:** the bottleneck is the transfer to real songs, and F20's scale is not the
  lever. The plan comes back to the user with transfer options (fix the bottleneck; don't drop the route). For
  example: training mixes closer to real records, an input that survives the mix, a loss scored by sound, or the
  readout.
- **Both flat:** data is not the bottleneck at this size. The input and model options come back to the user.
- **Undecided** (the intervals cannot tell the sizes apart, likely with 7 bands): this is said plainly. The user
  decides whether F20's first stage (5k, about 10k renders, about 3.5 h) runs as the next point of the curve, read
  on V-real.

**Code needed.**
- A subset option on `cc_build train`, writing to its own runs folder and never touching D_CC's runs.
- A step-0 readout in `cc_readout` for the three answers, reusing `render_answers` and the follow-up report.
- P2's FS readout (by knob and by sound), with calibration added.
- All are declared and reviewed first.

**The near-chance readout,** the former step 0b, is read within P3 (decision C):
- **The rule:** where a switch's pooled p lies within δ of 0.5, the answer takes the pool's majority (the model's
  own constant). It is read beside P3's fallback to S.
- **δ is set on FS at zero renders,** before any V-real read: the candidate (0, 0.05, 0.10, 0.15 or 0.20) with the
  best mean switch agreement, with ties going to the smaller value. The share of switch answers the rule overrides
  is printed.
- **Descriptive.** Flagged: the user's 2026-10-27 ruling made the plain readout the method.

## Step 1: F20 (only if step 0 supports it, and on the user's yes at B)

**The pool.**
- The clean/crunch pool's 294 sections, with heavy material at most 20%, under the trusted-data rules.
- T3's band cap: a band at most 35% of examples. Forkupines is at 35.9% of D_CC's planned training examples, so
  the cap binds there.
- "Unknown" DIs make up at most 25% of draws.
- ElecGtr8 joins if the alignment check on its shifted copy reads within 1 ms of 0. `cc_build shift` and
  `align-shifted` run inside this build (`amendment_4` (c)).
- The DI inventory and the pool are rebuilt first, with drift printed. D_CC's 3,033 kept examples, less the 64
  runaway ones, are reused toward the stages. Reused examples with a DT double (606 of 3,033, the review's step
  12) have their doubles re-rendered with the target's full setting: about 1.2k renders with priming. Their mixes
  are then rebuilt and their stems re-separated: 606 separations, about 31 min at 51 min per 1,000, and about
  1.1 GB at 1.8 GB per 1,000.
- The costs below assume D_CC's recipe. If P2's rungs point F20 at another input (step 16), the build changes and
  is re-costed before the user's yes at B.

**Stages, stopping on evidence.**
- Stages: 5k, 10k, then 20k examples in all.
- Each stage trains 2 seeds (20261042, 20261043) and is read on V-real-11. Its pooled answer costs 99 renders
  (33 × (1 + 1 × 2)), read against D_CC's constant and beside D_CC and the earlier stages. R0's FS_CC table is read
  beside it.
- The next stage starts only while V-real still improves. The renders used are reported at each stage.

**Cost.** These figures come from the pool's own build on 2026-10-30: 17,661 renders for 3,890 planned
examples, 3,033 kept. Per 1,000 new kept examples:
- about 5,000 renders: 4,540 per planned example as built, plus redraws in place of refusals (D_CC refused 15.8%
  of targets);
- about 53 min of render wall on 3 shards;
- about 51 min of separation (MPS and CPU workers);
- about 1.8 GB of disk (5.49 GB for 3,033 kept).

| Stage (total) | New examples | Renders | Render | Separation | Disk |
|---|---|---|---|---|---|
| 5k | about 2k | about 10k | 1.8 h | 1.7 h | 3.6 GB |
| 10k | about 7k | about 35k | 6.2 h | 6 h | 12.7 GB |
| 20k | about 17k | about 85k | 15 h | 14.5 h | 31 GB |

- **Rendering and separation do not overlap.** `local_objective._wait_cap` holds renders while a separation runs,
  so the wall times add: about 3.5 h, 12 h and 30 h of build. Changing that would need its own declaration; this
  plan does not propose it.
- **Disk is the binding limit.** On 2026-10-30, 48.4 GB were free (decimal) against the 31 GB floor, so about
  17 GB can be used. That fits 10k (12.7 GB) but not 20k (about 14 GB short; see F).
- **T3's estimate.** T3's plan costed 51k renders for about 15.8k new examples (it reused F5's), about 3.2 per
  example. The clean/crunch recipe costs about 5 per kept example, because each target renders in its own primed
  process.

**Training.**
- Per stage, 2 seeds. Per run, at most about 19 min at 5k, 39 min at 10k and 77 min at 20k (15.6 s per epoch
  scaled by size, 40-epoch cap).
- At the final stage: D_F20 with a third seed (20261044), and D_F20w, the same build with the audibility-weighted
  loss (D). No renders.

**The declared fixes**, from T3's F5 audit and since:
1. A near-silent target redraws its new controls from its own stream, up to 5 tries. It is dropped only when every
   try is silent. The redraw share and the switch on-rates are printed.
2. The audio runaway check. A target dominated by a steady tone the DI lacks, or rising steadily to saturation,
   is refused and redrawn. The rules and thresholds are those of the 2026-10-30 scan (`amendment_3_answers`).
   About 2% of each pool was runaway, mostly with delay feedback of 0.75 or more.
3. Each example is separated once, on one recorded device (D_CC's 802105 was separated by both workers).
4. The near-chance readout (C), if the user adopts it.
5. The model is read against its own constant: that is the primary row.
6. Audibility-weighted time-effect labels (D), declared and reviewed before use.
7. ElecGtr8 and the 35% band cap, as above.

## Step 2: the final readout on V-real-11

- **V-real-11:** the same frozen 11 parts, 66 directions and 7 bands as every stored arm (decision E). T3's F20
  code expects V-real-12, so the readout reads T3's frozen V-real-11 as `cc_readout` does, a small code change.
- **The answers:**
  - D_F20 (pooled, plain readout);
  - D_F20:C (the readout rule, if C is adopted; beside it otherwise);
  - D_F20's own constant;
  - D_F20:at-S:pedals;
  - D_F20w.
- **Renders:** 33 × (1 + 5 × 2) = 363, about 25 min.
- **Primary row: D_F20 − its own constant.**
- **Beside it,** descriptive:
  - D_F20 − S (S's stored renders);
  - D_F20 − D_CC;
  - D_F20 − D_F5;
  - D_F20:at-S:pedals − D_F20;
  - D_F20w − D_F20;
  - D_F20:C − D_F20.
- Each row: band-weighted means, 90% band-clustered t (7 bands), per class with bands −/+, part-weighted,
  V-real-10 and leave-one-band-out beside. Per-seed answers are inference only.
- No pass bar: an interval holding 0 is undecided, not failed.

## Decisions for the user

- **A. The order:** the pipeline review's P1, P2a and P4 first. Then step 0 (6 short runs and 231 renders, about
  an hour), if P4 shows transfer. *Recommended:* it reads the size points where it matters, on real songs, before
  F20's 10–85k renders.
- **B. F20 on step 0's result.**
  - If V-real improves with size: build in stages (5k, 10k, then 20k if disk allows), reading V-real at each and
    stopping when it stops improving.
  - If the gain stays in distribution, or nothing moves: no F20 renders. Bring the transfer, input or model options
    back to you.
  - If undecided: your call on the 5k stage as the next point.
  - *Recommended.*
- **C. The near-chance readout.**
  - Within δ of 0.5 (δ set on FS), take the pool's majority. This keeps every control learned. It is read within
    the review's P3, beside P3's fallback to S.
  - Adopting either changes the 2026-10-27 plain-readout ruling, so it is your call.
  - *Recommended: decide after P3's read.*
- **D. The audibility weight's form.**
  - A sliding per-example weight for each time effect and spring, not tied to an ear cut (the ear places none, and
    no spring pair was heard).
  - It comes from a zero-render proxy computed from the settings, fitted to guitar-alone J on T3's 824 stored pairs
    (`trusted-data/audibility/measure.json`: delay, reverb and tremolo 200 each, springs 224) plus step 4's 71.
    Cross-validation is grouped by section.
  - Solo J measures the guitar alone, not ROADMAP's "audible in the mix" (A_e, read beside).
  - Trained as D_F20w beside the plain D_F20, so no extra renders.
  - *Recommended.* Measuring every training example's audibility by rendering (one effect-off render per "on"
    time effect) is not proposed.
- **E. V-real-11 or V-real-12.**
  - *Recommended: V-real-11*, comparable with every stored arm.
  - Signs ElecGtr6, the 12th part, would need every compared arm rendered there too. Not proposed.
- **F. Disk for 20k.**
  - 10k fits today. 20k needs about 14 GB more free above the floor.
  - What to move to the Trash is your call. Otherwise F20 stops at 10k.
  - *Recommended: decide only if V-real still improves at 10k.*
