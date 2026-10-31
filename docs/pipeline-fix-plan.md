# Fixing the pipeline review's findings (plan, 2026-10-31)

**Status: declared 2026-10-31; independently reviewed and re-reviewed the same day (required changes all made,
below). Phase 1 has run (P5, P6, the dirty-double scan; zero renders, audited): see the review's steps 5, 12 and 36
and the ledger's `phase_1_outcome`.**

**Why.** The user (2026-10-31): "Start with the review, reevaluate our entire plan/roadmap and make sure we go
over each finding the review found, fully understand it, fix it and verify its fixed. Be organized, go step by
step and make sure no issues are opened in the end. We must fix what's blocked us from making the ML efforts
work." That asks for the [pipeline review](ml-pipeline-review.md)'s tests P1–P7 to run and each finding to be
fixed. Each phase is still entered in the ledger (`pipeline-fix`) before it runs, and each result is audited
before it is written up.

## The roadmap, re-evaluated

- **What the record shows.** Across every direct-model build (part C, the stems pilot, D_F5, D_CC), gains in
  distribution never carried over to real songs, and no build beat S on V-real. The review then found that D_F5
  reads almost nothing even on its own made-up songs (step 29). The next build (F20, more data) would scale a
  pipeline that is not yet shown to learn.
- **The order changes:**
  1. Make the yardstick fair: S's home advantage (P5), Wickerman's duplicate input (step 32), render-order noise
     (step 33).
  2. Fix the training data that is wrong: the DT doubles (step 12) and the runaway targets (step 6).
  3. Find the failing step: P1 (can the network learn at all?), then P2's ladder of inputs (clean target, target in
     its backing, the full mix, the stem), read by knob and by sound, on new settings and on new songs.
  4. Fix what the ladder locates and train one model with every adopted fix (D_fix), chosen on the training pool's
     own reads, never on V-real.
  5. Read D_fix on V-real. Scale (F20) only if the learning curves say size is the lever.
- **F20's draft (PR #345) is folded in here** and closed as superseded when this plan merges:
  - its step 0 (a size curve) becomes P2's learning curves, on the clean input and on the stem;
  - its decisions A (the order) and B (F20 on the evidence) become this plan's order and phase 5;
  - its near-chance switch rule (decision C) is read beside P3, as a measurement;
  - its audibility weights (decision D) are a phase 5 candidate.
- **Unchanged:** the product (`generate`, `match`, `edit`), arm A, the scope (clean, edge-of-breakup and crunch),
  the trusted-data rules and V-real-11's freeze.

## When a finding counts as closed

Each step that is not OK gets a dated line in the review, under the step and in its table row, saying which of
these holds:
- **Fixed:** the code change is merged with a test, and a run in this plan that uses it is named.
- **Ruled out:** a declared test shows the step does not limit the model (an effect size with its interval).
- **Limit, measured:** a limit this plan cannot remove (for example V-real's 7 bands), with its size stated, the
  mitigation in use and the plan that would remove it.
- **User decision:** the evidence is in and the choice is the user's (the readout's fallback, below).

The plan ends when every step reads OK, Fixed, Ruled out, Limit, measured or User decision. Which steps can end
as a limit or a decision is said in the table.

## The common recipe for every retrain in this plan

So that the ladder's rungs differ only in their input:
- **Split (step 23).** Two whole songs are held out ("NS", new songs): Adam Buckley "Drag Me Down" (clean) and The
  Maybe Next Years "One Flip Flop" (crunch). They were chosen as one clean and one crunch song of middling size,
  outside the two largest songs. NS holds 383 examples from 36 sections and 5 DIs in 2 bands. It is less dense than
  V-real: 144 of its 383 examples have one other guitar, and it has no DT doubles.
  - Training is D_CC's training examples of the other 8 songs: 2,327 examples, 232 sections, 27 DIs, 7 bands.
  - FS is FS_CC's examples of those songs: 259 examples in 6 bands, new settings on seen performances.
- **Dirty examples (steps 6, 12).**
  - The 64 runaway targets (`cc_drive_page.RUNAWAY`, the 2026-10-30 scan; 10 in the NS songs) are dropped
    everywhere.
  - Every DT double differs from its target's label: the zero-render scan finds 606 kept examples with one, all 606
    differing in at least one sounding control, 565 in at least one of the eight switches, and a median 73 stored
    settings. They are re-rendered with the target's full setting (phase 1b), so every rung trains and reads the
    same examples. If phase 1b's positive control fails, all 606 are dropped from every rung instead.
- **Class (step 5).** Every consumer keys on the section's class (`cls`), as V-real does: the network's class input,
  the constant, the pull's cells and the merge pools. Consequence, stated: D_CC's labels were drawn around the
  coin's (`base`) S, so `cls` carries no label information in this build, and the constant per (amp, `cls`) is
  roughly class-blind (pr12-crunch drive2 is on in 52.7% of labels by `base`, 42% by `cls`, so its majority flips to
  off). A future build draws the class from the section.
- **Inputs.**
  - P2a: the target render at its level in its own mix (the stored target times the mix's stored gain), so no rung
    can read absolute level, which a song does not carry. This is a perfect-separator rung.
  - P2b: P2c's mix minus every other guitar (the rendered ones and the recorded stand-ins), at P2c's own backing and
    overall gains and the same mastering draw. No gain is recomputed.
  - P2c: the stored self-built mix. P2d: its stored X-LANCE stem.
  - Each in the network's first channel, the second zeroed (D_stem's layout).
- **Augmentation (step 18).** None on the ladder. P2d-aug, D_CC's full augmentation on the stem, is a separate arm.
- **Length (step 22).** A fixed, generous epoch cap with a checkpoint every 10 epochs, the cap set from P1 and
  entered in the ledger before the ladder trains. Reads use both the final checkpoint and the NS-best one. A
  stopping metric that follows the sound (step 23's second fix) is not done here.
- **Diagnostics (step 24).** Each checkpoint logs, in eval mode: the loss on a fixed 300-example training subset
  and on NS, each head family's loss, and the label-marginal baseline in the same units.
  - The baseline is fitted on the training labels per (amp, `cls`) and read out of sample on NS: each knob a
    4-component 1-D mixture by EM, its sigma held to the network's range [e^-6, e^1]; each switch its on-rate; each
    mic and the amp their frequencies (add-half smoothing).
  - In P1 it is fitted on the memorised examples themselves (in sample), said so.
- **Seeds.** One seed (20261042) on the ladder's first pass; the second (20261043) where a paired difference is
  undecided, and for D_fix.

## The findings, one by one

Steps 1, 2, 9, 10, 17, 25, 28, 34 and 38 are OK in the review and need nothing. The rest:

| Step | Finding | Fix | Verified by | Can end as |
|---|---|---|---|---|
| 3 | Overlapping sections leak into early stopping | Stopping on held-out songs (step 23) | the recipe | Fixed |
| 4 | 2,699 examples from 10 songs | Learning curves on P2a and P2d (settings per performance, and performances); F20 is the next plan if they rise | the curves | Limit, measured |
| 5 | Class input is the coin in training, the part's class on songs | `cls` everywhere | P6 (FS half), a test that training, reads and V-real use one field, every run | Fixed |
| 6 | Wide, wet prior; runaway targets | Runaways dropped; the constant re-taken by `cls`; the prior itself is the next build's | every run; P3 measures the readout's share | Fixed (runaways), Limit, measured (prior) |
| 7 | Silent refusals skew the mode mix | The redraw in `cc_build` for the next build; by-knob error split by mode | the split | Limit, measured |
| 8 | Inaudible settings labelled in full | P2a's per-head table: which heads read even from the clean target; the audibility-weighted loss in phase 5 if the time effects fail there | P2a | Ruled out, or Fixed in D_fix, or Limit, measured |
| 11 | Stereo-only controls labelled, input mono | Their heads read on P2a's table; stereo input is the next build's | P2a | Limit, measured |
| 12 | DT doubles rendered with a different setting | Re-rendered with the target's full setting; `cc_build` renders them so in the next build | the positive control, P2c, P2d | Fixed |
| 13 | Stand-ins in 44% (a D_CC/D_F5 confound) | All comparisons here are within one build; P2b removes every other guitar | b − c | Ruled out (as an error) |
| 14 | The level prior holds V-real bands' statistics | V-real bands out of the ratio prior for the next build; level statistics, not labels | a test | Limit, measured |
| 15 | Half the mixes mastered; V-real's raw | By-knob error split by mastered on P2c and P2d | the split | Ruled out, or Limit, measured |
| 16 | The stem holds every guitar | Located by the ladder; the fix chosen in phase 5 | a − b, b − c, c − d | Fixed in D_fix, or Limit, measured |
| 18 | Augmentation may hide treble cues | P2d against P2d-aug | the pair | Ruled out, or Fixed |
| 19 | Tone lost before the model | Re-read with trained models by the ladder | the ladder | Ruled out, or as 16 |
| 20 | Network never shown to fit | P1 | P1 | Ruled out, or Fixed |
| 21 | Loss in knob units | P2a by sound against by knob | P2a | Ruled out, or a phase 5 candidate |
| 22 | Very little training | P1, the ladder's checkpoints, the curves | as named | Fixed (the length) |
| 23 | Early stopping on the training songs | Held-out songs and checkpoints | the recipe | Fixed |
| 24 | Training logs only total losses | Eval-mode, per-head and baseline logs | a test, P1 | Fixed |
| 26 | Knobs pulled toward the training average | P3 (toward S) read beside the plain readout | P3 | User decision |
| 27 | A 0.5 cut flips near-chance pedals | P3 (S's state) and the near-chance rule, beside the plain readout | P3 | User decision |
| 29 | Reads almost nothing on FS5 | P1 and the ladder locate it; D_fix | the ladder, D_fix | Fixed, or Limit, measured |
| 30 | Never read by sound on FS | The by-sound reads | P2 | Fixed |
| 31 | V-real: 11 parts, 7 bands | Part-weighted co-primary; Wickerman ElecGtr2 and 3 counted as one input | the rows | Limit, measured |
| 32 | Wickerman ElecGtr2 and 3 share one input | Counted once in every new row (P3 and P4 alike); P4 reads their own amp tracks | rows, P4 | Fixed |
| 33 | Render-order noise for time effects | Every new render, comparators included, in its own primed process | the renderer | Fixed |
| 35 | Low power | As 31; leave-one-band-out beside | the rows | Limit, measured |
| 36 | S chosen on V-real's clips | P5: S re-picked without them; read against both | P5 | Ruled out, or Fixed (S' as the comparator) |
| 37 | The training average leans worse than S | The constant re-taken by `cls`, re-rendered; P3 | P3 | User decision |

## Phases

### Phase 1: zero renders, no training

- **P5, S's home advantage (step 36).** Both start rules (`pipeline_review.pick_start`) re-run on the pinned
  development parts minus V-real's 9 part slugs (its 8 clips in the choice sets, and It Was My Fault ElecGtr1's
  other clip), then minus V-real's bands (clean only; crunch keeps one part). Where a pick changes (S'), S' − S on
  V-real from the stored distances where they exist; T3's own crop of It Was My Fault ElecGtr1, It Was My Fault
  ElecGtr3 and Signs ElecGtr3 have none and are listed (their renders are declared before they run, at most 66).
- **P6, the class input (step 5), FS half only.** D_CC's knob error on FS_CC with the coin it was trained on against
  the section's class. The V-real flip is dropped: the class fix is adopted either way, so it would touch held-out
  inputs for nothing.
- **P7 is dropped.** Its question, how much the doubles cost, is answered by fixing them (phase 1b); its "matching"
  group would hold 2 FS examples.
- **Code, each with tests:** the recipe (split, runaway and doubles handling, `cls` everywhere, eval-mode per-head
  and baseline logs, checkpoints). Phases 3 and 4 add their own: the by-sound read with a fresh primed process per
  answer render (step 33), and the V-real rows with Wickerman ElecGtr2 and 3 counted as one input and a
  part-weighted co-primary (steps 31, 32, 35). The next build's `cc_build` changes (the redraw, step 7; the ratio
  prior without V-real's bands, step 14; the class drawn from the section, step 5; doubles with the full setting,
  step 12) are written with phase 5, versioned so that D_CC's stored plan still reproduces.
- **The dirty-double scan** (done 2026-10-31, zero renders, training data only): 606 of 3,033 kept examples have a
  DT double; 565 differ in at least one of the eight switches, 424 in a pedal switch; a median 73 stored settings
  differ.

### Phase 1b: the doubles fix (renders, no training)

- For each of the 606 doubled examples, every other guitar re-rendered as `cc_build` rendered it, except that each
  DT double takes the target's full setting and renders in its own primed process (the target's time effects run on
  across renders in one process).
- **Positive control first:** the sections of 4 doubled examples are replayed exactly as `cc_build` rendered them
  (each section's whole job list in one shared process, the same order and priming), and every example's sum must
  reproduce its stored others within one FLAC step. If not, phase 1b stops and the 606 are dropped from every rung
  instead.
- The production re-render puts the ordinary other guitars in a new job order: valid renders, not necessarily
  bit-identical to the stored ones. After it, P2b of the doubled examples is rebuilt from their new mix, at its
  recomputed backing gain, with the same parity check.
- Then their mixes and X-LANCE stems (`cc_build build`'s recipe), written to `pipeline-fix/cc-dt/`; D_CC's files are
  never written.
- About 3,600 renders with priming and 606 separations, about 1.5–2 h.

### Phase 2: P1, can the network learn? (minutes of MPS)

- D_CC's network on 200 fixed training examples, inputs P2a and P2d, no augmentation, no early stopping, until the
  eval-mode loss on them stops falling (at most 1,500 epochs).
- Read per head family: how far below the in-sample label-marginal baseline its loss gets. No pass bar.
- If most heads stay near their baseline even on P2a, the network, loss or labels are broken: that is found and fixed,
  and P1 re-run, before phase 3.
- **Setting the ladder's length from P1:** the cap is the number of optimiser steps at which P1's P2a loss came within
  10% of its final fall, in the ladder's epochs (37 steps each), at least 60 epochs and at most 200. It is entered in
  the ledger before the ladder trains. A cap that would take the plan's MPS budget past 12 h comes back to the user.

### Phase 3: P2, where is the tone lost?

In the lean order: each step runs only while the one before leaves the question open.
1. **P2a and P2d** (one seed each), read by knob on FS and NS (R0's rule; zero renders), at both checkpoints.
2. **P2b and P2c**, unless a − d is already closed by knob.
3. **By sound:** a fixed sample of 60 FS and 60 NS examples (drawn once, spread over sections, entered in the ledger),
   grown to 120 each while the locating rows stay undecided.
   - Each model's answer (both halves' readouts and both seeds pooled, the plain readout on the example's own amp)
     is rendered through the example's own measure DI in its own process, primed with the same setting (as the
     targets were), and judged against the stored target render on both halves (`knob_ceiling.judge`).
   - S (the `cls` start preset) and the constant (`cls`) are rendered once for the sample.
   - **Positive control first:** each sampled example's own label on its own select ("truth") must reproduce its
     stored target render (the judge at its floor), and on the class start preset's select, where answers are
     written, too. At most 480 renders.
   - A judge refusal (a silent render) is counted and shown per row, never dropped quietly.
   - **The locating rows:** a − b, b − c and c − d, paired on the same examples. Beside them, each rung − S and −
     constant. FS rows are band-clustered (6 bands); NS rows are section-clustered with the caveat that NS is one
     clean and one crunch song (2 bands).
4. **Beside the ladder:**
   - P2d-aug (step 18);
   - learning curves on P2a and P2d, by knob: 25% and 50% of the training examples nested within sections (more
     settings per performance, F20's lever), and 50% of the sections with all their examples (fewer performances);
   - new songs by k-fold: the 10 songs in 5 folds by band (BKS's two songs together), P2a and P2d, one seed, the
     ladder's length, read by knob on every held-out song (band-clustered, 9 bands);
   - zero-render splits of the by-knob error: by draw mode (step 7) and by mastered (step 15).
- **Reading:** the rung whose locating row carries the loss is the failing step. If P2a has no skill, the problem
  is the model, labels or loss (steps 20–24), not the input.
- **An easier task than V-real:** on FS and NS the model is told the true amp, and the answer is rendered on it. On
  V-real no Morgan amp is the real one. Phase 5's by-sound read with the amp mismatched measures that gap.

### Phase 4: P3 and P4 on V-real (measurements)

- **P3, fall back to S (steps 26, 27, 37), a measurement only.** The user ruled on 2026-10-27 that writing S for
  unreadable controls is a measurement, not the method. For D_CC and for the ladder's best rung that a song can
  feed (P2c or P2d):
  - the plain readout;
  - knobs pulled toward S, and a switch whose head did not read on FS and NS kept at S;
  - the near-chance rule (F20's decision C): a switch within δ of 0.5 takes its pool's majority, δ set on FS.
- **P4, real guitar input (steps 9, 11, 32).** P2a's model reads V-real's own amp tracks at the training median
  loudness: does learning from Morgan renders carry over to real recordings?
- **Inputs on V-real:** P2c reads the crop's raw mix, P2d its stored stem, P2a the amp track (P4). P2b has no input
  on a real song and is not read there.
- Every answer, and every comparator (S, the `cls` constant, D_CC's plain answer), is rendered in its own primed
  process (step 33), since the stored comparators were rendered in shared processes. Wickerman ElecGtr2 and 3 count
  as one input in both P3 and P4. Band-weighted, 90% band-clustered t (7 bands), part-weighted beside.

### Phase 5: the located fix, D_fix, and scale

- **Chosen on FS, NS and the k-fold reads only**, before any V-real read of D_fix. Phase 4's V-real reads are
  measurements; if they shape the choice, D_fix's V-real read is labelled selection-contaminated. The candidates by
  outcome:
  - other guitars carry the loss (a − b small, b − c large): train where the target leads the other guitars; how
    the product says a part is not readable is for the product session;
  - the separator carries it (c − d large): read the mix, or the mix and the stem;
  - the clean input already fails: the loss or labels (audibility weights, a sound-aware loss), sized by P1;
  - the curves still rise at full size: scale (F20's staged build), read on V-real at each stage, in its own plan.
- **D_fix:** the recipe plus every adopted fix, 2 seeds, read by sound on FS and NS, with the amp mismatched (about
  480 renders), and on V-real with the plain readout as primary and P3's readouts beside.
- **Decisions for the user, with the evidence:** whether to adopt the S fallback or the near-chance rule
  (steps 26, 27, 37), and whether to scale.

## Budget

- **Renders:** about 3,600 for phase 1b; about 2,200 for P2's by-sound read; about 1,600 for phase 4; about 1,000
  for D_fix's reads. About 8,400 in all, roughly 3–4 h of render time at 3 processes.
- **MPS:** about 12 h at a 100-epoch cap (P1, the ladder with second seeds where needed, P2d-aug, 6 curve points,
  10 k-fold runs, D_fix). A cap from P1 that goes past it comes back to the user.
- **Disk:** P2's inputs about 0.3 GB; phase 1b's audio and features about 1.2 GB; the 31 GB guard holds.
- Every render: isolate=True, a discarded priming render, 0.25 s trimmed, at most 3 render processes,
  `setopt no_bg_nice`. V-real is read only in P5's stored distances, phase 4 and D_fix's declared read.

## Review (2026-10-31)

An independent review approved with 12 required changes, all made above:
1. the rungs now differ only in their input (level, augmentation, examples, P2b's construction);
2. every DT double counts as dirty (the doubles are re-rendered), and P7 is dropped;
3. NS's intervals are section-clustered with the caveat, and new songs are read by k-fold over all bands;
4. P3 is a measurement, the S fallback a decision for the user;
5. `cls` replaces `base` in every consumer, with its consequence stated;
6. the budget is re-costed;
7. each closure is reachable in this plan, or named as a limit or a decision;
8. paired locating rows;
9. a fixed cap with checkpoints, and the baseline declared;
10. curves on the stem too, and a fewer-performances point;
11. V-real inputs per rung, and the amp mismatch;
12. D_fix is chosen without V-real.

**Re-review (2026-10-31)** of the revision and its code: approve with 4 required changes, all made: phase 1b's
positive control replays the original job order; P2b of a doubled example uses its new mix's backing gain; the
by-sound read gets a "truth" positive control; the bookkeeping (P5 and P6 entered, the ledger's held-out and band
lines). It audited P5 and P6 and agrees with their readings.

Its optional points are folded in: the lean order, P6's FS half only, a sample that grows on evidence, one
Wickerman weighting for P3 and P4, the runaway list named, the by-sound protocol, step 23's unfinished second fix,
the product's ownership and PR #345's decisions.
